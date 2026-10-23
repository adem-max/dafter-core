"""Nobody deletes an accounting or stock document, not even a draft: a
deleted draft leaves a hole in its numbering series, and decree 09-110
(art. 13, 17) asks for continuous numbering and validated entries that
never change. Cancelling stays possible: with the immutable ledger
(setup/accounts.py) it posts a dated reversal.

The documents are the ones the audit trail follows (hooks.py AUDITED, but
for the assets: STILL_DELETABLE below), plus
those apps on top declare with a `dz_no_delete` hook (dz_cod: Courier
Settlement). "Delete Transactions" on the Company (a Transaction Deletion
Record) is refused to every role for the same reason.

Done through Custom DocPerm (Role Permissions Manager), so it survives
ERPNext updates, and done again after every migrate, so a right given back
by hand does not last. The Administrator and code that ignores permissions
(the demo wipes) are not affected: a deletion by them goes to the audit
trail (books/audit.py).
"""

import frappe
from frappe.permissions import setup_custom_perms, update_permission_property

from dz_core.hooks import AUDITED

NO_CREATE = ["Transaction Deletion Record"]
# Audited, but deletable: ERPNext deletes the draft assets it made when their
# purchase receipt or invoice is cancelled, as the user who cancels. An asset
# posts nothing while it is a draft.
STILL_DELETABLE = ["Asset"]


def no_delete():
	"""The doctypes nobody may delete: dz_core's and the apps' on top."""
	names = [name for name in AUDITED if name not in STILL_DELETABLE]
	return names + [name for name in frappe.get_hooks("dz_no_delete") if name not in names]


def lock_deletions():
	"""Returns the (doctype, role, right) taken away."""
	removed = []
	for doctype, right in [(d, "delete") for d in no_delete()] + [(d, "create") for d in NO_CREATE]:
		setup_custom_perms(doctype)
		for perm in frappe.get_all(
			"Custom DocPerm", filters={"parent": doctype, right: 1}, fields=["role", "permlevel"]
		):
			update_permission_property(doctype, perm.role, perm.permlevel, right, 0, validate=False)
			removed.append((doctype, perm.role, right))
	if removed:
		frappe.clear_cache()
	return removed
