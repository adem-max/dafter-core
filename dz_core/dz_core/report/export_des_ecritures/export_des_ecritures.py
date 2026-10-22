"""Report "Export des écritures": the ledger lines of a period with their
journal, as the entry export writes them (dz_core/books/export.py; decree
09-110 art. 15). The button "Fichier des écritures" (export_des_ecritures.js)
writes the files and keeps them on a DZ Archive with their SHA-256.
"""

from frappe import _
from frappe.utils import get_first_day, getdate, today

from dz_core.books.export import entry_rows
from dz_core.reports import get_company

COLUMNS = [
	("JournalCode", _("Journal"), "Data", 70),
	("EcritureNum", _("N° d'écriture"), "Data", 170),
	("EcritureDate", _("Date"), "Date", 95),
	("CompteNum", _("Compte"), "Data", 90),
	("CompteLib", _("Libellé du compte"), "Data", 200),
	("CompAuxLib", _("Tiers"), "Data", 160),
	("PieceRef", _("Pièce"), "Data", 140),
	("EcritureLib", _("Libellé"), "Data", 260),
	("Debit", _("Débit"), "Currency", 120),
	("Credit", _("Crédit"), "Currency", 120),
	("ValidDate", _("Saisie le"), "Date", 95),
	("Utilisateur", _("Utilisateur"), "Data", 160),
]


def execute(filters=None):
	filters = filters or {}
	company = get_company(filters)
	start = filters.get("from_date") or get_first_day(today())
	end = filters.get("to_date") or today()
	columns = [
		{"fieldname": name, "label": label, "fieldtype": fieldtype, "width": width}
		for name, label, fieldtype, width in COLUMNS
	]
	rows = entry_rows(company, getdate(start), getdate(end))
	if rows:
		rows.append(
			{
				"EcritureLib": _("Total"),
				"Debit": sum(row["Debit"] for row in rows),
				"Credit": sum(row["Credit"] for row in rows),
			}
		)
	return columns, rows
