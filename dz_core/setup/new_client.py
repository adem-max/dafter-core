"""Prepare a fresh client site in one command.

Run once, right after `bench new-site` and `bench --site <site> install-app dz_core`:

    bench --site client1.localhost execute dz_core.setup.new_client.prepare \\
        --kwargs "{'company': 'Miel Atlas', 'abbr': 'MA',
                   'sector': 'Alimentaire et cosmétique', 'tax_regime': 'IFU'}"

It runs the setup wizard (French, Algeria, DZD, Algerian chart of accounts),
applies the sector template (item groups, units, attributes, the three
warehouses and which group goes where), applies the tax regime, adds the
opening-balance account and fills DZ Core Settings. Safe to run twice:
whatever already exists is skipped.

It also makes "Facture DZ" and "Bon de livraison DZ" the default print formats
(unless the client already chose others), and the Atelier home page the page
users land on after login.

Stays manual, because it differs per client: the company's legal mentions
(Company form, section "Mentions légales"), users, then the client's data
through the import workbook (dz_core/imports).

For an online-sales client, install dz_cod after this and run its own
prepare: it adds the COD warehouses, courier and settings on top.
"""

import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter
from frappe.utils import today

from dz_core.dz_core.doctype.dz_core_settings.dz_core_settings import IFU
from dz_core.setup.accounts import opening_account
from dz_core.setup.sectors import apply_sector
from dz_core.setup.tax import IFU_NOTE, apply_tax_regime

CHART_OF_ACCOUNTS = "Algerie - Plan Comptable General 2 avec code"

# Our legal invoice and delivery note print by default (dz_core/dz_core/print_format)
DEFAULT_PRINT_FORMATS = {"Sales Invoice": "Facture DZ", "Delivery Note": "Bon de livraison DZ"}


def prepare(company, abbr, sector, tax_regime=IFU):
	run_setup_wizard(company, abbr)
	warehouses = apply_sector(sector, company)
	apply_tax_regime(company, tax_regime)
	opening_account(company)
	set_default_print_formats()
	allow_printing_cancelled()
	set_address_template()
	make_atelier_the_home_page()

	settings = frappe.get_doc("DZ Core Settings")
	settings.update({"company": company, "sector": sector, "tax_regime": tax_regime, **warehouses})
	if tax_regime == IFU and not settings.invoice_note:
		settings.invoice_note = IFU_NOTE
	settings.save(ignore_permissions=True)
	frappe.db.commit()
	print(f"{company} is ready ({sector}, {tax_regime}).")
	print("Next: legal mentions on the Company form, users, then the import workbook.")


def make_atelier_the_home_page():
	"""After login, open the Atelier home page instead of ERPNext's app list
	(route from add_to_apps_screen in hooks.py). A user can still pick another
	default app for themselves. An online-sales client then runs dz_cod's
	prepare, which makes COD the home page instead."""
	from frappe.core.doctype.system_settings.system_settings import clear_system_settings_cache

	frappe.db.set_single_value("System Settings", "default_app", "dz_core")
	# System Settings are cached per process: drop the copies so it applies now
	clear_system_settings_cache()
	frappe.local.system_settings = None


def set_default_print_formats():
	"""Facture DZ and Bon de livraison DZ by default, unless the client already
	chose one (Customize Form saves that choice as a Property Setter). ERPNext's
	own default (v16: "Sales Invoice Modern with Images") is not a choice."""
	for doctype, print_format in DEFAULT_PRINT_FORMATS.items():
		chosen = frappe.db.exists(
			"Property Setter",
			{"doc_type": doctype, "property": "default_print_format", "is_system_generated": 0},
		)
		if not chosen:
			make_property_setter(
				doctype, None, "default_print_format", print_format, "Data", for_doctype=True
			)


def allow_printing_cancelled():
	"""A cancelled invoice must stay printable (Facture DZ marks it FACTURE
	ANNULÉE across the page); ERPNext refuses by default."""
	frappe.db.set_single_value("Print Settings", "allow_print_for_cancelled", 1)


# How an Algerian address prints (invoices, delivery notes): ERPNext has no
# template for Algeria, and its default one ends with the country, in English
ADDRESS_TEMPLATE = """{{ address_line1 }}<br>
{% if address_line2 %}{{ address_line2 }}<br>{% endif -%}
{% if pincode %}{{ pincode }} {% endif %}{{ city }}<br>
{% if state and state != city %}{{ state }}<br>{% endif -%}
{% if country and country != "Algeria" %}{{ country }}<br>{% endif -%}
"""


def set_address_template():
	"""A French address template for Algeria. ERPNext's wizard makes one with
	Frappe's stock text; it is replaced unless the client edited it."""
	from frappe.contacts.doctype.address_template.address_template import get_default_address_template

	current = frappe.db.get_value("Address Template", "Algeria", "template")
	if current is None:
		frappe.get_doc(
			{"doctype": "Address Template", "country": "Algeria", "template": ADDRESS_TEMPLATE}
		).insert(ignore_permissions=True)
	elif current.strip() == get_default_address_template().strip():
		frappe.db.set_value("Address Template", "Algeria", "template", ADDRESS_TEMPLATE)


def run_setup_wizard(company, abbr):
	if frappe.is_setup_complete():
		# The wizard ran before (by hand, or by another app's setup): it will not
		# run again, so the company must already exist under this exact name
		if not frappe.db.exists("Company", company):
			existing = ", ".join(frappe.get_all("Company", pluck="name")) or "aucune"
			frappe.throw(
				f"Le site est déjà configuré, mais la société « {company} » n'existe pas. "
				f"Sociétés du site : {existing}. Relancez avec le nom exact."
			)
		return
	from frappe.desk.page.setup_wizard.setup_wizard import setup_complete

	year = today()[:4]
	setup_complete(
		{
			"language": "Français",
			"lang": "Français",
			"country": "Algeria",
			"timezone": "Africa/Algiers",
			"currency": "DZD",
			"company_name": company,
			"company_abbr": abbr,
			"chart_of_accounts": CHART_OF_ACCOUNTS,
			"fy_start_date": f"{year}-01-01",
			"fy_end_date": f"{year}-12-31",
			"setup_demo": 0,
		}
	)
	# Saving the document (not just the value) also sets every user's default company
	defaults = frappe.get_doc("Global Defaults")
	defaults.update({"default_company": company, "default_currency": "DZD", "country": "Algeria"})
	defaults.save()
