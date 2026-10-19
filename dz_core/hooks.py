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

# Custom fields for the legal mentions (dz_core/setup/custom_fields.py)
after_install = "dz_core.setup.install.after_install"
after_migrate = "dz_core.setup.install.after_migrate"

# Optional features per client (dz_core/features.py). Apps declare theirs with
# a `dz_features` hook; dz_core has none of its own yet.
extend_bootinfo = ["dz_core.features.boot"]

# One format for customer phones (dz_core/phone.py)
doc_events = {"Customer": {"validate": "dz_core.phone.normalize_customer_phone"}}

# montant() and montant_en_lettres() in print formats (dz_core/utils.py)
jinja = {"methods": ["dz_core.utils.montant", "dz_core.utils.montant_en_lettres"]}
