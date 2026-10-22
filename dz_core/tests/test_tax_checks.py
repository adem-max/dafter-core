"""Tax warnings and the TVA given back on losses and gifts (dz_core/tax_checks.py).

Run: bench --site <site> run-tests --module dz_core.tests.test_tax_checks
"""

import frappe
from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from erpnext.controllers.accounts_controller import get_taxes_and_charges
from frappe.tests import IntegrationTestCase
from frappe.utils import flt, today

from dz_core import tax_checks
from dz_core.closing import month_bounds
from dz_core.setup.accounts import account_by_number
from dz_core.setup.scf import apply_scf_setup
from dz_core.setup.sectors import SECTORS
from dz_core.setup.tax import PURCHASE_TEMPLATE
from dz_core.tests.test_core import ensure_prepared


def messages():
	return " | ".join(str(m) for m in frappe.local.message_log)


class TestTaxChecks(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.settings = ensure_prepared()
		cls.company = cls.settings.company
		apply_scf_setup(cls.company)
		cls.abbr = frappe.get_cached_value("Company", cls.company, "abbr")
		cls.supplier = frappe.db.get_value("Supplier", {"supplier_name": "Fournisseur contrôles test"}) or (
			frappe.get_doc(
				{
					"doctype": "Supplier",
					"supplier_name": "Fournisseur contrôles test",
					"supplier_group": "Fournisseurs de stocks",
				}
			)
			.insert()
			.name
		)
		cls.machine = frappe.db.exists("Item", "CONTROLE-MACHINE") or (
			frappe.get_doc(
				{
					"doctype": "Item",
					"item_code": "CONTROLE-MACHINE",
					"item_name": "Machine à coudre",
					"item_group": "Petites fournitures",
					"stock_uom": "Nos",
					"is_stock_item": 0,
				}
			)
			.insert()
			.name
		)
		group = next(g for g, kind in SECTORS[cls.settings.sector]["group_kinds"].items() if kind == "raw")
		cls.material = frappe.db.exists("Item", "CONTROLE-MP") or (
			frappe.get_doc(
				{
					"doctype": "Item",
					"item_code": "CONTROLE-MP",
					"item_name": "Matière contrôle",
					"item_group": group,
					"stock_uom": "Kg",
					"is_stock_item": 1,
					"valuation_rate": 100,
				}
			)
			.insert()
			.name
		)

	def purchase(self, item, rate, **values):
		return frappe.get_doc(
			{
				"doctype": "Purchase Invoice",
				"company": self.company,
				"supplier": self.supplier,
				"bill_no": frappe.generate_hash(length=8),
				"items": [{"item_code": item, "qty": 1, "rate": rate}],
				**values,
			}
		)

	def test_low_value_limit_warns(self):
		frappe.local.message_log = []
		self.purchase(self.machine, 59000).insert()
		self.assertNotIn("immobilisation", messages())
		self.purchase(self.machine, 80000).insert()
		self.assertIn("immobilisation", messages())

	def test_no_tva_without_an_invoice(self):
		template = f"{PURCHASE_TEMPLATE} - {self.abbr}"
		doc = self.purchase(
			self.machine,
			5000,
			dz_no_invoice=1,
			taxes_and_charges=template,
			taxes=get_taxes_and_charges("Purchase Taxes and Charges Template", template),
		)
		with self.assertRaises(frappe.ValidationError):
			doc.insert()

	def test_big_invoice_paid_in_cash_warns(self):
		invoice = self.purchase(self.machine, 1_200_000).insert()
		invoice.submit()
		payment = get_payment_entry("Purchase Invoice", invoice.name)
		payment.paid_from = account_by_number(self.company, "5311")
		payment.reference_no, payment.reference_date = "-", today()
		frappe.local.message_log = []
		payment.insert()
		self.assertIn("1 000 000", messages())

	def test_tva_given_back_on_a_loss(self):
		start, end = month_bounds(today())
		if tax_checks.tva_reversal_entry(self.company, end):
			self.skipTest("this month's reversal is already posted on this site")
		warehouse = self.settings.raw_materials_warehouse
		receipt = frappe.get_doc(
			{
				"doctype": "Stock Entry",
				"stock_entry_type": "Material Receipt",
				"company": self.company,
				"items": [
					{"item_code": self.material, "qty": 10, "basic_rate": 100, "t_warehouse": warehouse}
				],
			}
		).insert()
		receipt.submit()
		issue = frappe.get_doc(
			{
				"doctype": "Stock Entry",
				"stock_entry_type": "Material Issue",
				"company": self.company,
				"dz_issue_reason": "Casse ou vol",
				"items": [{"item_code": self.material, "qty": 2, "s_warehouse": warehouse}],
			}
		).insert()
		issue.submit()
		lines = [
			line for line in tax_checks.tva_reversal_lines(self.company, start, end) if line[0] == issue.name
		]
		self.assertEqual(len(lines), 1)
		_entry, _item, _account, value, rate, tva = lines[0]
		self.assertEqual(rate, 19)
		self.assertAlmostEqual(tva, flt(value * 0.19, 2), 2)
		entry = tax_checks.make_tva_reversal(self.company, today())
		credit = frappe.db.get_value(
			"Journal Entry Account",
			{"parent": entry, "account": account_by_number(self.company, "44566")},
			"credit_in_account_currency",
		)
		self.assertGreaterEqual(credit, tva)
		with self.assertRaises(frappe.ValidationError):
			tax_checks.make_tva_reversal(self.company, today())
