"""Accounts of a client company on ERPNext's Algerian chart of accounts.

The setup wizard fills the Company's default accounts with the last account
of each type in the chart, rarely the right one for this chart: receivables
in 4172 "Créances sur prestations en cours", suppliers in 4213 "Soldes de tout
compte restant dus" (a salary account), the bank in 5176 "Société de bourse",
stock in 3451 "Prestations de services"... `set_default_accounts` puts the
SCF accounts in their place, by account number (DECISIONS.md, "Default
accounts", lists them and what the accountant must confirm). A default that
is not the wizard's pick any more was chosen by someone and is kept.

The chart has no ledger account for finished goods (3551 is a group), so
35511 "Produits finis" is added under it.

ERPNext's standard chart also has a "Temporary Opening" account for opening
balances (opening stock, opening receivables). The Algerian chart shipped
with ERPNext has none, and an Opening Stock reconciliation refuses to post
without an asset or liability account of type "Temporary". So one is added
under the liability root.

To check with the accountant: which SCF account the opening balances should
finally be cleared to, and the choices of DECISIONS.md "Default accounts".
"""

import frappe

OPENING_ACCOUNT = "Ouverture temporaire"

# The finished goods ledger the chart lacks: (number, name, parent group's number)
FINISHED_GOODS = ("35511", "Produits finis", "3551")

# Company field -> (SCF account number we use, the one the wizard puts there)
COMPANY_ACCOUNTS = {
	"default_receivable_account": ("4111", "4172"),  # Clients : Ventes de biens et services
	"default_payable_account": ("40132", "4213"),  # Fournisseurs de stocks : Nationaux, Privés
	"default_bank_account": ("5121", "5176"),  # Comptes bancaires : Dinars
	"default_cash_account": ("5311", "5322"),  # Caisse principale en Dinars
	"stock_received_but_not_billed": ("4081", "4088"),  # Fournisseurs de stocks : factures non parvenues
	"default_inventory_account": (FINISHED_GOODS[0], "3451"),  # Produits finis (warehouses below)
	"stock_adjustment_account": ("6031", "6032"),  # Variation des stocks de matières premières & fournitures
	"default_income_account": ("7011", "7001"),  # Ventes de produits finis
	# Cost of the products sold: "déstockage" of finished goods, 7245 Variation
	# de stocks de produits finis (the wizard's 6078 is a non-stock supply account)
	"default_expense_account": ("7245", "6078"),
	"round_off_account": ("6588", "766"),  # Autres charges diverses de gestion courante
	"depreciation_expense_account": ("6812", "6862"),  # Dotations : immobilisations corporelles
	"capital_work_in_progress_account": ("2328", "237"),  # Autres immobilisations corporelles en cours
}
# DZ Core Settings warehouse field -> stock account
WAREHOUSE_ACCOUNTS = {
	"raw_materials_warehouse": "311",  # Matières premières
	"wip_warehouse": "3311",  # Produits en cours
	"finished_goods_warehouse": FINISHED_GOODS[0],
}


def opening_account(company):
	"""The company's Temporary account, created under the liability root if missing."""
	name = frappe.db.get_value("Account", {"company": company, "account_type": "Temporary", "is_group": 0})
	if name:
		return name
	parent = frappe.db.get_value(
		"Account",
		{"company": company, "root_type": "Liability", "is_group": 1, "parent_account": ["is", "not set"]},
	)
	doc = frappe.get_doc(
		{
			"doctype": "Account",
			"account_name": OPENING_ACCOUNT,
			"company": company,
			"parent_account": parent,
			"account_type": "Temporary",
			"is_group": 0,
		}
	).insert(ignore_permissions=True)
	return doc.name


def account_by_number(company, number):
	"""The company's ledger (not group) account with this SCF number, if any."""
	return frappe.db.get_value("Account", {"company": company, "account_number": number, "is_group": 0})


def finished_goods_account(company):
	"""35511 "Produits finis", created under the group 3551 if missing (None
	on a chart without that group)."""
	number, name, parent_number = FINISHED_GOODS
	account = account_by_number(company, number)
	if account:
		return account
	parent = frappe.db.get_value(
		"Account", {"company": company, "account_number": parent_number, "is_group": 1}
	)
	if not parent:
		return None
	doc = frappe.get_doc(
		{
			"doctype": "Account",
			"account_name": name,
			"account_number": number,
			"company": company,
			"parent_account": parent,
			"account_type": "Stock",
			"is_group": 0,
		}
	).insert(ignore_permissions=True)
	return doc.name


def set_default_accounts(company):
	"""Put the SCF accounts in the Company's defaults and its warehouses,
	where the wizard's pick (or nothing) is. Returns {field: (old, new)} for
	the Company defaults that changed."""
	finished_goods_account(company)
	changes = {}
	for field, (number, wizard_pick) in COMPANY_ACCOUNTS.items():
		current = frappe.db.get_value("Company", company, field)
		if current and frappe.db.get_value("Account", current, "account_number") != wizard_pick:
			continue  # someone's choice
		account = account_by_number(company, number)
		if account and account != current:
			changes[field] = (current, account)
	if changes:
		frappe.db.set_value("Company", company, {field: new for field, (_old, new) in changes.items()})
		frappe.clear_document_cache("Company", company)
	follow_payment_modes(company, {old: new for old, new in changes.values() if old})
	set_warehouse_accounts(company)
	return changes


def follow_payment_modes(company, replaced):
	"""Modes of payment pointing to a replaced default (the wizard sets Cash to
	the cash default) point to its successor."""
	for row in frappe.get_all(
		"Mode of Payment Account",
		filters={"company": company, "default_account": ["in", list(replaced) or [""]]},
		fields=["name", "default_account"],
	):
		frappe.db.set_value(
			"Mode of Payment Account", row.name, "default_account", replaced[row.default_account]
		)


def set_warehouse_accounts(company):
	"""The three dz_core warehouses of the company get their stock account, if
	they have none (a warehouse without one uses the Company's default)."""
	settings = frappe.get_single("DZ Core Settings")
	if settings.company != company:
		return
	for field, number in WAREHOUSE_ACCOUNTS.items():
		warehouse = settings.get(field)
		account = account_by_number(company, number)
		if warehouse and account and not frappe.db.get_value("Warehouse", warehouse, "account"):
			frappe.db.set_value("Warehouse", warehouse, "account", account)
