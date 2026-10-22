"""DZ Archive: files kept with their SHA-256 (dz_core/books/archive.py).

Made only by code (books.archive.keep), never changed, never deleted: the
demo wipe alone may remove one (frappe.flags.dz_wipe).
"""

import frappe
from frappe import _
from frappe.model.document import Document


class DZArchive(Document):
	def validate(self):
		if not self.flags.dz_internal:
			frappe.throw(_("Une archive est faite par Daftar et ne se modifie pas."))

	def on_trash(self):
		if not frappe.flags.dz_wipe:
			frappe.throw(_("Une archive ne se supprime pas (conservation 10 ans, art. 64 CPF)."))
