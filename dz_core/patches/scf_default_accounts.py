"""Companies set up before 21 October 2026 kept the setup wizard's default
accounts (receivables in 4172, suppliers in 4213, the bank in 5176...): they
get the SCF accounts of setup/accounts.py, their warehouses a stock account,
their finished goods a cost-of-sales account.

Documents already posted keep their accounts. No client site was live; on a
site with transactions, the accountant decides whether to move the balances
(the demos are reloaded instead, docs/DEMO.md)."""

import frappe

from dz_core.setup.accounts import set_default_accounts


def execute():
	for company in frappe.get_all("Company", pluck="name"):
		for field, (old, new) in set_default_accounts(company).items():
			print(f"{company}: {field} {old or '-'} -> {new}")
