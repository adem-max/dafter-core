"""Sales and purchases registers, Aide G12 and the filing reminders
(dz_core/books/registers.py, books/ifu.py, closing.deadline_rows).

Run: bench --site <site> run-tests --module dz_core.tests.test_registers
"""

import frappe
from erpnext.accounts.utils import get_fiscal_year
from frappe.tests import IntegrationTestCase
from frappe.utils import flt, getdate, today

from dz_core import closing
from dz_core.books import ifu
from dz_core.books.registers import purchases_register, sales_register
from dz_core.setup.scf import apply_scf_setup
from dz_core.setup.sectors import SECTORS
from dz_core.tests.test_core import ensure_prepared


class TestRegisters(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.settings = ensure_prepared()
		cls.company = cls.settings.company
		apply_scf_setup(cls.company)
		cls.fiscal_year, cls.start, cls.end = get_fiscal_year(today(), company=cls.company)
		group = next(
			g for g, kind in SECTORS[cls.settings.sector]["group_kinds"].items() if kind == "finished"
		)
		cls.item = frappe.db.exists("Item", "REGISTRE-TEST") or (
			frappe.get_doc(
				{
					"doctype": "Item",
					"item_code": "REGISTRE-TEST",
					"item_name": "Produit registre",
					"item_group": group,
					"stock_uom": "Nos",
					"is_stock_item": 0,
				}
			)
			.insert()
			.name
		)
		cls.customer = frappe.db.get_value("Customer", {"customer_name": "Client registre test"}) or (
			frappe.get_doc(
				{"doctype": "Customer", "customer_name": "Client registre test", "customer_type": "Company"}
			)
			.insert()
			.name
		)

	def invoice(self, amount, is_return=0, return_against=None):
		doc = frappe.get_doc(
			{
				"doctype": "Sales Invoice",
				"company": self.company,
				"customer": self.customer,
				"is_return": is_return,
				"return_against": return_against,
				"items": [{"item_code": self.item, "qty": -1 if is_return else 1, "rate": amount}],
			}
		).insert()
		doc.submit()
		return doc

	def test_sales_register_numbers_months_and_credit_notes(self):
		sale = self.invoice(10000)
		credit = self.invoice(10000, is_return=1, return_against=sale.name)
		register = sales_register(self.company, self.start, self.end)
		lines = [line for line in register.rows if line[0] is not None]
		numbers = [line[0] for line in lines]
		self.assertEqual(numbers, sorted(numbers))
		self.assertEqual(len(set(numbers)), len(numbers))
		by_name = {line[2]: line for line in lines}
		self.assertEqual(by_name[sale.name][5], 10000)
		self.assertEqual(by_name[credit.name][5], -10000)
		totals = [line for line in register.rows if line[0] is None]
		self.assertAlmostEqual(sum(t[5] for t in totals), sum(line[5] for line in lines), 2)

	def test_purchases_register_runs(self):
		register = purchases_register(self.company, self.start, self.end)
		self.assertEqual(register.columns[2][0], "N° de facture du fournisseur")

	def test_g12_matches_the_register_and_books_the_ifu(self):
		self.invoice(10000)
		figures = ifu.year_figures(self.company, self.fiscal_year)
		register = sales_register(self.company, self.start, self.end)
		self.assertAlmostEqual(
			figures.turnover, sum(flt(line[5]) for line in register.rows if line[0] is not None), 2
		)
		self.assertAlmostEqual(figures.due, flt(figures.goods * 0.05 + figures.services * 0.12, 2), 2)
		entry = ifu.book_ifu(self.company, self.fiscal_year)
		self.assertEqual(frappe.db.get_value("Journal Entry", entry, "docstatus"), 1)
		with self.assertRaises(frappe.ValidationError):
			ifu.book_ifu(self.company, self.fiscal_year)

	def test_ifu_sites_are_reminded_of_the_g12(self):
		june = getdate(f"{getdate(today()).year}-06-15")
		rows = closing.closing_rows(self.company, june)
		reminders = [row["check"] for row in rows if row["code"] == "deadline"]
		self.assertTrue(any("G12 prévisionnel" in text for text in reminders), reminders)
