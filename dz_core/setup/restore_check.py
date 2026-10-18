"""What scripts/restore_test.sh compares between a live site and its restored copy.

    bench --site <site> execute dz_core.setup.restore_check.summary

prints one JSON object: how many records of each kind, the date of the last
invoice, and whether every stored password can be decrypted (it can only if
the site has the right encryption_key in site_config.json).

Copied from dz_cod and made generic: it counts what every client has.
dz_cod sites can keep using dz_cod's own version, which counts COD records.
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


def summary():
	result = {doctype: frappe.db.count(doctype) for doctype in COUNTED}
	last = frappe.get_all("Sales Invoice", fields=["creation"], order_by="creation desc", limit=1)
	result["last_invoice"] = str(last[0].creation) if last else ""
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
