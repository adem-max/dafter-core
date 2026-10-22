"""Report "Registre des achats": the year's purchase invoices to copy into the
paper register (dz_core/books/registers.py)."""

from frappe.utils import get_year_start, today

from dz_core.books.registers import as_report, purchases_register
from dz_core.reports import get_company


def execute(filters=None):
	filters = filters or {}
	return as_report(
		purchases_register(
			get_company(filters),
			filters.get("from_date") or get_year_start(today()),
			filters.get("to_date") or today(),
		)
	)
