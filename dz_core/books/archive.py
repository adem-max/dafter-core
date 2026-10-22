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
		content = frappe.get_doc("File", {"file_url": row.file, "attached_to_name": doc.name}).get_content()
		if isinstance(content, str):
			content = content.encode("utf-8")
		result.append([row.file_name, sha256(content) == row.sha256])
	return result


def protect_file(doc, method=None):
	"""File on_trash (hooks.py): an archived file stays."""
	if doc.attached_to_doctype == "DZ Archive" and not frappe.flags.dz_wipe:
		frappe.throw(_("Ce fichier est archivé : il ne se supprime pas (conservation 10 ans, art. 64 CPF)."))
