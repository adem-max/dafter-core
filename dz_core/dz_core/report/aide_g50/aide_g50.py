"""Report "Aide G50": the month's TVA for a company on the régime réel,
from the ledger (dz_core/closing.py tva_figures): taxable turnover per rate,
TVA collected, TVA deductible, the credit carried, and what is to pay on the
G50 (or the new credit). A button posts the settlement entry
(make_tva_settlement). A help, not the declaration: the client or the
accountant files the G50.
"""

from frappe import _

from dz_core.closing import tva_figures
from dz_core.reports import get_company


def execute(filters=None):
	filters = filters or {}
	f = tva_figures(get_company(filters), filters.get("month"))
	columns = [
		{"fieldname": "line", "label": _("Ligne"), "fieldtype": "Data", "width": 420},
		{"fieldname": "base", "label": _("Base HT"), "fieldtype": "Currency", "width": 150},
		{"fieldname": "tva", "label": _("TVA"), "fieldtype": "Currency", "width": 150},
	]
	rows = [
		{
			"line": _("Chiffre d'affaires taxable à 19 % (445711)"),
			"base": f.bases["19"],
			"tva": f.collected_19,
		},
		{"line": _("Chiffre d'affaires taxable à 9 % (445712)"), "base": f.bases["9"], "tva": f.collected_9},
		{"line": _("Chiffre d'affaires exonéré ou hors champ"), "base": f.bases["0"], "tva": 0},
		{"line": _("TVA collectée"), "tva": f.collected_19 + f.collected_9},
		{"line": _("TVA déductible sur achats de stocks et services (44566)"), "tva": -f.deductible},
		{"line": _("TVA déductible sur immobilisations (44562)"), "tva": -f.deductible_assets},
		{"line": _("Crédit de TVA du mois précédent (44568)"), "tva": -f.credit_before},
	]
	if f.new_credit:
		rows.append({"line": _("Crédit de TVA à reporter (44568)"), "tva": -f.new_credit})
	else:
		rows.append({"line": _("TVA à payer sur le G50 (44551)"), "tva": f.to_pay})
	if f.settlement:
		rows.append({"line": _("Liquidation passée : {0}").format(f.settlement)})
	return columns, rows
