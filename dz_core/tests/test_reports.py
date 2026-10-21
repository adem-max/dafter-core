"""The producer reports (dz_core/dz_core/report/) on a tiny workshop.

One jam made from fruit, sugar and jars, bought at known prices, so every
figure can be checked by hand.

Run: bench --site <site> run-tests --module dz_core.tests.test_reports
"""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, nowdate, random_string

from dz_core.dz_core.report.a_acheter import a_acheter
from dz_core.dz_core.report.a_produire import a_produire
from dz_core.dz_core.report.cout_de_revient import cout_de_revient
from dz_core.reports import STOCK_VALUE
from dz_core.tests.test_core import ensure_prepared


class TestProducerReports(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.settings = ensure_prepared()
		cls.company = cls.settings.company
		t = random_string(5).upper()
		cls.sugar, cls.fruit, cls.jar, cls.jam = (
			f"RM-{t}-SUCRE",
			f"RM-{t}-FRUIT",
			f"PK-{t}-POT",
			f"FG-{t}-CONF",
		)
		item(cls.sugar, "Matières premières", "Kg")
		item(cls.fruit, "Matières premières", "Kg")
		item(cls.jar, "Emballages", "Nos", reorder=(cls.settings.raw_materials_warehouse, 200, 500))
		item(cls.jam, "Produits finis", "Nos", price=200)
		cls.supplier = make(
			"Supplier", supplier_name=f"Fournisseur {t}", supplier_group=leaf("Supplier Group")
		)
		cls.customer = make("Customer", customer_name=f"Client {t}", customer_group=leaf("Customer Group"))
		cls.receive(cls.sugar, 100, 100)
		cls.receive(cls.fruit, 50, 300)
		cls.receive(cls.jar, 100, 25)
		# 10 jars: 1.5 Kg fruit, 1.2 Kg sugar, 10 jars -> 82 DA a jar
		bom = frappe.get_doc(
			{
				"doctype": "BOM",
				"item": cls.jam,
				"company": cls.company,
				"quantity": 10,
				"is_active": 1,
				"is_default": 1,
				"items": [
					{"item_code": cls.fruit, "qty": 1.5},
					{"item_code": cls.sugar, "qty": 1.2},
					{"item_code": cls.jar, "qty": 10},
				],
			}
		).insert()
		bom.submit()
		cls.bom = bom.name

	@classmethod
	def receive(cls, item_code, qty, rate):
		doc = frappe.get_doc(
			{
				"doctype": "Purchase Receipt",
				"company": cls.company,
				"supplier": cls.supplier,
				"items": [
					{
						"item_code": item_code,
						"qty": qty,
						"rate": rate,
						"warehouse": cls.settings.raw_materials_warehouse,
					}
				],
			}
		).insert()
		doc.submit()

	def cost_row(self, **filters):
		_columns, rows, *_rest = cout_de_revient.execute({"item": self.jam, **filters})
		return next(row for row in rows if not row["indent"])

	def test_cost_per_product_follows_the_last_purchase(self):
		row = self.cost_row()
		self.assertAlmostEqual(row["materials"], 82)
		self.assertEqual(row["price"], 200)
		self.assertAlmostEqual(row["margin"], 118)
		_columns, rows, *_rest = cout_de_revient.execute({"item": self.jam})
		self.assertEqual(len([r for r in rows if r["indent"] == 1]), 3, "one line per material")

		# a dearer sugar delivery moves the jam's cost at once
		self.receive(self.sugar, 100, 120)
		self.assertAlmostEqual(self.cost_row()["materials"], 84.4)
		# priced at what the stock is worth: half the sugar at 100, half at 120
		self.assertAlmostEqual(self.cost_row(rate_basis=STOCK_VALUE)["materials"], 83.2)

	def test_a_acheter_lists_what_is_under_its_level(self):
		_columns, rows, *_rest = a_acheter.execute({})
		row = next(r for r in rows if r["item"] == self.jar)
		self.assertEqual(row["status"], a_acheter.TO_ORDER)
		self.assertEqual(row["actual"], 100)
		self.assertEqual(row["to_order"], 500)
		self.assertEqual(row["supplier"], None)  # bought on receipts only, no order yet
		self.assertFalse(any(r["item"] == self.sugar for r in rows), "no level, never listed")

	def test_a_produire_counts_orders_stock_and_work_orders(self):
		order = frappe.get_doc(
			{
				"doctype": "Sales Order",
				"company": self.company,
				"customer": self.customer,
				"delivery_date": add_days(nowdate(), 3),
				**direct_sale(),
				"items": [
					{
						"item_code": self.jam,
						"qty": 30,
						"rate": 200,
						"warehouse": self.settings.finished_goods_warehouse,
					}
				],
			}
		).insert()
		order.submit()
		self.assertEqual(self.to_produce(), 30)
		work_order = frappe.get_doc(
			{
				"doctype": "Work Order",
				"company": self.company,
				"production_item": self.jam,
				"bom_no": self.bom,
				"qty": 10,
				"wip_warehouse": self.settings.wip_warehouse,
				"fg_warehouse": self.settings.finished_goods_warehouse,
			}
		).insert()
		work_order.submit()
		self.assertEqual(self.to_produce(), 20)

	def to_produce(self):
		_columns, rows, *_rest = a_produire.execute({"only_missing": 1})
		return next(r["to_produce"] for r in rows if r["item"] == self.jam)


def item(code, group, uom, price=None, reorder=None):
	doc = frappe.get_doc(
		{
			"doctype": "Item",
			"item_code": code,
			"item_name": code,
			"item_group": group,
			"stock_uom": uom,
			"is_stock_item": 1,
			"standard_rate": price or 0,
		}
	)
	if reorder:
		warehouse, level, qty = reorder
		doc.append(
			"reorder_levels",
			{
				"warehouse": warehouse,
				"warehouse_reorder_level": level,
				"warehouse_reorder_qty": qty,
				"material_request_type": "Purchase",
			},
		)
	return doc.insert().name


def make(doctype, **values):
	return frappe.get_doc({"doctype": doctype, **values}).insert().name


def direct_sale():
	"""On a test site that also has dz_cod, this producer's order is a direct
	sale (dz_cod's sales channel): ERPNext's usual flow, without the COD checks
	or COD Settings."""
	if "dz_cod" not in frappe.get_installed_apps():
		return {}
	return {"dz_channel": "Vente directe"}


def leaf(doctype):
	"""A group that can be picked (not a parent of other groups)."""
	return frappe.db.get_value(doctype, {"is_group": 0})
