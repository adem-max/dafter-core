"""Tax regime of a client: IFU or régime réel.

Most very small producers pay the IFU (flat tax on turnover) and do not
charge TVA. Others are on the régime réel and charge TVA at 19 % (standard)
or 9 % (reduced: basic foodstuffs and listed essentials).

- IFU: no tax template is applied by default, so invoices carry no TVA.
- Régime réel: the 19 % template made by the setup wizard is the default.
  The wizard also makes a 9 % template ("Algeria TVA 9%"); the user picks it
  per invoice, or sets it on an Item Tax Template for the products that use
  it. If a site has no 9 % template, one is added.

Not handled yet, waiting for the accountant:
- stamp duty on cash payments (droit de timbre, scale from circular
  14/MF/DGI/LF.2025): electronic payments are exempt
- the G50 helper report for clients on the régime réel
- the turnover report for IFU clients
"""

import frappe

from dz_core.dz_core.doctype.dz_core_settings.dz_core_settings import IFU, REEL

TEMPLATE_DOCTYPES = ("Sales Taxes and Charges Template", "Purchase Taxes and Charges Template")
REDUCED_RATE = 9
IFU_NOTE = "Contribuable soumis à l'IFU : TVA non facturée."


def apply_tax_regime(company, regime):
	if regime == IFU:
		unset_default_templates(company)
	elif regime == REEL:
		set_default_templates(company)
		create_reduced_rate_templates(company)
	else:
		frappe.throw(f"Régime fiscal inconnu : {regime}")


def unset_default_templates(company):
	for doctype in TEMPLATE_DOCTYPES:
		for name in frappe.get_all(doctype, {"company": company, "is_default": 1}, pluck="name"):
			frappe.db.set_value(doctype, name, "is_default", 0)


def template_with_rate(doctype, company, rate):
	"""A tax template of this company whose only rate is `rate`, if any."""
	for name in frappe.get_all(doctype, {"company": company}, pluck="name", order_by="creation"):
		rates = {row.rate for row in frappe.get_doc(doctype, name).taxes}
		if rates == {rate}:
			return name
	return None


def standard_template(doctype, company):
	"""The 19 % template the setup wizard made for this company, if any."""
	return template_with_rate(doctype, company, 19)


def set_default_templates(company):
	"""Make the 19 % template the default again (a client may move from IFU to réel)."""
	for doctype in TEMPLATE_DOCTYPES:
		name = standard_template(doctype, company)
		if name and not frappe.db.get_value(doctype, name, "is_default"):
			for other in frappe.get_all(doctype, {"company": company, "is_default": 1}, pluck="name"):
				frappe.db.set_value(doctype, other, "is_default", 0)
			frappe.db.set_value(doctype, name, "is_default", 1)


def create_reduced_rate_templates(company):
	"""A 9 % copy of each 19 % template, same tax account, if the site has no 9 % template."""
	abbr = frappe.get_cached_value("Company", company, "abbr")
	for doctype in TEMPLATE_DOCTYPES:
		title = f"TVA {REDUCED_RATE}%"
		if template_with_rate(doctype, company, REDUCED_RATE):
			continue
		source = standard_template(doctype, company)
		if not source:
			continue
		doc = frappe.copy_doc(frappe.get_doc(doctype, source))
		doc.title = title
		doc.is_default = 0
		for row in doc.taxes:
			row.rate = REDUCED_RATE
			row.description = f"TVA {REDUCED_RATE}%"
		doc.insert(ignore_permissions=True)
		frappe.logger("dz_core").info(f"{doctype} {title} - {abbr} created")
