"""Tax warnings on purchases and payments, and the TVA given back on losses
and gifts (SCF advice, deep research and follow-up checks of 21 October
2026; DECISIONS.md, "Tax").

- A purchase line of a non-stock, non-asset item above 60,000 DA HT a unit
  is probably equipment to depreciate, not an expense (CIDTA art. 141-3 as
  rewritten by LF 2022): a warning on the Purchase Invoice.
- A purchase "Sans facture (justificatif interne)" (an informal supplier)
  carries no TVA: refused if it has any; the closing file lists the year's
  total as likely non-deductible.
- A supplier invoice above 1,000,000 DA TTC paid in cash loses its TVA
  deduction (CTCA art. 30): a warning on the Payment Entry.
- Régime réel: stock issued for a loss, theft, destruction or as samples
  and gifts gives back the TVA deducted on it, except proven force majeure
  (CTCA arts. 37-a, 41-5). "Aide G50" lists the month's issues and posts the
  reversal (Dr the issue's expense account / Cr 44566) once a month, at each
  item's own rate (its Item Tax Template on 44566).
"""

import frappe
from frappe import _
from frappe.utils import flt

from dz_core.setup.accounts import account_by_number

LOW_VALUE_LIMIT = 60_000  # DA HT per unit
CASH_LIMIT = 1_000_000  # DA TTC per invoice
DEDUCTIBLE = "44566"
REASONS_GIVING_BACK_TVA = ("Casse ou vol", "Échantillons et cadeaux", "Destruction")
# own products leave stock through 7245; the TVA they give back is a charge,
# not production (the class 72 check, closing.py), so it goes here
OTHER_CHARGES = "65888"
INFORMAL_SUPPLIER = "Fournisseur divers sans facture"
INFORMAL_GROUP = "Fournisseurs de stocks"


def setup_informal_supplier():
	"""The supplier informal purchases are entered against (hooks after_migrate)."""
	if frappe.db.exists("Supplier Group", INFORMAL_GROUP) and not frappe.db.exists(
		"Supplier", {"supplier_name": INFORMAL_SUPPLIER}
	):
		frappe.get_doc(
			{"doctype": "Supplier", "supplier_name": INFORMAL_SUPPLIER, "supplier_group": INFORMAL_GROUP}
		).insert(ignore_permissions=True)


def purchase_invoice_checks(doc, method=None):
	"""Purchase Invoice validate (hooks.py)."""
	if doc.get("dz_no_invoice"):
		taxed = [row for row in doc.get("taxes") or [] if flt(row.tax_amount)]
		if taxed:
			frappe.throw(_("Un achat sans facture ne permet pas de déduire la TVA : retirez les taxes."))
	for row in doc.get("items") or []:
		if row.get("is_fixed_asset") or frappe.get_cached_value("Item", row.item_code, "is_stock_item"):
			continue
		unit = flt(row.base_net_rate) / (flt(row.conversion_factor) or 1)
		if unit > LOW_VALUE_LIMIT:
			frappe.msgprint(
				_(
					"Ligne {0} : {1} à {2} DA HT l'unité, au-delà de 60 000 DA : c'est sans doute une "
					"immobilisation à amortir, pas une charge (art. 141-3 CIDTA)."
				).format(
					row.idx, row.item_name or row.item_code, frappe.format(unit, {"fieldtype": "Float"})
				),
				indicator="orange",
				alert=True,
			)


def cash_payment_checks(doc, method=None):
	"""Payment Entry validate (hooks.py): a big supplier invoice paid in cash."""
	if doc.payment_type != "Pay" or doc.party_type != "Supplier":
		return
	if not (frappe.db.get_value("Account", doc.paid_from, "account_number") or "").startswith("53"):
		return
	for ref in doc.get("references") or []:
		if ref.reference_doctype != "Purchase Invoice" or not ref.allocated_amount:
			continue
		if flt(frappe.db.get_value("Purchase Invoice", ref.reference_name, "base_grand_total")) > CASH_LIMIT:
			frappe.msgprint(
				_(
					"La facture {0} dépasse 1 000 000 DA TTC : payée en espèces, sa TVA n'est pas déductible "
					"(art. 30 CTCA). Payez-la par chèque ou virement."
				).format(ref.reference_name),
				indicator="orange",
				alert=True,
			)


def informal_purchases(company, start, end):
	"""Total of the purchases without an invoice in the period."""
	return flt(
		frappe.db.sql(
			"""SELECT SUM(base_grand_total) FROM `tabPurchase Invoice`
			WHERE company = %s AND docstatus = 1 AND dz_no_invoice = 1 AND posting_date BETWEEN %s AND %s""",
			(company, start, end),
		)[0][0],
		2,
	)


# ------------------------------------------------- TVA on losses and gifts


def deductible_rate(item_code, company):
	"""The % the item's Item Tax Template (item, else its group) puts on 44566."""
	account = account_by_number(company, DEDUCTIBLE)
	item_group = frappe.get_cached_value("Item", item_code, "item_group")
	for parenttype, parent in (("Item", item_code), ("Item Group", item_group)):
		for template in frappe.get_all(
			"Item Tax", filters={"parenttype": parenttype, "parent": parent}, pluck="item_tax_template"
		):
			if frappe.get_cached_value("Item Tax Template", template, "company") != company:
				continue
			rate = frappe.db.get_value(
				"Item Tax Template Detail", {"parent": template, "tax_type": account}, "tax_rate"
			)
			return flt(rate)
	return 0


def reversal_remark(end):
	return _("Reversement TVA pertes et dons {0}").format(end.strftime("%m/%Y"))


def tva_reversal_lines(company, start, end):
	"""[(stock entry, item, expense account, value, rate, tva)] of the month's
	issues whose reason gives back the TVA."""
	lines = []
	for entry, item_code, expense_account, value in frappe.db.sql(
		"""SELECT se.name, sed.item_code, sed.expense_account, sed.amount
		FROM `tabStock Entry Detail` sed JOIN `tabStock Entry` se ON se.name = sed.parent
		WHERE se.company = %s AND se.docstatus = 1 AND se.stock_entry_type = 'Material Issue'
			AND se.dz_issue_reason IN %s AND se.posting_date BETWEEN %s AND %s
		ORDER BY se.posting_date, se.name, sed.idx""",
		(company, REASONS_GIVING_BACK_TVA, start, end),
	):
		rate = deductible_rate(item_code, company)
		if rate:
			lines.append(
				(entry, item_code, expense_account, flt(value, 2), rate, flt(flt(value) * rate / 100, 2))
			)
	return lines


def tva_reversal_entry(company, end):
	from dz_core.closing import closing_entries, closing_key

	found = closing_entries(company, closing_key("tva-losses", end))
	return found[0] if found else None


@frappe.whitelist()
def make_tva_reversal(company, month):
	"""Dr each issue's expense account / Cr 44566, dated the month end, once a month."""
	from dz_core.closing import check_company, closing_key, lock_company, month_bounds

	frappe.has_permission("Journal Entry", "create", throw=True)
	check_company(company)
	start, end = month_bounds(month)
	lock_company(company)
	if tva_reversal_entry(company, end):
		frappe.throw(_("La TVA sur les pertes et dons de ce mois est déjà reversée."))
	by_account = {}
	for _entry, _item, expense_account, _value, _rate, tva in tva_reversal_lines(company, start, end):
		if (frappe.db.get_value("Account", expense_account, "account_number") or "").startswith("72"):
			expense_account = account_by_number(company, OTHER_CHARGES)
		by_account[expense_account] = by_account.get(expense_account, 0) + tva
	if not by_account:
		frappe.throw(_("Pas de sortie pour perte ou don ce mois-ci."))
	cost_center = frappe.get_cached_value("Company", company, "cost_center")
	entry = frappe.new_doc("Journal Entry")
	entry.update(
		{
			"company": company,
			"posting_date": end,
			"user_remark": reversal_remark(end),
			"dz_closing_key": closing_key("tva-losses", end),
		}
	)
	for account, amount in by_account.items():
		entry.append(
			"accounts",
			{"account": account, "debit_in_account_currency": flt(amount, 2), "cost_center": cost_center},
		)
	entry.append(
		"accounts",
		{
			"account": account_by_number(company, DEDUCTIBLE),
			"credit_in_account_currency": flt(sum(by_account.values()), 2),
		},
	)
	entry.insert()
	entry.submit()
	return entry.name
