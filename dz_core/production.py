"""Manufacture posted the SCF way (DECISIONS.md, "Chart of accounts and
default accounts").

With inventory accounts per item group, a manufacture should post the
materials consumed to their consumption account (60111, 60261...) and the
product made to "production stockée" (7245, scrap 7248): the SCF
permanent-inventory entries. ERPNext does so when each line of the Stock
Entry carries its item group's expense account, but a manufacture made from
a Work Order gets the company's stock adjustment account (6572) on every
line, and the lines cancel out: materials go straight into finished goods,
with nothing in 60x or 72.

`production_accounts` (Stock Entry validate, hooks.py) gives each line of a
manufacture or repack its item's (group's) expense account where ERPNext
left the stock adjustment default. An account someone chose on a line is kept.
"""

import frappe
from erpnext.setup.doctype.item_group.item_group import get_item_group_defaults
from erpnext.stock.doctype.item.item import get_item_defaults

from dz_core.setup.accounts import item_wise

PRODUCTION = ("Manufacture", "Repack", "Material Consumption for Manufacture")


def item_expense_account(item_code, company):
	return (get_item_defaults(item_code, company) or {}).get("expense_account") or (
		get_item_group_defaults(item_code, company) or {}
	).get("expense_account")


def production_accounts(doc, method=None):
	if doc.purpose not in PRODUCTION or not item_wise(doc.company):
		return
	adjustment = frappe.get_cached_value("Company", doc.company, "stock_adjustment_account")
	for row in doc.items:
		if row.expense_account and row.expense_account != adjustment:
			continue  # someone's choice
		account = item_expense_account(row.item_code, doc.company)
		if account:
			row.expense_account = account
