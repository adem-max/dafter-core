"""Sales and purchases registers (CPF art. 1; loi 22-23 art. 9 for
auto-entrepreneurs; SCF advice Q18; DECISIONS.md, "Tax").

IFU taxpayers keep a purchases and a sales register, numbered and initialled
by the tax office, and an auto-entrepreneur a register of receipts; nothing
in the texts allows keeping them only in software, so Daftar prints them to
be copied into the paper books. Every regime gets them: they are also a
plain list of the year's invoices.

One line per submitted invoice (opening invoices left out), in date order,
with its order number in the fiscal year; credit notes are negative;
a subtotal closes each month. On an auto-entrepreneur site the sales
register adds the day the invoice was paid (turnover counts at delivery,
per CIDTA art. 282 quater, the payment date is the reconciliation).
"""

import frappe
from erpnext.accounts.utils import get_fiscal_year
from frappe import _
from frappe.utils import flt, getdate

from dz_core.books.tables import AMOUNT, DATE, TEXT, table


def numbered(doctype, company, start, end, fields):
	"""The year's invoices up to `end`, numbered from the fiscal year's first
	day, then kept from `start`."""
	year_start = getdate(get_fiscal_year(start, company=company)[1])
	rows = frappe.get_all(
		doctype,
		filters={
			"company": company,
			"docstatus": 1,
			"is_opening": ["!=", "Yes"],
			"posting_date": ["between", [year_start, end]],
		},
		fields=["name", "posting_date", *fields],
		order_by="posting_date, creation, name",
	)
	return [
		(number, row) for number, row in enumerate(rows, 1) if getdate(row.posting_date) >= getdate(start)
	]


def with_month_totals(lines, date_index, amount_indexes, width, label_index):
	"""Insert a "Total MM/YYYY" line after each month (label in a text column)."""
	result, month, totals = [], None, None

	def close():
		if month is not None:
			line = [None] * width
			line[label_index] = _("Total {0}").format(month)
			for i, value in totals.items():
				line[i] = flt(value, 2)
			result.append(line)

	for line in lines:
		this = line[date_index].strftime("%m/%Y")
		if this != month:
			close()
			month, totals = this, dict.fromkeys(amount_indexes, 0.0)
		for i in amount_indexes:
			totals[i] += flt(line[i])
		result.append(line)
	close()
	return result


def paid_on(invoices):
	"""{sales invoice: the last day a payment was allocated to it}."""
	if not invoices:
		return {}
	return dict(
		frappe.db.sql(
			"""SELECT ref.reference_name, MAX(pe.posting_date) FROM `tabPayment Entry Reference` ref
			JOIN `tabPayment Entry` pe ON pe.name = ref.parent
			WHERE pe.docstatus = 1 AND ref.reference_doctype = 'Sales Invoice' AND ref.reference_name IN %s
			GROUP BY ref.reference_name""",
			(tuple(invoices),),
		)
	)


def sales_register(company, start, end, receipts=False):
	rows = numbered(
		"Sales Invoice",
		company,
		start,
		end,
		[
			"customer",
			"customer_name",
			"base_net_total",
			"base_total_taxes_and_charges",
			"base_grand_total",
			"dz_payment_mode",
		],
	)
	nif = dict(
		frappe.get_all(
			"Customer",
			filters={"name": ["in", list({row.customer for _n, row in rows}) or [""]]},
			fields=["name", "dz_nif"],
			as_list=True,
		)
	)
	paid = paid_on([row.name for _n, row in rows]) if receipts else {}
	lines = []
	for number, row in rows:
		line = [
			number,
			getdate(row.posting_date),
			row.name,
			row.customer_name,
			nif.get(row.customer) or "",
			flt(row.base_net_total, 2),
			flt(row.base_total_taxes_and_charges, 2),
			flt(row.base_grand_total, 2),
			row.dz_payment_mode or "",
		]
		if receipts:
			line.append(paid.get(row.name))
		lines.append(line)
	columns = [
		(_("N° d'ordre"), TEXT),
		(_("Date"), DATE),
		(_("N° de facture"), TEXT),
		(_("Client"), TEXT),
		(_("NIF"), TEXT),
		(_("Montant HT"), AMOUNT),
		(_("TVA et taxes"), AMOUNT),
		(_("Montant TTC"), AMOUNT),
		(_("Mode de paiement"), TEXT),
	]
	if receipts:
		columns.append((_("Encaissé le"), DATE))
	title = _("Registre des recettes") if receipts else _("Registre des ventes")
	return table(title, columns, with_month_totals(lines, 1, (5, 6, 7), len(columns), label_index=3))


def purchases_register(company, start, end):
	fields = [
		"supplier",
		"supplier_name",
		"bill_no",
		"bill_date",
		"base_net_total",
		"base_total_taxes_and_charges",
		"base_grand_total",
	]
	informal = frappe.get_meta("Purchase Invoice").has_field("dz_no_invoice")
	if informal:
		fields.append("dz_no_invoice")
	rows = numbered("Purchase Invoice", company, start, end, fields)
	tax_id = dict(
		frappe.get_all(
			"Supplier",
			filters={"name": ["in", list({row.supplier for _n, row in rows}) or [""]]},
			fields=["name", "tax_id"],
			as_list=True,
		)
	)
	lines = [
		[
			number,
			getdate(row.posting_date),
			row.bill_no or row.name,
			getdate(row.bill_date) if row.bill_date else None,
			row.supplier_name,
			tax_id.get(row.supplier) or "",
			flt(row.base_net_total, 2),
			flt(row.base_total_taxes_and_charges, 2),
			flt(row.base_grand_total, 2),
			_("Sans facture") if informal and row.dz_no_invoice else "",
		]
		for number, row in rows
	]
	columns = [
		(_("N° d'ordre"), TEXT),
		(_("Date"), DATE),
		(_("N° de facture du fournisseur"), TEXT),
		(_("Date de la facture"), DATE),
		(_("Fournisseur"), TEXT),
		(_("NIF"), TEXT),
		(_("Montant HT"), AMOUNT),
		(_("TVA"), AMOUNT),
		(_("Montant TTC"), AMOUNT),
		(_("Justificatif"), TEXT),
	]
	return table(
		_("Registre des achats"), columns, with_month_totals(lines, 1, (6, 7, 8), len(columns), label_index=4)
	)


def as_report(t):
	"""(columns, rows) for a script report from a table."""
	kinds = {AMOUNT: "Currency", DATE: "Date", TEXT: "Data"}
	columns = [
		{
			"fieldname": f"c{i}",
			"label": label,
			"fieldtype": kinds.get(kind, "Data"),
			"width": 150 if kind != TEXT else 170,
		}
		for i, (label, kind) in enumerate(t.columns)
	]
	rows = [{f"c{i}": value for i, value in enumerate(line)} for line in t.rows]
	return columns, rows
