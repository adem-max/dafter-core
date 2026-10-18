"""Accounts the Algerian chart of accounts does not provide.

ERPNext's standard chart has a "Temporary Opening" account for opening
balances (opening stock, opening receivables). The Algerian chart shipped
with ERPNext has none, and an Opening Stock reconciliation refuses to post
without an asset or liability account of type "Temporary". So one is added
under the liability root.

To check with the accountant: which SCF account the opening balances should
finally be cleared to, and the stock (inventory) accounts the chart maps by
default (Company > Default Inventory Account), which look wrong on a fresh
site (a class 3 "Prestations de services" account).
"""

import frappe

OPENING_ACCOUNT = "Ouverture temporaire"


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
