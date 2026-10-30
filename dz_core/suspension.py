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

How: a doc_events "*" hook on every save, submit, cancel and delete. The
records Frappe and Daftar write while a user only reads (logs, the audit
trail, a report run in the background) stay allowed. Writes that skip
documents (db_set, raw SQL in code) are not stopped: this is a lock on the
user's actions, not on the database.
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
	if frappe.flags.in_migrate or frappe.flags.in_install or frappe.flags.in_patch:
		return
	frappe.throw(
		_(
			"Abonnement suspendu : vos données restent consultables et exportables, mais rien ne "
			"peut être enregistré. Contactez votre fournisseur pour réactiver l'abonnement."
		),
		title=_("Abonnement suspendu"),
	)
