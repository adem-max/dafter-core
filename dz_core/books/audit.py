"""The audit trail (decree 09-110 art. 18: author, workstation, date, time,
operation), in DZ Audit Log.

ERPNext's Version log keeps who changed a document and when, not from where,
and its Activity Log is pruned after 90 days. So every validation,
cancellation and change after validation of the documents listed in hooks.py
(AUDITED) writes one DZ Audit Log row with the user, the IP address and the browser (User-Agent);
a background job or the console writes "système" as the workstation. So does
every change of the company's "Accounts Frozen Till Date" (the monthly
freeze, closing.freeze_month, or the Company form).
"""

import frappe
from frappe import _

OPERATIONS = {
	"on_submit": "Validation",
	"on_cancel": "Annulation",
	"on_update_after_submit": "Modification après validation",
}
FREEZE = "Gel des écritures"
SYSTEM = "système (tâche de fond ou console)"


def log(doc, method=None):
	"""doc_events on_submit, on_cancel, on_update_after_submit (hooks.py)."""
	details = ""
	if method == "on_submit" and doc.get("amended_from"):
		details = _("Remplace {0}").format(doc.amended_from)
	write(OPERATIONS.get(method, method), doc.doctype, doc.name, doc.get("company"), details)


def log_frozen_date(doc, method=None):
	"""Company on_update (hooks.py): the freeze date changed in the form."""
	before = doc.get_doc_before_save()
	if before and before.accounts_frozen_till_date != doc.accounts_frozen_till_date:
		frozen(doc.name, before.accounts_frozen_till_date, doc.accounts_frozen_till_date)


def frozen(company, before, after):
	write(FREEZE, "Company", company, company, f"{before or '-'} -> {after or '-'}")


def write(operation, doctype, name, company=None, details=""):
	request = getattr(frappe.local, "request", None)
	device = request.headers.get("User-Agent") if request else None
	frappe.get_doc(
		{
			"doctype": "DZ Audit Log",
			"operation": operation,
			"reference_doctype": doctype,
			"reference_name": name,
			"company": company,
			"user": frappe.session.user,
			"ip_address": getattr(frappe.local, "request_ip", None) if request else None,
			"device": device or SYSTEM,
			"details": details,
		}
	).insert(ignore_permissions=True)
