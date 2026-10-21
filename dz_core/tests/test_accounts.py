"""The SCF set-up of a company (dz_core/setup/scf.py): chart changes, default
accounts, accounting settings, accounts per item group, supplier groups,
payment modes, no deletion of accounting documents, and the patch that
applies it to older sites.

Run: bench --site <site> run-tests --module dz_core.tests.test_accounts
"""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import flt

from dz_core.dz_core.doctype.dz_core_settings.dz_core_settings import get_settings
from dz_core.imports.workbook import SHEETS, Report, check
from dz_core.patches import scf_setup
from dz_core.setup.accounts import COMPANY_ACCOUNTS, account_by_number, item_wise, set_default_accounts
from dz_core.setup.chart import CREATE, apply_chart_changes
from dz_core.setup.item_groups import FINISHED, KINDS, SERVICE_GROUPS, group_has_accounts, set_group_accounts
from dz_core.setup.parties import SUPPLIER_GROUPS
from dz_core.setup.permissions import NO_DELETE
from dz_core.setup.scf import apply_scf_setup
from dz_core.setup.sectors import SECTORS
from dz_core.tests.test_core import ensure_prepared


def number(account):
	return frappe.db.get_value("Account", account, "account_number")


def any_account(company, account_number):
	"""By number, enabled or not (4172 is disabled by the set-up)."""
	return frappe.db.get_value(
		"Account", {"company": company, "account_number": account_number, "is_group": 0}
	)


class TestScfSetup(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.settings = ensure_prepared()
		cls.company = cls.settings.company
		apply_scf_setup(cls.company)  # a test site prepared before 21 Oct 2026

	def test_chart_changes(self):
		for account_number, _name, _parent, _is_group, _type in CREATE:
			with self.subTest(account=account_number):
				self.assertTrue(
					frappe.db.exists("Account", {"company": self.company, "account_number": account_number})
				)
		# the opening account is 479, still of type Temporary
		opening = frappe.db.get_value(
			"Account", {"company": self.company, "account_type": "Temporary"}, "account_number"
		)
		self.assertEqual(opening, "479")
		# TAP is repealed; nobody posts to it
		self.assertTrue(
			frappe.db.get_value("Account", {"company": self.company, "account_number": "6421"}, "disabled")
		)
		# a second run creates nothing
		self.assertFalse([line for line in apply_chart_changes(self.company) if line.startswith("created")])

	def test_default_accounts(self):
		company = frappe.get_doc("Company", self.company)
		for field, numbers in COMPANY_ACCOUNTS.items():
			with self.subTest(field=field):
				self.assertIn(number(company.get(field)), numbers)

	def test_settings(self):
		self.assertTrue(item_wise(self.company))
		self.assertEqual(frappe.db.get_value("Company", self.company, "valuation_method"), "Moving Average")
		self.assertTrue(
			frappe.db.get_value("Company", self.company, "book_advance_payments_in_separate_party_account")
		)
		self.assertFalse(frappe.db.get_single_value("Accounts Settings", "delete_linked_ledger_entries"))
		self.assertFalse(frappe.db.get_single_value("Accounts Settings", "book_stock_expense_gl_entries"))
		# taxes come from the document's template only (every group carries "TVA 19 %")
		self.assertFalse(frappe.db.get_single_value("Accounts Settings", "add_taxes_from_item_tax_template"))

	def test_item_groups_carry_their_accounts(self):
		for group, kind in SECTORS[self.settings.sector]["group_kinds"].items():
			row = next(
				r
				for r in frappe.get_doc("Item Group", group).item_group_defaults
				if r.company == self.company
			)
			with self.subTest(group=group):
				self.assertEqual(number(row.default_inventory_account), KINDS[kind][0])
				self.assertEqual(number(row.default_cogs_account), KINDS[kind][1])
		for group, expense in SERVICE_GROUPS.items():
			row = next(
				r
				for r in frappe.get_doc("Item Group", group).item_group_defaults
				if r.company == self.company
			)
			with self.subTest(group=group):
				self.assertEqual(number(row.expense_account), expense)

	def test_a_new_subgroup_inherits_its_parents_accounts(self):
		frappe.get_doc({"doctype": "Item Group", "item_group_name": "Parent de test", "is_group": 1}).insert()
		set_group_accounts(self.company, "Parent de test", FINISHED)
		child = frappe.get_doc(
			{
				"doctype": "Item Group",
				"item_group_name": "Confitures de test",
				"parent_item_group": "Parent de test",
			}
		).insert()
		self.assertTrue(group_has_accounts(child.name, self.company))

	def test_import_refuses_a_group_without_accounts(self):
		frappe.get_doc({"doctype": "Item Group", "item_group_name": "Groupe sans comptes"}).insert()
		frappe.db.delete("Item Default", {"parent": "Groupe sans comptes"})
		data = {sheet: [] for sheet in SHEETS}
		data["Articles"] = [
			(
				2,
				{
					"code": "ART-SANS-COMPTE",
					"name": "Article",
					"group": "Groupe sans comptes",
					"uom": "Nos",
					"buying": None,
					"selling": None,
					"batch": None,
					"expiry": None,
					"shelf_life": None,
					"reorder_level": None,
					"reorder_qty": None,
				},
			),
		]
		report = Report()
		check(data, get_settings(), report)
		self.assertTrue(any("Groupe sans comptes" in error for error in report.errors), report.errors)

	def test_stock_moves_post_to_the_groups_accounts(self):
		group = next(g for g, kind in SECTORS[self.settings.sector]["group_kinds"].items() if kind == "raw")
		item = frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": "SCF-TEST-MP",
				"item_name": "Matière de test",
				"item_group": group,
				"stock_uom": "Kg",
				"is_stock_item": 1,
				"valuation_rate": 100,
			}
		).insert()
		warehouse = self.settings.raw_materials_warehouse
		receipt = frappe.get_doc(
			{
				"doctype": "Stock Entry",
				"stock_entry_type": "Material Receipt",
				"company": self.company,
				"items": [{"item_code": item.name, "qty": 10, "basic_rate": 100, "t_warehouse": warehouse}],
			}
		)
		receipt.insert()
		receipt.submit()
		issue = frappe.get_doc(
			{
				"doctype": "Stock Entry",
				"stock_entry_type": "Material Issue",
				"company": self.company,
				"items": [{"item_code": item.name, "qty": 4, "s_warehouse": warehouse}],
			}
		)
		issue.insert()
		issue.submit()
		lines = frappe.get_all(
			"GL Entry",
			filters={"voucher_no": issue.name, "is_cancelled": 0},
			fields=["account", "debit", "credit"],
		)
		self.assertEqual(
			{number(line.account): flt(line.debit - line.credit) for line in lines},
			{"311": -400, "60111": 400},
		)

	def test_accounting_documents_cannot_be_deleted(self):
		for doctype in NO_DELETE:
			with self.subTest(doctype=doctype):
				self.assertFalse(frappe.db.exists("Custom DocPerm", {"parent": doctype, "delete": 1}))
		self.assertFalse(
			frappe.db.exists("Custom DocPerm", {"parent": "Transaction Deletion Record", "create": 1})
		)

	def test_supplier_groups(self):
		for group, (payable, advance) in SUPPLIER_GROUPS.items():
			row = next(
				r for r in frappe.get_doc("Supplier Group", group).accounts if r.company == self.company
			)
			with self.subTest(group=group):
				self.assertEqual((number(row.account), number(row.advance_account)), (payable, advance))

	def test_wizard_and_earlier_picks_are_replaced_and_choices_are_kept(self):
		wizard_cash = any_account(self.company, "5322")
		frappe.db.set_value(
			"Company",
			self.company,
			{
				"default_receivable_account": any_account(self.company, "4172"),  # the wizard's
				"default_expense_account": any_account(self.company, "7245"),  # Daftar 0.2.0's
				"default_cash_account": wizard_cash,
				# someone chose the services suppliers' account
				"default_payable_account": account_by_number(self.company, "40162"),
			},
		)
		changes = set_default_accounts(self.company)
		self.assertEqual(
			set(changes), {"default_receivable_account", "default_expense_account", "default_cash_account"}
		)
		company = frappe.get_doc("Company", self.company)
		self.assertEqual(number(company.default_receivable_account), "4111")
		self.assertEqual(number(company.default_expense_account), "6589")
		self.assertEqual(number(company.default_payable_account), "40162")

	def test_patch_changes_nothing_the_second_time(self):
		scf_setup.execute()
		log = apply_scf_setup(self.company)
		self.assertFalse([line for line in log if line.startswith("created") or "->" in line], log)


class TestTvaPerRate(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.settings = ensure_prepared()
		cls.company = cls.settings.company
		apply_scf_setup(cls.company)

	def test_an_invoice_books_tva_on_the_line_rate_ledger(self):
		from erpnext.controllers.accounts_controller import get_taxes_and_charges

		from dz_core.setup.tax import SALES_TEMPLATE

		abbr = frappe.get_cached_value("Company", self.company, "abbr")
		template = f"{SALES_TEMPLATE} - {abbr}"
		group = next(
			g for g, kind in SECTORS[self.settings.sector]["group_kinds"].items() if kind == "finished"
		)
		item = frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": "TVA-TEST-PF",
				"item_name": "Produit TVA",
				"item_group": group,
				"stock_uom": "Nos",
				"is_stock_item": 0,
			}
		).insert()
		customer = frappe.get_doc(
			{"doctype": "Customer", "customer_name": "Client TVA test", "customer_type": "Company"}
		).insert()
		invoice = frappe.get_doc(
			{
				"doctype": "Sales Invoice",
				"company": self.company,
				"customer": customer.name,
				"taxes_and_charges": template,
				"taxes": get_taxes_and_charges("Sales Taxes and Charges Template", template),
				"items": [{"item_code": item.name, "qty": 2, "rate": 1000}],
			}
		).insert()
		amounts = {number(row.account_head): flt(row.tax_amount) for row in invoice.taxes}
		self.assertEqual(amounts, {"445711": 380, "445712": 0})
		self.assertEqual(flt(invoice.grand_total), 2380)
		# the 9 % row, empty, is not printed
		html = frappe.get_print("Sales Invoice", invoice.name, "Facture DZ", doc=invoice)
		self.assertIn("TVA 19 %", html)
		self.assertNotIn("TVA 9 %", html)

		# without a template (IFU), the item's "TVA 19 %" adds nothing
		ifu = frappe.get_doc(
			{
				"doctype": "Sales Invoice",
				"company": self.company,
				"customer": customer.name,
				"items": [{"item_code": item.name, "qty": 2, "rate": 1000}],
			}
		).insert()
		self.assertFalse(ifu.taxes)
		self.assertEqual(flt(ifu.grand_total), 2000)
