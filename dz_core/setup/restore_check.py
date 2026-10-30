"""What scripts/restore_test.sh compares between a live site and its restored copy.

    bench --site <site> execute dz_core.setup.restore_check.summary

prints one JSON object: how many records of each kind, the date of the last
invoice, and whether every stored password can be decrypted (it can only if
the site has the right encryption_key in site_config.json).

It counts what every client has. An app on top adds its own records with two
hooks in its hooks.py (dz_cod adds its orders and Versements):

    dz_restore_check_counted = ["Sales Order", "Courier Settlement"]
    dz_restore_check_last = ["Sales Order"]   # date of the newest one
"""

import frappe
from frappe.utils.password import decrypt

COUNTED = [
	"Sales Invoice",
	"Delivery Note",
	"Purchase Receipt",
	"Work Order",
	"BOM",
	"Customer",
	"Supplier",
	"Item",
	"Stock Ledger Entry",
	"GL Entry",
	"File",
	"User",
]


# The newest record of these is shown with its date
LAST = ["Sales Invoice"]


def with_hooks(names, hook):
	return names + [name for name in frappe.get_hooks(hook) if name not in names]


def summary(until=None):
	"""`until` (the backup's time): count only what existed then. The live site
	keeps working after its backup, so restore_test.sh compares the copy with
	the live site *as it was at the backup*: the copy must hold at least that
	much (review of 20 October 2026, 3.2: a copy that lost 90 % of the invoices
	used to pass, as only "more than live" or "zero" failed)."""
	filters = {"creation": ["<=", until]} if until else {}
	result = {
		doctype: frappe.db.count(doctype, filters)
		for doctype in with_hooks(COUNTED, "dz_restore_check_counted")
	}
	for doctype in with_hooks(LAST, "dz_restore_check_last"):
		last = frappe.get_all(
			doctype, filters=filters, fields=["creation"], order_by="creation desc", limit=1
		)
		result[f"last {doctype}"] = str(last[0].creation) if last else ""
	result["passwords"], result["passwords_unreadable"] = check_passwords()
	return result


def check_passwords():
	"""(stored passwords, how many cannot be decrypted with this site's key)."""
	rows = frappe.db.sql("select password from `__Auth` where encrypted = 1", as_dict=True)
	unreadable = 0
	for row in rows:
		try:
			decrypt(row.password)
		except Exception:
			unreadable += 1
	frappe.clear_messages()  # decrypt() leaves an error message per failure
	return len(rows), unreadable
