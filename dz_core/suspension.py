"""A suspended client (unpaid subscription) can still log in, read and export
their books, but nothing can be saved, submitted, cancelled or deleted
(review of 27 October 2026, 3.5; decision D2 by Adem on 29 October 2026).

The hub's "Suspendre" sets the site_config key `dz_suspended` (and pauses
the scheduler); "Réactiver" clears both. A running site reads its config
again within about a minute.

Why not Frappe's maintenance mode with reads allowed: in that mode the
database is read-only, and a login must write its session, so a suspended
client could not even log in to read their books (tried on 30 October 2026:
503 InReadOnlyMode on /api/method/login). The client must be able to keep
and consult their books for ten years (CPF art. 64), paid up or not.

How: a doc_events "*" hook on every save, submit, change after submit
(a workflow step on a submitted order: Frappe runs before_validate only on
save and submit), cancel and delete. The records Frappe and Daftar write
while a user only reads (logs, the audit trail, a report run in the
background) stay allowed, and so do the archives an export or a closing
file writes (DZ Archive and its files), or the books could not be exported.
Writes that skip documents (db_set, raw SQL in code) are not stopped: this
is a lock on the user's actions, not on the database.
"""

import frappe
from frappe import _

KEY = "dz_suspended"
# Written while a user only reads, logs in or exports
ALLOWED = {
	"Access Log",
	"Activity Log",
	"Comment",
	"DZ Audit Log",
	"Error Log",
	"Prepared Report",
	"Route History",
	"Scheduled Job Log",
	"Version",
}


def suspended():
	return bool(frappe.conf.get(KEY))


def check(doc, method=None):
	"""doc_events "*": refuse a change while the site is suspended."""
	if not suspended() or doc.doctype in ALLOWED:
		return
	if doc.doctype == "DZ Archive" and doc.flags.dz_internal:
		return  # written by an export or a closing file (books/archive.keep)
	if doc.doctype == "File" and doc.attached_to_doctype == "DZ Archive":
		return  # that archive's files; other uploads stay refused
	if frappe.flags.in_migrate or frappe.flags.in_install or frappe.flags.in_patch:
		return
	frappe.throw(
		_(
			"Abonnement suspendu : vos données restent consultables et exportables, mais rien ne "
			"peut être enregistré. Contactez votre fournisseur pour réactiver l'abonnement."
		),
		title=_("Abonnement suspendu"),
	)
