"""The SCF accounts in a company's defaults (dz_core/setup/accounts.py), and
the patch that put them on companies set up before 21 October 2026.

Run: bench --site <site> run-tests --module dz_core.tests.test_accounts
"""

import frappe
from frappe.tests import IntegrationTestCase

from dz_core.patches import scf_default_accounts
from dz_core.setup.accounts import (
	COMPANY_ACCOUNTS,
	FINISHED_GOODS,
	WAREHOUSE_ACCOUNTS,
	account_by_number,
	set_default_accounts,
)
from dz_core.tests.test_core import ensure_prepared


def number(account):
	return frappe.db.get_value("Account", account, "account_number")


class TestDefaultAccounts(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.settings = ensure_prepared()
		cls.company = cls.settings.company
		set_default_accounts(cls.company)  # a test site prepared before 21 Oct 2026

	def cash_mode_row(self):
		"""This company's row of the Cash mode of payment (made by ERPNext's setup)."""
		mode = frappe.get_doc("Mode of Payment", frappe.db.get_value("Mode of Payment", {"type": "Cash"}))
		row = next((row for row in mode.accounts if row.company == self.company), None)
		if not row:
			row = mode.append("accounts", {"company": self.company, "default_account": None})
			mode.save()
		return row.name

	def test_prepared_company_uses_the_scf_accounts(self):
		company = frappe.get_doc("Company", self.company)
		for field, (ours, _wizard_pick) in COMPANY_ACCOUNTS.items():
			with self.subTest(field=field):
				self.assertEqual(number(company.get(field)), ours)
		for field, ours in WAREHOUSE_ACCOUNTS.items():
			with self.subTest(warehouse=field):
				warehouse = self.settings.get(field)
				self.assertEqual(number(frappe.db.get_value("Warehouse", warehouse, "account")), ours)
		# Finished goods: the ledger the chart lacks, under its group 3551
		parent = frappe.db.get_value("Account", company.default_inventory_account, "parent_account")
		self.assertEqual(number(parent), FINISHED_GOODS[2])

	def test_wizard_picks_are_replaced_and_choices_are_kept(self):
		wizard_cash = account_by_number(self.company, "5322")
		frappe.db.set_value(
			"Company",
			self.company,
			{
				"default_receivable_account": account_by_number(self.company, "4172"),
				"default_cash_account": wizard_cash,
				# someone chose the services suppliers' account
				"default_payable_account": account_by_number(self.company, "40162"),
			},
		)
		cash_row = self.cash_mode_row()
		frappe.db.set_value("Mode of Payment Account", cash_row, "default_account", wizard_cash)

		changes = set_default_accounts(self.company)

		self.assertEqual(set(changes), {"default_receivable_account", "default_cash_account"})
		company = frappe.get_doc("Company", self.company)
		self.assertEqual(number(company.default_receivable_account), "4111")
		self.assertEqual(number(company.default_cash_account), "5311")
		self.assertEqual(number(company.default_payable_account), "40162")
		# The Cash mode of payment follows the cash account
		self.assertEqual(
			number(frappe.db.get_value("Mode of Payment Account", cash_row, "default_account")), "5311"
		)

	def test_patch_changes_nothing_the_second_time(self):
		scf_default_accounts.execute()
		self.assertEqual(set_default_accounts(self.company), {})
