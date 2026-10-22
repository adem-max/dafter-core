"""Report "Aide G12": an IFU or auto-entrepreneur company's turnover of the
year per month, goods and services, the IFU on it, what is already booked and
the year before's turnover; a button books the IFU (dz_core/books/ifu.py).
A help, not the declaration."""

import frappe
from erpnext.accounts.utils import get_fiscal_year
from frappe.utils import today

from dz_core.books.ifu import figures_table, year_figures
from dz_core.books.registers import as_report
from dz_core.reports import get_company


def execute(filters=None):
	filters = filters or {}
	company = get_company(filters)
	fiscal_year = filters.get("fiscal_year") or get_fiscal_year(today(), company=company)[0]
	settings = frappe.get_cached_doc("DZ Core Settings")
	regime = settings.tax_regime if settings.company == company else None
	return as_report(figures_table(year_figures(company, fiscal_year, regime)))
