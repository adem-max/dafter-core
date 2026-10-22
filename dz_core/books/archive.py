"""Files kept with their SHA-256 (decree 09-110 arts. 19 to 21; CPF art. 64:
books and supporting documents 10 years, other documents and data 6 years).

A DZ Archive holds the files of one export, yearly archive or closing file,
as private site files (so the daily off-site backup carries them), each with
its SHA-256, plus a hash register in the `sha256sum` format:

    sha256sum -c registre-des-empreintes.txt

re-checks every file. An archive is made only by code and never changes; it
cannot be deleted, nor can its files (protect_file, hooks.py), except by the
demo wipe.
"""

import hashlib

import frappe
from frappe import _

EXPORT = "Export des écritures"
YEARLY = "Archive annuelle"
CLOSING_FILE = "Dossier de clôture"
REGISTER = "registre-des-empreintes.txt"


def sha256(content):
	return hashlib.sha256(content).hexdigest()


def keep(company, kind, files, from_date, to_date, fiscal_year=None, draft=0):
	"""A new DZ Archive with `files` ([(file name, bytes, description)]) and
	their hash register. Returns the archive."""
	archive = frappe.get_doc(
		{
			"doctype": "DZ Archive",
			"company": company,
			"kind": kind,
			"fiscal_year": fiscal_year,
			"from_date": from_date,
			"to_date": to_date,
			"draft": draft,
		}
	)
	archive.flags.dz_internal = True
	archive.insert(ignore_permissions=True)
	lines = []
	for name, content, description in files:
		archive.append("files", attach(archive, name, content, description))
		lines.append(f"{sha256(content)}  {name}")
	register = ("\n".join(lines) + "\n").encode("utf-8")
	archive.append("files", attach(archive, REGISTER, register, _("Registre des empreintes (SHA-256)")))
	archive.register_hash = sha256(register)
	archive.flags.dz_internal = True
	archive.save(ignore_permissions=True)
	return archive


def attach(archive, name, content, description):
	stored = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": f"{archive.name}-{name}",
			"content": content,
			"is_private": 1,
			"attached_to_doctype": "DZ Archive",
			"attached_to_name": archive.name,
		}
	).insert(ignore_permissions=True)
	return {
		"file": stored.file_url,
		"file_name": name,
		"sha256": sha256(content),
		"size": len(content),
		"description": description,
	}


@frappe.whitelist()
def verify(archive):
	"""[(file name, ok)]: each file's content against the hash taken when it was kept."""
	doc = frappe.get_doc("DZ Archive", archive)
	doc.check_permission("read")
	result = []
	for row in doc.files:
		# the bytes on disk: File.get_content() decodes text files (and drops a BOM)
		path = frappe.get_doc("File", {"file_url": row.file, "attached_to_name": doc.name}).get_full_path()
		with open(path, "rb") as stored:
			result.append([row.file_name, sha256(stored.read()) == row.sha256])
	return result


@frappe.whitelist()
def make_archive(company, fiscal_year):
	"""The yearly archive of a frozen year: the entry export, the books
	(balance générale, grand livre, journal centralisateur) in Excel, the SCF
	statements and the balance in PDF, the year's audit trail; each with its
	SHA-256 in the register."""
	from dz_core.books import tables
	from dz_core.books.export import entry_files, entry_rows
	from dz_core.books.statements import BALANCE_SHEET, INCOME_STATEMENT
	from dz_core.books.year_end import year_bounds

	frappe.has_permission("DZ Archive", "read", throw=True)
	frappe.has_permission("GL Entry", "read", throw=True)
	start, end = year_bounds(fiscal_year)
	frozen = frappe.db.get_value("Company", company, "accounts_frozen_till_date")
	if not frozen or frappe.utils.getdate(frozen) < end:
		frappe.throw(_("Gelez d'abord l'exercice jusqu'au {0}.").format(frappe.format(end, "Date")))
	entries = entry_rows(company, start, end)
	books = [
		tables.trial_balance(company, start, end),
		tables.general_ledger(company, start, end, entries),
		tables.centralising_journal(company, start, end, entries),
	]
	statements = [
		tables.statement_table(company, INCOME_STATEMENT, start, end),
		tables.statement_table(company, BALANCE_SHEET, start, end),
		books[0],
	]
	heading = _("{0} - exercice {1}").format(company, fiscal_year)
	files = entry_files(company, start, end, entries)
	files += [
		(
			f"livres-{fiscal_year}.xlsx",
			tables.to_xlsx(books),
			_("Balance, grand livre, journal centralisateur"),
		),
		(
			f"etats-{fiscal_year}.pdf",
			tables.to_pdf(statements, heading),
			_("États financiers SCF et balance"),
		),
		(
			f"journal-audit-{fiscal_year}.csv",
			tables.to_csv(audit_table(company, start, end)),
			_("Journal d'audit"),
		),
	]
	archive = keep(company, YEARLY, files, start, end, fiscal_year=fiscal_year)
	return archive.name


def audit_table(company, start, end):
	from dz_core.books.tables import DATE, TEXT, table

	rows = frappe.get_all(
		"DZ Audit Log",
		filters={"creation": ["between", [f"{start} 00:00:00", f"{end} 23:59:59"]]},
		fields=[
			"creation",
			"operation",
			"reference_doctype",
			"reference_name",
			"user",
			"ip_address",
			"device",
			"details",
			"company",
		],
		order_by="creation",
	)
	return table(
		_("Journal d'audit"),
		[
			(_("Date et heure"), DATE),
			(_("Opération"), TEXT),
			(_("Type"), TEXT),
			(_("Document"), TEXT),
			(_("Utilisateur"), TEXT),
			(_("Adresse IP"), TEXT),
			(_("Poste"), TEXT),
			(_("Détails"), TEXT),
		],
		[
			[
				r.creation,
				r.operation,
				r.reference_doctype,
				r.reference_name,
				r.user,
				r.ip_address,
				r.device,
				r.details,
			]
			for r in rows
			if not r.company or r.company == company
		],
	)


def protect_file(doc, method=None):
	"""File on_trash (hooks.py): an archived file stays."""
	if doc.attached_to_doctype == "DZ Archive" and not frappe.flags.dz_wipe:
		frappe.throw(_("Ce fichier est archivé : il ne se supprime pas (conservation 10 ans, art. 64 CPF)."))
