"""Report "Registre des ventes" (or "des recettes" on an auto-entrepreneur
site): the year's sales invoices to copy into the paper register
(dz_core/books/registers.py)."""

import frappe
from frappe.utils import get_year_start, today

from dz_core.books.registers import as_report, sales_register
from dz_core.dz_core.doctype.dz_core_settings.dz_core_settings import AUTO
from dz_core.reports import get_company


def execute(filters=None):
	filters = filters or {}
	company = get_company(filters)
	settings = frappe.get_cached_doc("DZ Core Settings")
	receipts = settings.company == company and settings.tax_regime == AUTO
	return as_report(
		sales_register(
			company,
			filters.get("from_date") or get_year_start(today()),
			filters.get("to_date") or today(),
			receipts=receipts,
		)
	)
