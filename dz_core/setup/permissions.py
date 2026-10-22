"""Nobody deletes an accounting or stock document, not even a draft: a
deleted draft leaves a hole in its numbering series, and decree 09-110
(art. 13, 17) asks for continuous numbering and validated entries that
never change. Cancelling stays possible: with the immutable ledger
(setup/accounts.py) it posts a dated reversal.

"Delete Transactions" on the Company (a Transaction Deletion Record) is
refused to every role for the same reason.

Done through Custom DocPerm (Role Permissions Manager), so it survives
ERPNext updates. The Administrator and code that ignores permissions (the
demo wipe) are not affected.
"""

import frappe
from frappe.permissions import setup_custom_perms, update_permission_property

NO_DELETE = [
	"Sales Invoice",
	"Purchase Invoice",
	"Payment Entry",
	"Journal Entry",
	"Stock Entry",
	"Stock Reconciliation",
	"Delivery Note",
	"Purchase Receipt",
]
NO_CREATE = ["Transaction Deletion Record"]


def lock_deletions():
	"""Returns the (doctype, role, right) taken away."""
	removed = []
	for doctype, right in [(d, "delete") for d in NO_DELETE] + [(d, "create") for d in NO_CREATE]:
		setup_custom_perms(doctype)
		for perm in frappe.get_all(
			"Custom DocPerm", filters={"parent": doctype, right: 1}, fields=["role", "permlevel"]
		):
			update_permission_property(doctype, perm.role, perm.permlevel, right, 0, validate=False)
			removed.append((doctype, perm.role, right))
	if removed:
		frappe.clear_cache()
	return removed
