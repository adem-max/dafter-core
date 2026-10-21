"""Default accounts and accounting settings of a client company on ERPNext's
Algerian chart of accounts (DECISIONS.md, "Chart of accounts and default
accounts", from the SCF advice of 21 October 2026).

The setup wizard fills the Company's default accounts with the last account
of each type in the chart, rarely the right one: receivables in 4172
"Créances sur prestations en cours", suppliers in 4213 "Soldes de tout compte
restant dus" (a salary account), the bank in 5176 "Société de bourse", stock
in 3451 "Prestations de services"... `set_default_accounts` puts the SCF
accounts there, by number. It replaces only an empty default, the wizard's
pick or what an earlier Daftar version set (REPLACEABLE): a default someone
chose is kept.

`set_accounting_settings` switches on what the advice asks for before the
first entry: inventory accounts per item (group) instead of per warehouse,
moving average valuation, advances in their own accounts, an immutable
ledger whose entries are never deleted. The first two are refused by ERPNext
once the company has stock entries; such a company keeps its warehouse
accounts (set_warehouse_accounts).

ERPNext's standard chart also has a "Temporary Opening" account for opening
balances (opening stock, opening receivables). The Algerian chart shipped
with ERPNext has none, and an Opening Stock reconciliation refuses to post
without an asset or liability account of type "Temporary". So one is added;
setup/chart.py then files it as 479 under class 47.
"""

import frappe

OPENING_ACCOUNT = "Ouverture temporaire"

# Company field -> SCF account numbers, in order of preference: the first that
# exists as a ledger is used (65881 needs 6588 turned into a group first)
COMPANY_ACCOUNTS = {
	"default_receivable_account": ("4111",),  # Clients : ventes de biens et services
	"default_payable_account": ("40132",),  # Fournisseurs de stocks : nationaux, privés
	"default_bank_account": ("5121",),  # Comptes bancaires : dinars
	"default_cash_account": ("5311",),  # Caisse principale en dinars
	"stock_received_but_not_billed": ("4081",),  # Fournisseurs de stocks : factures non parvenues
	"default_inventory_account": ("35511",),  # Produits finis (item groups decide, see item_groups.py)
	"stock_adjustment_account": ("6572", "6031"),  # Écart de stocks (négatif) de matières
	"default_income_account": ("7011",),  # Ventes de produits finis (item groups decide)
	# What no item group covers, and invoice / receipt differences: checked
	# and reclassified every month, never left there at the year end
	"default_expense_account": ("6589",),
	"service_expense_account": ("6589",),
	"round_off_account": ("65881", "6588"),  # Écarts d'arrondi
	"round_off_for_opening": ("479",),  # Ouverture temporaire
	"write_off_account": ("65882", "6588"),  # Écarts de règlement (pertes)
	"default_discount_account": ("668",),  # Autres charges financières (escompte)
	"exchange_gain_loss_account": ("666",),  # Pertes de change (gains moved to 766 at the year end)
	"unrealized_exchange_gain_loss_account": ("666",),
	"disposal_account": ("6528",),  # Moins-values (plus-values moved to 7528 at the year end)
	"asset_received_but_not_billed": ("4083",),
	"depreciation_expense_account": ("6812",),  # Dotations : immobilisations corporelles
	"capital_work_in_progress_account": ("2328",),
	"accumulated_depreciation_account": ("2818",),
	"default_advance_received_account": ("4191",),  # Clients : avances et acomptes reçus
	"default_advance_paid_account": ("40913",),  # Avances et acomptes sur stocks
}

# What the setup wizard puts in each field with this chart, and what Daftar
# 0.2.0 set (21 Oct 2026): replaced. Anything else was chosen and is kept.
REPLACEABLE = {
	"default_receivable_account": {"4172"},
	"default_payable_account": {"4213"},
	"default_bank_account": {"5176"},
	"default_cash_account": {"5322"},
	"stock_received_but_not_billed": {"4088"},
	"default_inventory_account": {"3451"},
	"stock_adjustment_account": {"6032", "6031"},
	"default_income_account": {"7001"},
	"default_expense_account": {"6078", "7245"},
	"round_off_account": {"766", "6588"},
	"write_off_account": {"6588"},
	"depreciation_expense_account": {"6862"},
	"capital_work_in_progress_account": {"237"},
}

# DZ Core Settings warehouse field -> stock account, for a company that keeps
# warehouse accounts (it had stock entries before item-wise accounts)
WAREHOUSE_ACCOUNTS = {
	"raw_materials_warehouse": "311",  # Matières premières
	"wip_warehouse": "3311",  # Produits en cours
	"finished_goods_warehouse": "35511",
}

VALUATION = "Moving Average"  # CMP: SCF allows it, Algerian accountants expect it


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
	"""The company's enabled ledger (not group) account with this SCF number, if any."""
	return frappe.db.get_value(
		"Account", {"company": company, "account_number": number, "is_group": 0, "disabled": 0}
	)


def first_account(company, numbers):
	return next((account for number in numbers if (account := account_by_number(company, number))), None)


def set_default_accounts(company):
	"""Put the SCF accounts in the Company's defaults, where nothing, the
	wizard's pick or an earlier Daftar value is. Returns {field: (old, new)}."""
	changes = {}
	for field, numbers in COMPANY_ACCOUNTS.items():
		current = frappe.db.get_value("Company", company, field)
		if current and frappe.db.get_value("Account", current, "account_number") not in REPLACEABLE.get(
			field, set()
		):
			continue  # someone's choice, or already ours
		account = first_account(company, numbers)
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


def has_stock_entries(company):
	return bool(frappe.db.exists("Stock Ledger Entry", {"company": company, "is_cancelled": 0}))


def item_wise(company):
	return bool(frappe.db.get_value("Company", company, "enable_item_wise_inventory_account"))


def set_warehouse_accounts(company):
	"""A company that keeps warehouse accounts (it had stock entries before
	item-wise accounts) gives the three dz_core warehouses their stock account,
	if they have none. With item-wise accounts they stay empty: unused."""
	if item_wise(company):
		return
	settings = frappe.get_single("DZ Core Settings")
	if settings.company != company:
		return
	for field, number in WAREHOUSE_ACCOUNTS.items():
		warehouse = settings.get(field)
		account = account_by_number(company, number)
		if warehouse and account and not frappe.db.get_value("Warehouse", warehouse, "account"):
			frappe.db.set_value("Warehouse", warehouse, "account", account)


def set_accounting_settings(company):
	"""The switches to set before the first entry. Returns what could not be
	set (the company already has stock entries)."""
	skipped = []
	frappe.db.set_single_value(
		"Accounts Settings",
		{
			# a validated entry is never changed: cancelling posts a dated reversal (decree 09-110 art. 13)
			"enable_immutable_ledger": 1,
			"delete_linked_ledger_entries": 0,
			"book_stock_expense_gl_entries": 0,
			# every item group carries "TVA 19 %" (setup/tax.py): the tax rows must
			# come from the document's template only, or an IFU invoice gets TVA
			"add_taxes_from_item_tax_template": 0,
		},
	)
	values = {"book_advance_payments_in_separate_party_account": 1, "default_operating_cost_account": None}
	if item_wise(company):
		pass
	elif has_stock_entries(company):
		skipped.append("item-wise inventory accounts and moving average: the company has stock entries")
	else:
		values.update({"enable_item_wise_inventory_account": 1, "valuation_method": VALUATION})
		if not frappe.db.exists("Stock Ledger Entry", {"is_cancelled": 0}):
			frappe.db.set_single_value("Stock Settings", "valuation_method", VALUATION)
	frappe.db.set_value("Company", company, values)
	frappe.clear_document_cache("Company", company)
	return skipped
