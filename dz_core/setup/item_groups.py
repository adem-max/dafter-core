"""Accounts per item group (DECISIONS.md, "Chart of accounts and default
accounts", from the SCF advice of 21 October 2026).

With inventory accounts per item (setup/accounts.py), ERPNext takes an
item's stock account from the item or its group and refuses an item with
none: there is no company fallback, and a group does not inherit from its
parent. So every group carries its accounts here, and a group someone adds
later copies its parent's (inherit_parent_accounts, hooks.py).

Each group is of a kind. The kind gives, as SCF numbers:
- inventory: the stock account;
- cogs: what a sale or a delivery debits (7245 for own products: "production
  déstockée"; 6001 for resold goods);
- expense: what a manufacture or a Material Issue debits when the item is
  consumed (60111 materials...), and for finished goods what a manufacture
  credits (7245 "production stockée"): ERPNext then posts the SCF
  permanent-inventory entries itself (checked on 21 Oct 2026);
- income: what a sale credits.
"""

import frappe
from frappe.utils.nestedset import get_root_of

from dz_core.setup.accounts import account_by_number

RAW = "raw"
TRIMS = "trims"
PACKAGING = "packaging"
FINISHED = "finished"
MERCHANDISE = "merchandise"
SCRAP = "scrap"
SERVICE = "service"

# kind -> (inventory, cogs, expense, income)
KINDS = {
	RAW: ("311", "60111", "60111", "7081"),  # Matières premières / consommées / cession
	TRIMS: ("317", "60171", "60171", "7082"),  # Fournitures accessoires
	PACKAGING: ("3261", "60261", "60261", "7082"),  # Emballages perdus
	FINISHED: ("35511", "7245", "7245", "7011"),  # Produits finis / variation / ventes
	MERCHANDISE: ("301", "6001", "6571", "7001"),  # Marchandises; an issue is a loss (6571)
	SCRAP: ("35831", "7248", "7248", "7031"),  # Chutes et déchets
}

# The groups every company gets, besides its sector's (setup/sectors.py)
MERCHANDISE_GROUP = "Marchandises"
SCRAP_GROUP = "Déchets et chutes"
SERVICES_GROUP = "Services achetés"
COMMON_GROUPS = {MERCHANDISE_GROUP: MERCHANDISE, SCRAP_GROUP: SCRAP}

# Purchased services (non-stock items), under SERVICES_GROUP: expense account
SERVICE_GROUPS = {
	"Loyer": "6132",
	"Énergie atelier": "6072",
	"Eau, gaz, électricité bureaux": "6073",
	"Internet": "6264",
	"Téléphone": "6263",
	"Transporteurs": "6241",
	"Publicité": "6231",
	"Comptable": "6226",
	"Frais bancaires": "6278",
	"Entretien": "6152",
	"Assurance": "6161",
	"Petites fournitures": "6075",
}


def setup_item_groups(company, sector_kinds):
	"""Create the common groups and give every group its accounts for the
	company. sector_kinds = {group: kind} of the company's sector."""
	root = get_root_of("Item Group")
	for group in COMMON_GROUPS:
		ensure_group(group, root)
	ensure_group(SERVICES_GROUP, root, is_group=1)
	for group in SERVICE_GROUPS:
		ensure_group(group, SERVICES_GROUP)
	for group, kind in {**sector_kinds, **COMMON_GROUPS}.items():
		set_group_accounts(company, group, kind)
	for group, number in SERVICE_GROUPS.items():
		set_service_account(company, group, number)


def ensure_group(name, parent, is_group=0):
	if not frappe.db.exists("Item Group", name):
		frappe.get_doc(
			{
				"doctype": "Item Group",
				"item_group_name": name,
				"parent_item_group": parent,
				"is_group": is_group,
			}
		).insert(ignore_permissions=True)


def company_row(doc, company):
	"""(the group's row for the company, whether it was just added)"""
	row = next((row for row in doc.item_group_defaults if row.company == company), None)
	if row:
		return row, False
	return doc.append("item_group_defaults", {"company": company}), True


def set_group_accounts(company, group, kind):
	"""The kind's accounts on the group's row for the company; an account
	already set there (someone's choice) is kept."""
	inventory, cogs, expense, income = KINDS[kind]
	fill(
		company,
		group,
		{
			"default_inventory_account": inventory,
			"default_cogs_account": cogs,
			"expense_account": expense,
			"income_account": income,
		},
	)


def set_service_account(company, group, number):
	fill(company, group, {"expense_account": number})


def fill(company, group, numbers):
	doc = frappe.get_doc("Item Group", group)
	row, changed = company_row(doc, company)
	for field, number in numbers.items():
		account = account_by_number(company, number)
		if account and not row.get(field):
			row.set(field, account)
			changed = True
	if changed:
		doc.save(ignore_permissions=True)


def group_has_accounts(group, company):
	"""Does a stock item of this group get a stock account for the company?"""
	return bool(
		frappe.db.get_value(
			"Item Default",
			{"parenttype": "Item Group", "parent": group, "company": company},
			"default_inventory_account",
		)
	)


def inherit_parent_accounts(doc, method=None):
	"""Item Group before_insert (hooks.py): a new group gets its parent's
	accounts, for each company, unless it brings its own."""
	if not doc.parent_item_group:
		return
	parent = frappe.get_cached_doc("Item Group", doc.parent_item_group)
	for row in parent.item_group_defaults:
		if any(own.company == row.company for own in doc.item_group_defaults):
			continue
		doc.append(
			"item_group_defaults",
			{
				field: row.get(field)
				for field in (
					"company",
					"default_inventory_account",
					"default_cogs_account",
					"expense_account",
					"income_account",
					"default_warehouse",
				)
			},
		)
