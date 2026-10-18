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

Stays manual, because it differs per client: the company's legal mentions
(Company form, section "Mentions légales"), users, then the client's data
through the import workbook (dz_core/imports).

For an online-sales client, install dz_cod after this and run its own
prepare: it adds the COD warehouses, courier and settings on top.
"""

import frappe
from frappe.utils import today

from dz_core.dz_core.doctype.dz_core_settings.dz_core_settings import IFU
from dz_core.setup.accounts import opening_account
from dz_core.setup.sectors import apply_sector
from dz_core.setup.tax import IFU_NOTE, apply_tax_regime

CHART_OF_ACCOUNTS = "Algerie - Plan Comptable General 2 avec code"


def prepare(company, abbr, sector, tax_regime=IFU):
	run_setup_wizard(company, abbr)
	warehouses = apply_sector(sector, company)
	apply_tax_regime(company, tax_regime)
	opening_account(company)

	settings = frappe.get_doc("DZ Core Settings")
	settings.update({"company": company, "sector": sector, "tax_regime": tax_regime, **warehouses})
	if tax_regime == IFU and not settings.invoice_note:
		settings.invoice_note = IFU_NOTE
	settings.save(ignore_permissions=True)
	frappe.db.commit()
	print(f"{company} is ready ({sector}, {tax_regime}).")
	print("Next: legal mentions on the Company form, users, then the import workbook.")


def run_setup_wizard(company, abbr):
	if frappe.is_setup_complete():
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
