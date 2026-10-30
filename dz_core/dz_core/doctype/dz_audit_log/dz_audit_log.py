"""DZ Audit Log: one row per validation, cancellation or change after
validation of an accounting or stock document (dz_core/books/audit.py).

Not ERPNext's Activity Log, which Log Settings prunes after 90 days: the
audit trail is kept with the books. Never changed, never deleted (the demo
wipe alone may, frappe.flags.dz_wipe).
"""

import frappe
from frappe import _
from frappe.model.document import Document


class DZAuditLog(Document):
	def validate(self):
		if not self.is_new():
			frappe.throw(_("Le journal d'audit ne se modifie pas."))

	def db_insert(self, *args, **kwargs):
		# here the row's name and time are final: chain it (books/audit_chain.py)
		from dz_core.books.audit_chain import link

		link(self)
		return super().db_insert(*args, **kwargs)

	def on_trash(self):
		if not frappe.flags.dz_wipe:
			frappe.throw(_("Le journal d'audit ne se supprime pas."))
