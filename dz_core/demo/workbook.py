"""The demo's master data, written into the client import workbook and imported
with it: the demo goes through the same door as a real client's Excel file.

The generated file stays in the site's private files ("import-demo-<profile>.xlsx")
so a prospect can be shown the Excel their data would come in.
"""

import datetime
import os

import frappe

from dz_core.imports.workbook import SHEETS, import_workbook

# Profile attribute holding each sheet's rows
SOURCES = {
	"Fournisseurs": "SUPPLIERS",
	"Clients": "CUSTOMERS",
	"Articles": "ITEMS",
	"Modèles": "MODELS",
}


def cell(value):
	if isinstance(value, bool):
		return "Oui" if value else "Non"
	if isinstance(value, list | tuple):
		return ", ".join(str(v) for v in value)
	if isinstance(value, datetime.date):
		return value.strftime("%d/%m/%Y")
	return value


def rows_of(profile, sheet):
	if sheet in SOURCES:
		return [
			[cell(row.get(key)) for _header, key, _req in SHEETS[sheet]]
			for row in getattr(profile, SOURCES[sheet], [])
		]
	if sheet == "Nomenclatures":
		return [
			[product, batch_qty, component, qty, None]
			for product, (batch_qty, components) in profile.BOMS.items()
			for component, qty in components
		]
	if sheet == "Stock initial":
		return [
			[code, warehouse, qty, rate, batch, cell(expiry)]
			for code, warehouse, qty, rate, batch, expiry in profile.OPENING
		]
	return []


def write_workbook(profile, path, sheets=tuple(SHEETS)):
	from openpyxl import Workbook
	from openpyxl.styles import Font

	wb = Workbook()
	wb.remove(wb.active)
	for sheet, columns in SHEETS.items():
		if sheet not in sheets:
			continue
		ws = wb.create_sheet(sheet)
		ws.append([header for header, _key, _req in columns])
		for header_cell in ws[1]:
			header_cell.font = Font(bold=True)
		for row in rows_of(profile, sheet):
			ws.append(row)
	wb.save(path)
	return path


def import_masters(profile_name, profile, opening_date):
	"""Two files, like a real onboarding: the masters first (suppliers,
	customers, items, models with their size/colour variants, recipes), then
	the opening stock count, which can name the variants the first one made."""
	masters = [sheet for sheet in SHEETS if sheet != "Stock initial"]
	return [
		import_file(f"import-demo-{profile_name}-1-donnees.xlsx", profile, masters, None),
		import_file(
			f"import-demo-{profile_name}-2-stock-initial.xlsx", profile, ["Stock initial"], opening_date
		),
	]


def import_file(filename, profile, sheets, opening_date):
	"""Write one workbook, check it (no error allowed), then import it."""
	path = frappe.get_site_path("private", "files", filename)
	os.makedirs(os.path.dirname(path), exist_ok=True)
	write_workbook(profile, path, sheets)
	file_url = f"/private/files/{filename}"
	if not frappe.db.exists("File", {"file_url": file_url}):
		frappe.get_doc(
			{"doctype": "File", "file_name": filename, "file_url": file_url, "is_private": 1}
		).insert(ignore_permissions=True)

	check = import_workbook(path)
	if check["errors"]:
		frappe.throw("Démo : le classeur d'import a des erreurs :<br>" + "<br>".join(check["errors"]))
	return import_workbook(path, dry_run=0, opening_date=str(opening_date) if opening_date else None)
