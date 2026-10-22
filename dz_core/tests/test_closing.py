"""The monthly close and the TVA settlement (dz_core/closing.py; reports
"Cloture du mois" and "Aide G50").

Run: bench --site <site> run-tests --module dz_core.tests.test_closing
"""

import frappe
from erpnext.controllers.accounts_controller import get_taxes_and_charges
from frappe.tests import IntegrationTestCase
from frappe.utils import flt, get_last_day, today

from dz_core import closing
from dz_core.setup.accounts import account_by_number, opening_account
from dz_core.setup.scf import apply_scf_setup
from dz_core.setup.sectors import SECTORS
from dz_core.setup.tax import PURCHASE_TEMPLATE, SALES_TEMPLATE
from dz_core.tests.test_core import ensure_prepared


def check(rows, start):
	return next(row for row in rows if row["check"].startswith(start))


class TestMonthlyClose(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.settings = ensure_prepared()
		cls.company = cls.settings.company
		apply_scf_setup(cls.company)
		cls.abbr = frappe.get_cached_value("Company", cls.company, "abbr")
		cls.supplier = (
			frappe.db.get_value("Supplier", {"supplier_name": "Fournisseur clôture test"})
			or frappe.get_doc(
				{
					"doctype": "Supplier",
					"supplier_name": "Fournisseur clôture test",
					"supplier_group": "Fournisseurs de stocks",
				}
			)
			.insert()
			.name
		)
		group = next(g for g, kind in SECTORS[cls.settings.sector]["group_kinds"].items() if kind == "raw")
		cls.material = (
			frappe.get_doc(
				{
					"doctype": "Item",
					"item_code": "CLOTURE-MP",
					"item_name": "Matière clôture",
					"item_group": group,
					"stock_uom": "Kg",
					"is_stock_item": 1,
					"valuation_rate": 100,
				}
			)
			.insert()
			.name
		)

	def journal(self, debit_number, credit_number, amount):
		entry = frappe.get_doc(
			{
				"doctype": "Journal Entry",
				"company": self.company,
				"posting_date": today(),
				"accounts": [
					{
						"account": account_by_number(self.company, debit_number),
						"debit_in_account_currency": amount,
					},
					{
						"account": account_by_number(self.company, credit_number),
						"credit_in_account_currency": amount,
					},
				],
			}
		).insert()
		entry.submit()
		return entry

	def test_an_amount_left_to_reclassify_is_flagged(self):
		before = check(closing.closing_rows(self.company, today()), "6589")["amount"]
		self.journal("6589", "5311", 1234)
		row = check(closing.closing_rows(self.company, today()), "6589")
		self.assertEqual(row["status"], closing.TO_CHECK)
		self.assertAlmostEqual(row["amount"] - before, 1234, 2)

	def test_an_invoice_before_its_goods_is_reclassified_once(self):
		invoice = frappe.get_doc(
			{
				"doctype": "Purchase Invoice",
				"company": self.company,
				"supplier": self.supplier,
				"bill_no": "F-CLOTURE-1",
				"items": [{"item_code": self.material, "qty": 10, "rate": 100}],
			}
		)
		invoice.set("taxes", [])
		invoice.insert()
		invoice.submit()
		debits = closing.srbnb_debits(self.company, get_last_day(today()))
		self.assertAlmostEqual(debits[self.supplier], 1000, 2)

		names = closing.reclassify_srbnb(self.company, today())
		self.assertEqual(len(names), 2)  # the month end, and its reversal on the 1st
		lines = frappe.get_all(
			"GL Entry",
			filters={"voucher_no": names[0], "is_cancelled": 0},
			fields=["account", "debit", "credit"],
		)
		accounts = {
			frappe.db.get_value("Account", line.account, "account_number"): flt(line.debit - line.credit)
			for line in lines
		}
		self.assertEqual(accounts["4097"], sum(debits.values()))
		self.assertEqual(check(closing.closing_rows(self.company, today()), "4081")["status"], closing.OK)
		with self.assertRaises(frappe.ValidationError):
			closing.reclassify_srbnb(self.company, today())

	def test_opening_stock_is_not_production(self):
		"""Finished goods received against the opening account (479) leave the
		class 72 check as it was; the same receipt against 7245 too."""
		group = next(
			g for g, kind in SECTORS[self.settings.sector]["group_kinds"].items() if kind == "finished"
		)
		item = frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": "CLOTURE-PF",
				"item_name": "Produit fini clôture",
				"item_group": group,
				"stock_uom": "Kg",
				"is_stock_item": 1,
				"valuation_rate": 500,
			}
		).insert()
		before = check(closing.closing_rows(self.company, today()), "Classe 72")["amount"]
		for account in (opening_account(self.company), None):
			receipt = frappe.get_doc(
				{
					"doctype": "Stock Entry",
					"stock_entry_type": "Material Receipt",
					"company": self.company,
					"items": [
						{
							"item_code": item.name,
							"qty": 2,
							"basic_rate": 500,
							"t_warehouse": self.settings.finished_goods_warehouse,
							"expense_account": account,
						}
					],
				}
			).insert()
			receipt.submit()
			self.assertEqual(
				check(closing.closing_rows(self.company, today()), "Classe 72")["amount"], before
			)

	def test_the_month_can_be_frozen(self):
		before = frappe.db.get_value("Company", self.company, "accounts_frozen_till_date")
		try:
			end = closing.freeze_month(self.company, today())
			self.assertEqual(frappe.db.get_value("Company", self.company, "accounts_frozen_till_date"), end)
			self.assertEqual(
				check(closing.closing_rows(self.company, today()), "Mois gelé")["status"], closing.OK
			)
		finally:
			frappe.db.set_value("Company", self.company, "accounts_frozen_till_date", before)

	def test_tva_of_the_month_and_its_settlement(self):
		figures = closing.tva_figures(self.company, today())
		if figures.settlement:
			self.skipTest("this month's TVA is already settled on this site")
		group = next(
			g for g, kind in SECTORS[self.settings.sector]["group_kinds"].items() if kind == "finished"
		)
		item = frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": "G50-TEST-PF",
				"item_name": "Produit G50",
				"item_group": group,
				"stock_uom": "Nos",
				"is_stock_item": 0,
			}
		).insert()
		customer = frappe.get_doc(
			{"doctype": "Customer", "customer_name": "Client G50 test", "customer_type": "Company"}
		).insert()
		sales = f"{SALES_TEMPLATE} - {self.abbr}"
		invoice = frappe.get_doc(
			{
				"doctype": "Sales Invoice",
				"company": self.company,
				"customer": customer.name,
				"taxes_and_charges": sales,
				"taxes": get_taxes_and_charges("Sales Taxes and Charges Template", sales),
				"items": [{"item_code": item.name, "qty": 1, "rate": 10000}],
			}
		).insert()
		invoice.submit()
		purchases = f"{PURCHASE_TEMPLATE} - {self.abbr}"
		bill = frappe.get_doc(
			{
				"doctype": "Purchase Invoice",
				"company": self.company,
				"supplier": self.supplier,
				"bill_no": "F-G50-1",
				"taxes_and_charges": purchases,
				"taxes": get_taxes_and_charges("Purchase Taxes and Charges Template", purchases),
				"items": [{"item_code": self.material, "qty": 10, "rate": 400}],
			}
		).insert()
		bill.submit()

		after = closing.tva_figures(self.company, today())
		self.assertAlmostEqual(after.collected_19 - figures.collected_19, 1900, 2)
		self.assertAlmostEqual(after.deductible - figures.deductible, 760, 2)
		self.assertAlmostEqual(after.bases["19"] - figures.bases["19"], 10000, 2)

		name = closing.make_tva_settlement(self.company, today())
		entry = frappe.get_doc("Journal Entry", name)
		self.assertAlmostEqual(
			sum(flt(r.debit) for r in entry.accounts), sum(flt(r.credit) for r in entry.accounts), 2
		)
		# the settlement itself is left out of the month's figures
		self.assertAlmostEqual(closing.tva_figures(self.company, today()).collected_19, after.collected_19, 2)
		with self.assertRaises(frappe.ValidationError):
			closing.make_tva_settlement(self.company, today())
