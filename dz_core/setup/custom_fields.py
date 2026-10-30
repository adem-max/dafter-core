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

Customer phone (normalized, dz_core/phone.py) and wilaya (DZ Wilaya) are here
too: every client has customers somewhere in Algeria.

The exact list must be checked with an accountant before a client goes live.
"""

from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

LEGAL_FORMS = "\nAuto-entrepreneur\nPersonne physique\nEURL\nSARL\nSPA\nSNC\nAutre"
# Contre-remboursement: an online order paid to the courier on delivery (dz_cod invoices it)
PAYMENT_MODES = "\nEspèces\nChèque\nVirement\nCCP / BaridiMob\nCarte (TPE)\nContre-remboursement\nÀ terme"

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
	# Phone and wilaya: every client needs them (moved from dz_cod, which adds
	# commune and address to the same section for its delivery snapshot)
	{
		"fieldname": "dz_section",
		"label": "Coordonnées",
		"fieldtype": "Section Break",
		"insert_after": "customer_group",
	},
	{
		"fieldname": "dz_phone",
		"label": "Téléphone",
		"fieldtype": "Data",
		"options": "Phone",
		"insert_after": "dz_section",
		"in_standard_filter": 1,
		"in_global_search": 1,
		# looked up by dz_cod's phone checks on every order (review of 27 October 2026, 4.1)
		"search_index": 1,
	},
	{
		"fieldname": "dz_wilaya",
		"label": "Wilaya",
		"fieldtype": "Link",
		"options": "DZ Wilaya",
		"insert_after": "dz_phone",
		"in_standard_filter": 1,
	},
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
	# a cheque or a transfer whose references are on the invoice owes no stamp
	# duty (code du timbre art. 258; dz_core/stamp.py)
	{
		"fieldname": "dz_payment_reference",
		"label": "N° du chèque ou référence du virement",
		"fieldtype": "Data",
		"insert_after": "dz_payment_mode",
		"depends_on": "eval:['Chèque', 'Virement'].includes(doc.dz_payment_mode)",
		"print_hide": 1,
	},
	{
		"fieldname": "dz_payment_reference_date",
		"label": "Date du chèque ou du virement",
		"fieldtype": "Date",
		"insert_after": "dz_payment_reference",
		"depends_on": "eval:['Chèque', 'Virement'].includes(doc.dz_payment_mode)",
		"print_hide": 1,
	},
	{
		"fieldname": "dz_payment_bank",
		"label": "Banque tirée ou banques du virement",
		"fieldtype": "Data",
		"insert_after": "dz_payment_reference_date",
		"depends_on": "eval:['Chèque', 'Virement'].includes(doc.dz_payment_mode)",
		"print_hide": 1,
	},
]

# A purchase without an invoice (informal supplier): recorded, never with TVA,
# listed as likely non-deductible (dz_core/tax_checks.py)
PURCHASE_INVOICE_FIELDS = [
	{
		"fieldname": "dz_no_invoice",
		"label": "Sans facture (justificatif interne)",
		"fieldtype": "Check",
		"insert_after": "bill_date",
		"description": "Achat sans facture du fournisseur : bon d'achat interne signé par le vendeur. "
		"Pas de TVA déductible ; la charge est probablement non déductible.",
	},
]

# Why stock went out without a sale: losses and gifts give back their TVA on
# the régime réel (CTCA arts. 37-a, 41-5; dz_core/tax_checks.py)
STOCK_ENTRY_FIELDS = [
	{
		"fieldname": "dz_issue_reason",
		"label": "Motif de la sortie",
		"fieldtype": "Select",
		"options": "\nCasse ou vol\nÉchantillons et cadeaux\nDestruction\nForce majeure",
		"insert_after": "stock_entry_type",
		"depends_on": "eval:doc.stock_entry_type == 'Material Issue'",
		"allow_on_submit": 1,
	},
]


# The entries Daftar makes once a month or once a year (TVA settlement, 4081
# reclassification, TVA on losses, IFU) are found by this key, never by their
# remark: the remark is translated, and a user may type the same words
# (closing.closing_key; review of 27 October 2026, 2.5)
JOURNAL_ENTRY_FIELDS = [
	{
		"fieldname": "dz_closing_key",
		"label": "Clé de clôture Daftar",
		"fieldtype": "Data",
		"insert_after": "user_remark",
		"read_only": 1,
		"no_copy": 1,
		"search_index": 1,
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
			"Purchase Invoice": PURCHASE_INVOICE_FIELDS,
			"Stock Entry": STOCK_ENTRY_FIELDS,
			"Journal Entry": JOURNAL_ENTRY_FIELDS,
		},
		update=True,
	)
