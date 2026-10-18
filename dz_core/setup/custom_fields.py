"""Custom fields for Algerian legal mentions (decree 05-468 on invoices).

Every field starts with "dz_" like in dz_cod. Names used here never clash
with dz_cod's fields: keep it that way when adding new ones (search both
repos for the fieldname first).

What the decree asks for, and where it lives:
- seller: name, legal form, nature of activity, address, RC (or
  auto-entrepreneur card), NIF, NIS, tax article, share capital for a company
  -> Company fields below (name and address are ERPNext's own)
- buyer who is a business: name, address, RC, NIF, NIS, tax article
  -> Customer fields below
- payment method and payment date -> Sales Invoice "dz_payment_mode" and
  ERPNext's own due date

The exact list must be checked with an accountant before a client goes live.
"""

from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

LEGAL_FORMS = "\nAuto-entrepreneur\nPersonne physique\nEURL\nSARL\nSPA\nSNC\nAutre"
PAYMENT_MODES = "\nEspèces\nChèque\nVirement\nCCP / BaridiMob\nCarte (TPE)\nÀ terme"

COMPANY_FIELDS = [
	{
		"fieldname": "dz_legal_section",
		"label": "Mentions légales (facture)",
		"fieldtype": "Section Break",
		"insert_after": "tax_id",
		"collapsible": 0,
	},
	{
		"fieldname": "dz_legal_form",
		"label": "Forme juridique",
		"fieldtype": "Select",
		"options": LEGAL_FORMS,
		"insert_after": "dz_legal_section",
	},
	{
		"fieldname": "dz_activity",
		"label": "Nature de l'activité",
		"fieldtype": "Data",
		"insert_after": "dz_legal_form",
	},
	{
		"fieldname": "dz_rc",
		"label": "N° RC ou carte auto-entrepreneur",
		"fieldtype": "Data",
		"insert_after": "dz_activity",
	},
	{
		"fieldname": "dz_capital",
		"label": "Capital social (DA)",
		"fieldtype": "Currency",
		"insert_after": "dz_rc",
		"depends_on": "eval:['EURL','SARL','SPA','SNC'].includes(doc.dz_legal_form)",
	},
	{"fieldname": "dz_legal_column", "fieldtype": "Column Break", "insert_after": "dz_capital"},
	{"fieldname": "dz_nif", "label": "NIF", "fieldtype": "Data", "insert_after": "dz_legal_column"},
	{"fieldname": "dz_nis", "label": "NIS", "fieldtype": "Data", "insert_after": "dz_nif"},
	{"fieldname": "dz_ai", "label": "Article d'imposition", "fieldtype": "Data", "insert_after": "dz_nis"},
]

CUSTOMER_FIELDS = [
	{
		"fieldname": "dz_legal_section",
		"label": "Identifiants (client professionnel)",
		"fieldtype": "Section Break",
		"insert_after": "tax_id",
		"collapsible": 1,
		"description": "Seulement pour les clients professionnels : imprimés sur leurs factures.",
	},
	{"fieldname": "dz_rc", "label": "N° RC", "fieldtype": "Data", "insert_after": "dz_legal_section"},
	{"fieldname": "dz_nif", "label": "NIF", "fieldtype": "Data", "insert_after": "dz_rc"},
	{"fieldname": "dz_legal_column", "fieldtype": "Column Break", "insert_after": "dz_nif"},
	{"fieldname": "dz_nis", "label": "NIS", "fieldtype": "Data", "insert_after": "dz_legal_column"},
	{"fieldname": "dz_ai", "label": "Article d'imposition", "fieldtype": "Data", "insert_after": "dz_nis"},
]

SALES_INVOICE_FIELDS = [
	{
		"fieldname": "dz_payment_mode",
		"label": "Mode de paiement",
		"fieldtype": "Select",
		"options": PAYMENT_MODES,
		"insert_after": "due_date",
		"allow_on_submit": 1,
		"print_hide": 1,
	},
]


def setup_custom_fields():
	"""Create or update all custom fields. Safe to run many times."""
	create_custom_fields(
		{
			"Company": COMPANY_FIELDS,
			"Customer": CUSTOMER_FIELDS,
			"Sales Invoice": SALES_INVOICE_FIELDS,
		},
		update=True,
	)
