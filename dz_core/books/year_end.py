"""The year end (SCF advice Q13 and Q20; DECISIONS.md, "Compliance"), shown
by the report "Exercice comptable".

The checks are the last month's close (closing.py) plus the stock accounts
against the stock ledger, then the steps in order: close the year, freeze it,
make the accountant's closing file and the yearly archive.

Closing the year is ERPNext's Period Closing Voucher, into 120 (profit) or
129 (loss) by the sign of the result; the owners' decision on the result is
a journal entry afterwards. ERPNext 16 first wants a completed "Stock Closing
Entry" up to the year end when the company has stock, which it builds in the
background: close_year starts it and asks to come back, then posts the
voucher (whose ledger lines ERPNext also writes in the background).
"""

import frappe
from frappe import _
from frappe.utils import flt, getdate

from dz_core.books.archive import CLOSING_FILE, YEARLY
from dz_core.books.tables import stock_gap
from dz_core.closing import OK, check_company, closing_rows, row
from dz_core.tax_checks import informal_purchases

# checks that must be OK before the year is closed (accounts that must be
# empty, production, stock) and, with the rest of the close, before the file
BLOCK_CLOSING = {"6589", "4781", "476", "479", "72", "stock"}
NOT_FOR_THE_FILE = {
	"4081",
	"frozen",
	"result",
	"closed",
	"closing_file",
	"archive",
	"deadline",
	"informal",
	"tva",
	"tva_earlier",
}
PROFIT, LOSS = "120", "129"


def year_bounds(fiscal_year):
	start, end = frappe.db.get_value("Fiscal Year", fiscal_year, ["year_start_date", "year_end_date"])
	return getdate(start), getdate(end)


def year_result(company, start, end):
	"""Income minus expenses of the year, before the closing voucher."""
	return flt(
		frappe.db.sql(
			"""SELECT SUM(gle.credit - gle.debit) FROM `tabGL Entry` gle
			JOIN `tabAccount` acc ON acc.name = gle.account
			WHERE gle.company = %s AND gle.is_cancelled = 0 AND gle.posting_date BETWEEN %s AND %s
				AND acc.root_type IN ('Income', 'Expense') AND gle.voucher_type != 'Period Closing Voucher'""",
			(company, start, end),
		)[0][0],
		2,
	)


def closing_account(company, result):
	number = PROFIT if result >= 0 else LOSS
	account = frappe.db.get_value("Account", {"company": company, "account_number": number, "is_group": 0})
	if not account:
		frappe.throw(_("Le compte {0} manque : relancez la mise en place SCF.").format(number))
	return account


def closing_voucher(company, end):
	return frappe.db.get_value(
		"Period Closing Voucher",
		{"company": company, "period_end_date": end, "docstatus": 1},
		["name", "gle_processing_status"],
		as_dict=True,
	)


def latest_archive(company, fiscal_year, kind, draft=None):
	filters = {"company": company, "fiscal_year": fiscal_year, "kind": kind}
	if draft is not None:
		filters["draft"] = draft
	return frappe.db.get_value("DZ Archive", filters, "name", order_by="creation desc")


def year_checks(company, fiscal_year):
	start, end = year_bounds(fiscal_year)
	month_rows = closing_rows(company, end)
	frozen = [r for r in month_rows if r["code"] == "frozen"]
	rows = [r for r in month_rows if r["code"] != "frozen"]
	gap = stock_gap(company, end)
	rows.append(
		row(
			_("Stocks : comptes de stock égaux à l'état des stocks"),
			gap,
			abs(gap) < 1,
			_("Un mouvement de stock n'est pas passé en comptabilité : voyez avec le comptable."),
			code="stock",
		)
	)
	informal = informal_purchases(company, start, end)
	if informal:
		rows.append(
			row(
				_("Achats sans facture de l'exercice (probablement non déductibles)"),
				informal,
				True,
				code="informal",
			)
		)
	result = year_result(company, start, end)
	rows.append(
		row(
			_("Résultat de l'exercice ({0})").format(
				_("bénéfice, au 120") if result >= 0 else _("perte, au 129")
			),
			result,
			True,
			code="result",
		)
	)
	voucher = closing_voucher(company, end)
	rows.append(
		row(
			_("Exercice clôturé (écriture de clôture)"),
			0,
			bool(voucher) and voucher.gle_processing_status in (None, "", "Completed"),
			_("Clôturez l'exercice une fois les contrôles au vert.")
			if not voucher
			else _("ERPNext passe les écritures de clôture : revenez dans quelques minutes."),
			action="close_year",
			code="closed",
		)
	)
	rows += frozen
	rows.append(
		row(
			_("Dossier de clôture pour le comptable"),
			0,
			bool(latest_archive(company, fiscal_year, CLOSING_FILE, draft=0)),
			_("Faites le dossier de clôture (Excel, PDF et fichier des écritures)."),
			action="make_closing_file",
			code="closing_file",
		)
	)
	rows.append(
		row(
			_("Archive annuelle (conservée 10 ans)"),
			0,
			bool(latest_archive(company, fiscal_year, YEARLY)),
			_("Une fois l'exercice gelé, faites l'archive annuelle."),
			action="make_archive",
			code="archive",
		)
	)
	return rows


def failing(rows, codes=None, except_codes=None):
	return [
		r
		for r in rows
		if r["status"] != OK
		and (codes is None or r["code"] in codes)
		and (except_codes is None or r["code"] not in except_codes)
	]


def refuse_if(rows, what):
	if rows:
		frappe.throw(
			_("{0} : ces contrôles ne sont pas au vert :").format(what)
			+ "<ul>"
			+ "".join(f"<li>{frappe.utils.escape_html(r['check'])}</li>" for r in rows)
			+ "</ul>"
		)


@frappe.whitelist()
def close_year(company, fiscal_year):
	"""Close the year (see the module docstring). Returns {"status", "message"}."""
	frappe.has_permission("Period Closing Voucher", "create", throw=True)
	check_company(company)
	start, end = year_bounds(fiscal_year)
	if closing_voucher(company, end):
		frappe.throw(_("L'exercice {0} est déjà clôturé.").format(fiscal_year))
	refuse_if(failing(year_checks(company, fiscal_year), codes=BLOCK_CLOSING), _("Clôture refusée"))

	if frappe.db.exists(
		"Stock Ledger Entry", {"company": company, "is_cancelled": 0, "posting_date": ["<=", end]}
	):
		waiting = stock_closing(company, end)
		if waiting:
			return {"status": "stock", "message": waiting}

	result = year_result(company, start, end)
	voucher = frappe.get_doc(
		{
			"doctype": "Period Closing Voucher",
			"company": company,
			"fiscal_year": fiscal_year,
			"transaction_date": end,
			"period_start_date": start,
			"period_end_date": end,
			"closing_account_head": closing_account(company, result),
			"remarks": _("Clôture de l'exercice {0}").format(fiscal_year),
		}
	)
	voucher.insert()
	voucher.submit()
	return {
		"status": "closed",
		"message": _("Exercice clôturé : {0} ({1} au {2}).").format(
			voucher.name,
			frappe.format(abs(result), {"fieldtype": "Currency"}),
			PROFIT if result >= 0 else LOSS,
		),
	}


@frappe.whitelist()
def freeze_year(company, fiscal_year):
	"""No entry on or before the year end any more (closing.freeze_month)."""
	from dz_core.closing import freeze_month

	return freeze_month(company, year_bounds(fiscal_year)[1])


def stock_closing(company, end):
	"""None when ERPNext's Stock Closing Entry up to `end` is complete and
	fresh; else starts or restarts it and returns what to tell the user."""
	closing = frappe.db.get_value(
		"Stock Closing Entry",
		{"company": company, "to_date": end, "docstatus": 1},
		["name", "status", "modified"],
		as_dict=True,
	)
	if not closing:
		doc = frappe.get_doc({"doctype": "Stock Closing Entry", "company": company, "to_date": end})
		doc.insert()
		doc.submit()
		return _("Clôture des stocks lancée ({0}) : relancez la clôture dans quelques minutes.").format(
			doc.name
		)
	if closing.status in ("Queued", "In Progress"):
		return _("La clôture des stocks {0} est en cours : relancez dans quelques minutes.").format(
			closing.name
		)
	last_change = frappe.db.sql(
		"""SELECT MAX(modified) FROM `tabStock Ledger Entry` WHERE company = %s AND posting_date <= %s""",
		(company, end),
	)[0][0]
	if closing.status == "Failed" or (last_change and last_change > closing.modified):
		frappe.get_doc("Stock Closing Entry", closing.name).regenerate_closing_balance()
		return _("Clôture des stocks {0} relancée : relancez dans quelques minutes.").format(closing.name)
	return None
