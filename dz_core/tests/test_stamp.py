"""Stamp duty on cash receipts (dz_core/stamp.py).

Run: bench --site <site> run-tests --module dz_core.tests.test_stamp
"""

import frappe
from frappe.tests import IntegrationTestCase, UnitTestCase

from dz_core import stamp
from dz_core.setup.accounts import account_by_number
from dz_core.setup.scf import apply_scf_setup
from dz_core.setup.sectors import SECTORS
from dz_core.tests.test_core import ensure_prepared


class TestScale(UnitTestCase):
	def test_scale_of_circular_14(self):
		for amount, duty in ((300, 0), (301, 5), (5000, 50), (30000, 300), (35000, 525), (100001, 2002.0)):
			self.assertEqual(stamp.stamp_amount(amount), duty, amount)


class TestStampOnInvoices(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.settings = ensure_prepared()
		cls.company = cls.settings.company
		apply_scf_setup(cls.company)
		group = next(
			g for g, kind in SECTORS[cls.settings.sector]["group_kinds"].items() if kind == "finished"
		)
		cls.item = frappe.db.exists("Item", "TIMBRE-TEST") or (
			frappe.get_doc(
				{
					"doctype": "Item",
					"item_code": "TIMBRE-TEST",
					"item_name": "Produit timbre",
					"item_group": group,
					"stock_uom": "Nos",
					"is_stock_item": 0,
				}
			)
			.insert()
			.name
		)
		cls.customer = frappe.db.get_value("Customer", {"customer_name": "Client timbre test"}) or (
			frappe.get_doc(
				{"doctype": "Customer", "customer_name": "Client timbre test", "customer_type": "Company"}
			)
			.insert()
			.name
		)

	def setUp(self):
		settings = frappe.get_doc("DZ Core Settings")
		before = (settings.stamp_duty, [(row.mode, row.charge) for row in settings.stamp_modes])
		self.addCleanup(self.restore, before)
		settings.stamp_duty = 1
		settings.set("stamp_modes", [])
		for mode, charge in (*stamp.DEFAULT_MODES, (stamp.COD, stamp.SELLER_PAYS)):
			settings.append("stamp_modes", {"mode": mode, "charge": charge})
		settings.save()

	def restore(self, before):
		settings = frappe.get_doc("DZ Core Settings")
		settings.stamp_duty = before[0]
		settings.set("stamp_modes", [{"mode": mode, "charge": charge} for mode, charge in before[1]])
		settings.save()

	def invoice(self, mode, amount=35000, **values):
		return frappe.get_doc(
			{
				"doctype": "Sales Invoice",
				"company": self.company,
				"customer": self.customer,
				"dz_payment_mode": mode,
				"items": [{"item_code": self.item, "qty": 1, "rate": amount}],
				**values,
			}
		).insert()

	def stamp_rows(self, doc):
		accounts = {
			account_by_number(self.company, stamp.STAMP_ACCOUNT),
			account_by_number(self.company, stamp.SELLER_ACCOUNT),
		}
		return {row.account_head: row.tax_amount for row in doc.taxes if row.account_head in accounts}

	def test_cash_gets_the_duty_added(self):
		doc = self.invoice(stamp.CASH)
		self.assertEqual(self.stamp_rows(doc), {account_by_number(self.company, stamp.STAMP_ACCOUNT): 525})
		self.assertEqual(doc.grand_total, 35525)
		doc.dz_payment_mode = "CCP / BaridiMob"  # exempt: the row goes
		doc.save()
		self.assertEqual(self.stamp_rows(doc), {})
		self.assertEqual(doc.grand_total, 35000)

	def test_cheque_with_its_references_is_exempt(self):
		self.assertTrue(self.stamp_rows(self.invoice(stamp.CHEQUE)))
		doc = self.invoice(
			stamp.CHEQUE,
			dz_payment_reference="0012345",
			dz_payment_reference_date=frappe.utils.today(),
			dz_payment_bank="BNA Sétif",
		)
		self.assertEqual(self.stamp_rows(doc), {})

	def test_seller_pays_on_cash_on_delivery(self):
		doc = self.invoice(stamp.COD)
		self.assertEqual(doc.grand_total, 35000)
		doc.submit()
		lines = {
			row.account: row.credit - row.debit
			for row in frappe.get_all(
				"GL Entry",
				filters={
					"voucher_no": doc.name,
					"is_cancelled": 0,
					"account": ["in", list(self.stamp_rows(doc))],
				},
				fields=["account", "debit", "credit"],
			)
		}
		self.assertEqual(lines[account_by_number(self.company, stamp.STAMP_ACCOUNT)], 525)
		self.assertEqual(lines[account_by_number(self.company, stamp.SELLER_ACCOUNT)], -525)

	def test_cash_on_delivery_cannot_be_added_to_the_invoice(self):
		settings = frappe.get_doc("DZ Core Settings")
		next(row for row in settings.stamp_modes if row.mode == stamp.COD).charge = stamp.ADDED
		with self.assertRaises(frappe.ValidationError):
			settings.save()

	def test_off_means_no_duty(self):
		frappe.db.set_single_value("DZ Core Settings", "stamp_duty", 0)
		frappe.clear_document_cache("DZ Core Settings", "DZ Core Settings")
		self.assertEqual(self.stamp_rows(self.invoice(stamp.CASH)), {})
