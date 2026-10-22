"""Report "Clôture du mois": the checks to run before a month is frozen
(dz_core/closing.py; DECISIONS.md, "Monthly close").

One row per check, OK or À voir, with what to do. Two checks have an action
button (cloture_du_mois.js): moving suppliers' debit balances from 4081 to
4097, and freezing the month.
"""

from frappe import _

from dz_core.closing import closing_rows
from dz_core.reports import get_company


def execute(filters=None):
	filters = filters or {}
	company = get_company(filters)
	columns = [
		{"fieldname": "check", "label": _("Contrôle"), "fieldtype": "Data", "width": 460},
		{"fieldname": "amount", "label": _("Montant"), "fieldtype": "Currency", "width": 130},
		{"fieldname": "status", "label": _("État"), "fieldtype": "Data", "width": 80},
		{"fieldname": "todo", "label": _("À faire"), "fieldtype": "Data", "width": 520},
	]
	return columns, closing_rows(company, filters.get("month"))
