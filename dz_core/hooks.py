"""Frappe reads this file to know how dz_core plugs into ERPNext.

dz_core is the base every client gets: setup, sector templates, legal
invoices, import workbook, wilayas, phone numbers, backups. Online sellers
also get dz_cod, which runs on top of it.

Only the hooks we actually use are listed. For all possible hooks see
https://docs.frappe.io/framework/user/en/python-api/hooks
"""

app_name = "dz_core"
app_title = "DZ Core"
app_publisher = "Adem"
app_description = "Algerian base for small producers on ERPNext"
app_email = "adembenlecheb1@gmail.com"
app_license = "mit"

required_apps = ["erpnext"]

# Where to land after login: the Atelier home page (dz_core/dz_core/workspace/atelier).
# Atelier is docked on ERPNext's rail (dz_core/dock), so Frappe keeps it off the
# apps screen, but this route is used when dz_core is the site's default app
# (System Settings > default_app, set by new_client.prepare and the demo loader).
add_to_apps_screen = [
	{
		"name": "dz_core",
		"logo": "/assets/dz_core/images/atelier-logo.svg",
		"title": "Atelier",
		"route": "/desk/atelier",
		"has_permission": "erpnext.check_app_permission",
	}
]
# Frappe sends desk users to /desk after login: open the default app instead
get_website_user_home_page = "dz_core.setup.new_client.home_page_after_login"

# Custom fields for the legal mentions (dz_core/setup/custom_fields.py)
after_install = "dz_core.setup.install.after_install"
after_migrate = "dz_core.setup.install.after_migrate"

# Optional features per client (dz_core/features.py). Apps declare theirs with
# a `dz_features` hook; dz_core has none of its own yet.
extend_bootinfo = ["dz_core.features.boot"]

# The audit trail: who validated, cancelled, changed or deleted what, from where
# (books/audit.py). The documents that post to the ledgers: audited here, and
# nobody may delete one, assets aside (setup/permissions.py). Apps on top add theirs with a
# `dz_no_delete` hook and the same doc_events (dz_cod: Courier Settlement).
AUDIT = {
	"on_submit": "dz_core.books.audit.log",
	"on_cancel": "dz_core.books.audit.log",
	"on_update_after_submit": "dz_core.books.audit.log",
	"on_trash": "dz_core.books.audit.log",
}
AUDITED = [
	"Sales Invoice",
	"Purchase Invoice",
	"Payment Entry",
	"Journal Entry",
	"Stock Entry",
	"Stock Reconciliation",
	"Delivery Note",
	"Purchase Receipt",
	"Landed Cost Voucher",
	"Period Closing Voucher",
	"Subcontracting Receipt",
	"Asset",
	"Asset Capitalization",
	"Asset Repair",
	"Asset Value Adjustment",
	"Invoice Discounting",
	"Process Deferred Accounting",
]
# The audit trail points at the documents it records: a deletion (audited
# above, on_trash runs before Frappe's link check) must not be refused for it
ignore_links_on_delete = ["DZ Audit Log"]

doc_events = {
	**{doctype: dict(AUDIT) for doctype in AUDITED},
	# One format for customer phones (dz_core/phone.py)
	"Customer": {"validate": "dz_core.phone.normalize_customer_phone"},
	# a new item group gets its parent's accounts (setup/item_groups.py)
	"Item Group": {"before_insert": "dz_core.setup.item_groups.inherit_parent_accounts"},
	# a manufacture posts consumption (60x) and production stocked (72) (production.py)
	"Stock Entry": {"validate": "dz_core.production.production_accounts", **AUDIT},
	# stamp duty on cash receipts (stamp.py)
	"Sales Invoice": {"validate": "dz_core.stamp.apply_stamp", **AUDIT},
	"Payment Entry": {
		"validate": ["dz_core.stamp.warn_cash_payment", "dz_core.tax_checks.cash_payment_checks"],
		**AUDIT,
	},
	# low-value equipment, purchases without an invoice (tax_checks.py)
	"Purchase Invoice": {"validate": "dz_core.tax_checks.purchase_invoice_checks", **AUDIT},
	# changes of "Accounts Frozen Till Date" go to the audit trail
	"Company": {"on_update": "dz_core.books.audit.log_frozen_date"},
	# archived files stay (books/archive.py)
	"File": {"on_trash": "dz_core.books.archive.protect_file"},
	# a suspended client reads and exports, saves nothing (suspension.py)
	"*": {
		event: "dz_core.suspension.check"
		for event in ("before_validate", "before_submit", "before_cancel", "on_trash")
	},
}

# montant() and montant_en_lettres() in print formats (dz_core/utils.py)
jinja = {"methods": ["dz_core.utils.montant", "dz_core.utils.montant_en_lettres"]}
