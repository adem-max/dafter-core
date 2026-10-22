"""Report "Exercice comptable": the year-end checks and steps (close the year,
freeze it, the accountant's closing file, the yearly archive), with their
buttons (exercice_comptable.js; dz_core/books/year_end.py).
"""

import frappe
from erpnext.accounts.utils import get_fiscal_year
from frappe import _
from frappe.utils import today

from dz_core.books.year_end import year_checks
from dz_core.reports import get_company


def execute(filters=None):
	filters = filters or {}
	company = get_company(filters)
	fiscal_year = filters.get("fiscal_year") or get_fiscal_year(today(), company=company)[0]
	columns = [
		{"fieldname": "check", "label": _("Contrôle ou étape"), "fieldtype": "Data", "width": 460},
		{"fieldname": "amount", "label": _("Montant"), "fieldtype": "Currency", "width": 140},
		{"fieldname": "status", "label": _("État"), "fieldtype": "Data", "width": 80},
		{"fieldname": "todo", "label": _("À faire"), "fieldtype": "Data", "width": 520},
	]
	if not frappe.db.exists("Fiscal Year", fiscal_year):
		return columns, []
	return columns, year_checks(company, fiscal_year)
