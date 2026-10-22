"""Supplier groups, modes of payment and asset categories with their SCF
accounts (DECISIONS.md, "Chart of accounts and default accounts", from the
SCF advice of 21 October 2026). Created when missing; an account already
set on a row for the company (someone's choice) is kept.
"""

import frappe
from frappe.utils.nestedset import get_root_of

from dz_core.setup.accounts import account_by_number

STOCKS = "Fournisseurs de stocks"
SERVICES = "Fournisseurs de services"

# Supplier group -> (payable account, advance account). The minimum split
# an Algerian accountant expects: stocks / services / fixed assets, foreign apart.
SUPPLIER_GROUPS = {
	STOCKS: ("40132", "40913"),  # fabric, jars, sugar, merchandise
	SERVICES: ("40162", "40916"),  # couriers, accountant, printer, landlord
	"Organismes publics": ("40161", "40916"),  # Sonelgaz, Algérie Télécom, Algérie Poste
	"Fournisseurs étrangers (stocks)": ("40133", "40913"),
	"Fournisseurs étrangers (services)": ("40163", "40916"),  # Meta, TikTok
	"Fournisseurs d'immobilisations": ("4042", "2384"),  # machines, computers
}

# ERPNext's mode of payment (made by the setup wizard, or here) -> (type, account)
PAYMENT_MODES = {
	"Cash": ("Cash", "5311"),  # Espèces: caisse principale
	"Wire Transfer": ("Bank", "5121"),  # Virement
	"Cheque": ("Bank", "5111"),  # Chèques à encaisser, then the bank
	"CCP / BaridiMob": ("Bank", "5171"),  # BaridiMob moves money on the CCP account
	"Credit Card": ("Bank", "51181"),  # Carte (TPE, CIB, Edahabia): settlements in transit
}

# Asset category -> (asset, accumulated depreciation, depreciation expense)
ASSET_CATEGORIES = {
	"Machines et outillage": ("215", "2815", "6812"),
	"Matériel de transport": ("2182", "2818", "6812"),
	"Informatique et bureau": ("2183", "2818", "6812"),
	"Mobilier": ("2184", "2818", "6812"),
}


def setup_parties(company):
	for group, (payable, advance) in SUPPLIER_GROUPS.items():
		set_supplier_group_accounts(company, group, payable, advance)
	for mode, (kind, number) in PAYMENT_MODES.items():
		set_payment_mode_account(company, mode, kind, number)
	for category, numbers in ASSET_CATEGORIES.items():
		set_asset_category_accounts(company, category, *numbers)


def set_supplier_group_accounts(company, group, payable, advance):
	if not frappe.db.exists("Supplier Group", group):
		frappe.get_doc(
			{
				"doctype": "Supplier Group",
				"supplier_group_name": group,
				"parent_supplier_group": get_root_of("Supplier Group"),
			}
		).insert(ignore_permissions=True)
	doc = frappe.get_doc("Supplier Group", group)
	if any(row.company == company for row in doc.accounts):
		return
	account, advance_account = account_by_number(company, payable), account_by_number(company, advance)
	if account:
		doc.append("accounts", {"company": company, "account": account, "advance_account": advance_account})
		doc.save(ignore_permissions=True)


def set_payment_mode_account(company, mode, kind, number):
	account = account_by_number(company, number)
	if not account:
		return
	if not frappe.db.exists("Mode of Payment", mode):
		frappe.get_doc({"doctype": "Mode of Payment", "mode_of_payment": mode, "type": kind}).insert(
			ignore_permissions=True
		)
	doc = frappe.get_doc("Mode of Payment", mode)
	if any(row.company == company and row.default_account for row in doc.accounts):
		return
	doc.set("accounts", [row for row in doc.accounts if row.company != company])
	doc.append("accounts", {"company": company, "default_account": account})
	doc.save(ignore_permissions=True)


def set_asset_category_accounts(company, category, asset, accumulated, expense):
	accounts = {
		"fixed_asset_account": account_by_number(company, asset),
		"accumulated_depreciation_account": account_by_number(company, accumulated),
		"depreciation_expense_account": account_by_number(company, expense),
	}
	if not accounts["fixed_asset_account"]:
		return
	if not frappe.db.exists("Asset Category", category):
		frappe.get_doc(
			{
				"doctype": "Asset Category",
				"asset_category_name": category,
				"accounts": [{"company_name": company, **accounts}],
			}
		).insert(ignore_permissions=True)
		return
	doc = frappe.get_doc("Asset Category", category)
	if not any(row.company_name == company for row in doc.accounts):
		doc.append("accounts", {"company_name": company, **accounts})
		doc.save(ignore_permissions=True)
