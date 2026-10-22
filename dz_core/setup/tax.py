"""Tax regime of a client: IFU or régime réel, and the TVA templates
(DECISIONS.md "Tax", from the SCF advice of 21 October 2026, Q5).

Most very small producers pay the IFU (flat tax on turnover) and do not
charge TVA. Others are on the régime réel and charge TVA at 19 % (standard)
or 9 % (reduced). The 2026 tax codes put every product of our sectors at 19 %
(honey, jams, date paste, cosmetics, t-shirts, fabric); only fresh dates are
at 9 %, and locally grown fresh fruit is exempt until 31 Dec 2026.

The setup wizard's templates book collected and deductible TVA in one
account ("TVA 19%"), which the SCF does not allow. setup_tva makes, for
every company:
- per-rate collected TVA ledgers 445711 (19 %) and 445712 (9 %) (setup/chart.py),
  deductible TVA on 44566 (stocks and services) and 44562 (fixed assets);
- a sales template "TVA ventes" and a purchase template "TVA achats" whose
  rows carry rate 0: the rate comes from the item's Item Tax Template;
- Item Tax Templates "TVA 19 %", "TVA 9 %", "Exonéré" and "TVA 19 %
  immobilisations", and "TVA 19 %" on every item group of the company.

- IFU: no template is the default, so invoices carry no TVA (an IFU invoice
  may not show TVA: CTCA art. 64).
- Régime réel: "TVA ventes" and "TVA achats" are the defaults.

Not handled yet: stamp duty on cash payments (open for COD, see DECISIONS)
and the turnover report for IFU. The G50 helper is the report "Aide G50".
"""

import frappe

from dz_core.dz_core.doctype.dz_core_settings.dz_core_settings import AUTO, IFU, NO_TVA, REEL
from dz_core.setup.accounts import account_by_number

TEMPLATE_DOCTYPES = ("Sales Taxes and Charges Template", "Purchase Taxes and Charges Template")
IFU_NOTE = "Contribuable soumis à l'IFU : TVA non facturée."
AUTO_NOTE = "Auto-entrepreneur : TVA non facturée."
# the invoice note prepare() writes when none is set (DZ Core Settings, editable)
NOTES = {IFU: IFU_NOTE, AUTO: AUTO_NOTE}

STANDARD, REDUCED, EXEMPT, ASSETS = "TVA 19 %", "TVA 9 %", "Exonéré", "TVA 19 % immobilisations"
REDUCED_RATE = 9

# Item Tax Template -> {SCF account number: rate}
ITEM_TAX_TEMPLATES = {
	STANDARD: {"445711": 19, "445712": 0, "44566": 19, "44562": 0},
	REDUCED: {"445711": 0, "445712": 9, "44566": 9, "44562": 0},
	EXEMPT: {"445711": 0, "445712": 0, "44566": 0, "44562": 0},
	ASSETS: {"445711": 0, "445712": 0, "44566": 0, "44562": 19},  # a fixed asset bought
}

SALES_TEMPLATE = "TVA ventes"
PURCHASE_TEMPLATE = "TVA achats"
# (account number, description printed on the invoice)
SALES_ROWS = [("445711", "TVA 19 %"), ("445712", "TVA 9 %")]
PURCHASE_ROWS = [("44566", "TVA déductible"), ("44562", "TVA déductible sur immobilisations")]


def apply_tax_regime(company, regime):
	setup_tva(company)
	if regime in NO_TVA:
		unset_default_templates(company)
	elif regime == REEL:
		set_default_templates(company)
	else:
		frappe.throw(f"Régime fiscal inconnu : {regime}")


def abbr(company):
	return frappe.get_cached_value("Company", company, "abbr")


def setup_tva(company):
	"""The per-rate templates and the item groups' default (STANDARD). Safe to
	run again: what exists is kept."""
	if not all(account_by_number(company, number) for number, _rate in SALES_ROWS):
		return  # the chart changes (setup/chart.py) have not run on this company
	for title, rates in ITEM_TAX_TEMPLATES.items():
		item_tax_template(company, title, rates)
	tax_template("Sales Taxes and Charges Template", company, SALES_TEMPLATE, SALES_ROWS)
	tax_template("Purchase Taxes and Charges Template", company, PURCHASE_TEMPLATE, PURCHASE_ROWS)
	for group in frappe.get_all(
		"Item Default", filters={"parenttype": "Item Group", "company": company}, pluck="parent"
	):
		set_group_tax(company, group)


def item_tax_template(company, title, rates):
	name = f"{title} - {abbr(company)}"
	if not frappe.db.exists("Item Tax Template", name):
		frappe.get_doc(
			{
				"doctype": "Item Tax Template",
				"title": title,
				"company": company,
				"taxes": [
					{"tax_type": account_by_number(company, number), "tax_rate": rate}
					for number, rate in rates.items()
					if account_by_number(company, number)
				],
			}
		).insert(ignore_permissions=True)
	return name


def tax_template(doctype, company, title, rows):
	name = f"{title} - {abbr(company)}"
	if frappe.db.exists(doctype, name):
		return name
	doc = frappe.get_doc({"doctype": doctype, "title": title, "company": company})
	for number, description in rows:
		account = account_by_number(company, number)
		if account:
			row = {
				"charge_type": "On Net Total",
				"account_head": account,
				"rate": 0,
				"description": description,
			}
			if doctype.startswith("Purchase"):
				row.update({"category": "Total", "add_deduct_tax": "Add"})
			doc.append("taxes", row)
	doc.insert(ignore_permissions=True)
	return name


def set_group_tax(company, group, title=STANDARD):
	"""The group's Item Tax Template for the company, unless it has one."""
	template = f"{title} - {abbr(company)}"
	if not frappe.db.exists("Item Tax Template", template):
		return
	doc = frappe.get_doc("Item Group", group)
	if any(
		frappe.db.get_value("Item Tax Template", row.item_tax_template, "company") == company
		for row in doc.taxes
	):
		return
	doc.append("taxes", {"item_tax_template": template})
	doc.save(ignore_permissions=True)


def unset_default_templates(company):
	for doctype in TEMPLATE_DOCTYPES:
		for name in frappe.get_all(doctype, {"company": company, "is_default": 1}, pluck="name"):
			frappe.db.set_value(doctype, name, "is_default", 0)


def set_default_templates(company):
	"""Our per-rate templates become the defaults (a client may move from IFU to réel)."""
	for doctype, title in zip(TEMPLATE_DOCTYPES, (SALES_TEMPLATE, PURCHASE_TEMPLATE), strict=True):
		name = f"{title} - {abbr(company)}"
		if not frappe.db.exists(doctype, name):
			continue
		for other in frappe.get_all(doctype, {"company": company, "is_default": 1}, pluck="name"):
			if other != name:
				frappe.db.set_value(doctype, other, "is_default", 0)
		frappe.db.set_value(doctype, name, "is_default", 1)


def template_with_rate(doctype, company, rate):
	"""A tax template of this company whose only rate is `rate`, if any (the
	setup wizard's whole-invoice templates)."""
	for name in frappe.get_all(doctype, {"company": company}, pluck="name", order_by="creation"):
		rates = {row.rate for row in frappe.get_doc(doctype, name).taxes}
		if rates == {rate}:
			return name
	return None
