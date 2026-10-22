"""The entry export (decree 09-110 art. 15; SCF advice Q6, DECISIONS.md
"Compliance").

Every ledger line of a period, in the layout of the French "fichier des
écritures comptables" (FEC): Algeria's own specification is left to an
arrêté not yet published, and the FEC is what accounting software in Algeria
usually imports. One more column, Utilisateur, says who posted the line.

- Complete history: under the immutable ledger a cancelled document keeps its
  lines and gets reversal lines dated the day of the cancel, all with
  is_cancelled = 0, so the export shows both (a contre-passation, never a
  deletion).
- À-nouveaux (art. 14): when the period starts on the first day of a fiscal
  year, virtual "AN" lines carry the balance-sheet balances (classes 1 to 5,
  per account and party) from before it. Results of earlier years not yet
  closed go to 120 (profit) or 129 (loss), so the AN journal balances.
- Files: a tab-separated text (dates YYYYMMDD, decimal comma, as the FEC) and
  the same lines in Excel, kept on a DZ Archive with their SHA-256.
"""

import io

import frappe
from erpnext.accounts.utils import get_fiscal_year
from frappe import _
from frappe.utils import flt, getdate

from dz_core.books.journals import AN, journal_label, journal_of, treasury_journals

COLUMNS = [
	"JournalCode",
	"JournalLib",
	"EcritureNum",
	"EcritureDate",
	"CompteNum",
	"CompteLib",
	"CompAuxNum",
	"CompAuxLib",
	"PieceRef",
	"PieceDate",
	"EcritureLib",
	"Debit",
	"Credit",
	"ValidDate",
	"Utilisateur",
]
DATES = ("EcritureDate", "PieceDate", "ValidDate")
AMOUNTS = ("Debit", "Credit")
CANCELLATION = "On cancellation of "  # ERPNext's remark on reversal lines
RESULT_PROFIT, RESULT_LOSS = "120", "129"


def ledger_lines(company, start, end):
	return frappe.db.sql(
		"""SELECT gle.posting_date, gle.voucher_type, gle.voucher_no, gle.account,
			acc.account_number, acc.account_name, gle.party_type, gle.party,
			gle.debit, gle.credit, gle.remarks, gle.creation, gle.owner, gle.is_opening
		FROM `tabGL Entry` gle JOIN `tabAccount` acc ON acc.name = gle.account
		WHERE gle.company = %s AND gle.is_cancelled = 0 AND gle.posting_date BETWEEN %s AND %s
		ORDER BY gle.posting_date, gle.creation, gle.voucher_no, gle.name""",
		(company, start, end),
		as_dict=True,
	)


def starts_a_year(company, start):
	try:
		return getdate(get_fiscal_year(start, company=company)[1]) == getdate(start)
	except frappe.ValidationError:  # no fiscal year for that date
		return False


def opening_lines(company, start):
	"""The virtual à-nouveaux lines on `start` (see the module docstring)."""
	rows = frappe.db.sql(
		"""SELECT acc.account_number, acc.account_name, gle.account, gle.party_type, gle.party,
			SUM(gle.debit - gle.credit) AS amount
		FROM `tabGL Entry` gle JOIN `tabAccount` acc ON acc.name = gle.account
		WHERE gle.company = %s AND gle.is_cancelled = 0 AND gle.posting_date < %s
			AND acc.root_type IN ('Asset', 'Liability', 'Equity')
		GROUP BY gle.account, gle.party_type, gle.party
		HAVING ABS(amount) >= 0.005
		ORDER BY acc.account_number, gle.party""",
		(company, start),
		as_dict=True,
	)
	result = flt(
		frappe.db.sql(
			"""SELECT SUM(gle.debit - gle.credit) FROM `tabGL Entry` gle
			JOIN `tabAccount` acc ON acc.name = gle.account
			WHERE gle.company = %s AND gle.is_cancelled = 0 AND gle.posting_date < %s
				AND acc.root_type IN ('Income', 'Expense')""",
			(company, start),
		)[0][0]
	)
	if abs(result) >= 0.005:
		number = RESULT_LOSS if result > 0 else RESULT_PROFIT  # debit balance = a loss
		account = frappe.db.get_value(
			"Account", {"company": company, "account_number": number}, ["name", "account_name"], as_dict=True
		)
		rows.append(
			frappe._dict(
				account_number=number,
				account_name=account.account_name if account else _("Résultat non affecté"),
				account=account.name if account else number,
				party_type=None,
				party=None,
				amount=result,
			)
		)
	return [
		frappe._dict(
			posting_date=getdate(start),
			voucher_type="",
			voucher_no=f"{AN}-{getdate(start).year}",
			account_number=row.account_number,
			account_name=row.account_name,
			party_type=row.party_type,
			party=row.party,
			debit=max(flt(row.amount), 0),
			credit=max(-flt(row.amount), 0),
			remarks=_("À-nouveaux au {0}").format(getdate(start).strftime("%d/%m/%Y")),
			creation=None,
			owner="",
			is_opening="Yes",
		)
		for row in rows
	]


def party_names(lines):
	names = {}
	for doctype, field in (
		("Customer", "customer_name"),
		("Supplier", "supplier_name"),
		("Employee", "employee_name"),
	):
		parties = {line.party for line in lines if line.party_type == doctype and line.party}
		if parties:
			names.update(
				dict(
					frappe.get_all(
						doctype, filters={"name": ["in", list(parties)]}, fields=["name", field], as_list=True
					)
				)
			)
	return names


def supplier_bills(lines):
	"""{purchase invoice: (supplier's number, its date)}: the piece is the supplier's invoice."""
	invoices = {line.voucher_no for line in lines if line.voucher_type == "Purchase Invoice"}
	if not invoices:
		return {}
	return {
		name: (bill_no, bill_date)
		for name, bill_no, bill_date in frappe.get_all(
			"Purchase Invoice",
			filters={"name": ["in", list(invoices)]},
			fields=["name", "bill_no", "bill_date"],
			as_list=True,
		)
	}


def label(line, party_name):
	remarks = " ".join((line.remarks or "").split())
	if remarks.startswith(CANCELLATION):
		return _("Annulation de {0}").format(remarks[len(CANCELLATION) :])
	if not remarks or remarks == "No Remarks":
		remarks = " ".join(filter(None, [_(line.voucher_type), party_name or line.party]))
	return remarks[:200]


def entry_rows(company, start, end):
	"""The export's lines, as dicts keyed by COLUMNS (dates as dates, amounts as floats)."""
	start, end = getdate(start), getdate(end)
	lines = ledger_lines(company, start, end)
	if starts_a_year(company, start):
		lines = opening_lines(company, start) + lines
	treasury = treasury_journals(lines)
	names = party_names(lines)
	bills = supplier_bills(lines)
	rows = []
	for line in lines:
		code = journal_of(line, treasury)
		bill_no, bill_date = bills.get(line.voucher_no, (None, None))
		party_name = names.get(line.party) if line.party else None
		rows.append(
			{
				"JournalCode": code,
				"JournalLib": journal_label(code),
				"EcritureNum": line.voucher_no,
				"EcritureDate": line.posting_date,
				"CompteNum": line.account_number or line.account,
				"CompteLib": line.account_name,
				"CompAuxNum": line.party or "",
				"CompAuxLib": party_name or line.party or "",
				"PieceRef": bill_no or line.voucher_no,
				"PieceDate": getdate(bill_date) if bill_date else line.posting_date,
				"EcritureLib": label(line, party_name),
				"Debit": flt(line.debit, 2),
				"Credit": flt(line.credit, 2),
				"ValidDate": getdate(line.creation) if line.creation else line.posting_date,
				"Utilisateur": line.owner or "",
			}
		)
	return rows


def as_text(rows):
	"""FEC text: tab-separated, header line, dates YYYYMMDD, decimal comma."""

	def cell(column, value):
		if column in DATES:
			return value.strftime("%Y%m%d") if value else ""
		if column in AMOUNTS:
			return f"{flt(value):.2f}".replace(".", ",")
		return str(value or "").replace("\t", " ").replace("\n", " ")

	lines = ["\t".join(COLUMNS)]
	lines += ["\t".join(cell(column, row[column]) for column in COLUMNS) for row in rows]
	return ("\n".join(lines) + "\n").encode("utf-8")


def as_xlsx(rows, title):
	from openpyxl import Workbook
	from openpyxl.styles import Font

	book = Workbook()
	sheet = book.active
	sheet.title = title[:31]
	sheet.append(COLUMNS)
	for cell in sheet[1]:
		cell.font = Font(bold=True)
	for row in rows:
		sheet.append([row[column] for column in COLUMNS])
	for column in DATES:
		for cell in sheet[chr(ord("A") + COLUMNS.index(column))][1:]:
			cell.number_format = "DD/MM/YYYY"
	sheet.freeze_panes = "A2"
	buffer = io.BytesIO()
	book.save(buffer)
	return buffer.getvalue()


def entry_files(company, start, end, rows=None):
	"""[(file name, content, description)] for the export of a period."""
	rows = entry_rows(company, start, end) if rows is None else rows
	abbr = frappe.get_cached_value("Company", company, "abbr")
	stem = f"FEC-{abbr}-{getdate(start).strftime('%Y%m%d')}-{getdate(end).strftime('%Y%m%d')}"
	return [
		(f"{stem}.txt", as_text(rows), _("Fichier des écritures (texte, tabulations)")),
		(f"{stem}.xlsx", as_xlsx(rows, _("Écritures")), _("Fichier des écritures (Excel)")),
	]


@frappe.whitelist()
def export_entries(company, from_date, to_date):
	"""Write the export of the period, keep it on a DZ Archive and return
	{"archive": name, "files": [[file name, sha256]...]}."""
	from dz_core.books.archive import EXPORT, keep

	frappe.has_permission("GL Entry", "read", throw=True)
	if getdate(from_date) > getdate(to_date):
		frappe.throw(_("La date de début est après la date de fin."))
	archive = keep(company, EXPORT, entry_files(company, from_date, to_date), from_date, to_date)
	return {"archive": archive.name, "files": [[row.file_name, row.sha256] for row in archive.files]}
