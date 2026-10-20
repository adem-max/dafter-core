"""The reports "Valeur du stock" and "Ventes par mois" against ERPNext's own figures.

Run: bench --site <site> run-tests --module dz_core.tests.test_reports_stock_sales
"""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, add_months, flt, get_first_day, get_last_day, random_string, today
from frappe.utils.nestedset import get_root_of

from dz_core.dz_core.report.valeur_du_stock import valeur_du_stock
from dz_core.dz_core.report.ventes_par_mois import ventes_par_mois
from dz_core.tests.test_core import ensure_prepared


class TestStockValue(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.settings = ensure_prepared()
		cls.company = cls.settings.company
		t = random_string(5).upper()
		# an item group of its own, so stock left by other tests does not count here
		cls.group = (
			frappe.get_doc(
				{
					"doctype": "Item Group",
					"item_group_name": f"Test {t}",
					"parent_item_group": get_root_of("Item Group"),
				}
			)
			.insert()
			.name
		)
		cls.item = make_item(f"RM-{t}", cls.group, "Kg")
		cls.warehouse = cls.settings.raw_materials_warehouse
		receipt = frappe.get_doc(
			{
				"doctype": "Stock Entry",
				"stock_entry_type": "Material Receipt",
				"company": cls.company,
				"items": [
					{"item_code": cls.item, "qty": 40, "basic_rate": 125, "t_warehouse": cls.warehouse}
				],
			}
		).insert()
		receipt.submit()

	def rows(self, date=None):
		_columns, rows, _message, _chart, _summary = valeur_du_stock.execute({"date": date})
		return rows

	def group_row(self, date=None):
		return next((row for row in self.rows(date) if row.get("item_group") == self.group), None)

	def test_total_equals_stock_balance(self):
		from erpnext.stock.report.stock_balance.stock_balance import execute as stock_balance

		_columns, balance = stock_balance(
			frappe._dict(company=self.company, from_date=add_months(today(), -1), to_date=today())
		)
		total = next(row for row in self.rows() if row.get("is_total_row"))["value"]
		self.assertAlmostEqual(total, sum(flt(row["bal_val"]) for row in balance), places=2)

	def test_rows_per_warehouse_and_item_group(self):
		rows = self.rows()
		group = self.group_row()
		self.assertEqual((group["warehouse"], group["indent"]), (self.warehouse, 1))
		self.assertEqual((group["items"], group["qty"], group["value"]), (1, 40, 40 * 125))
		warehouse = next(row for row in rows if not row["indent"] and row["warehouse"] == self.warehouse)
		children = [row for row in rows if row["indent"] == 1 and row["warehouse"] == self.warehouse]
		self.assertAlmostEqual(warehouse["value"], sum(row["value"] for row in children), places=2)

	def test_value_at_a_date(self):
		# the receipt is today: the day before, the group had nothing in stock
		self.assertIsNone(self.group_row(add_days(today(), -1)))


class TestSalesPerMonth(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.settings = ensure_prepared()
		cls.company = cls.settings.company
		t = random_string(5).upper()
		cls.item = make_item(f"FG-{t}", "Produits finis", "Nos")
		cls.customer = make_customer(f"Client {t}")
		cls.last_month = add_months(get_first_day(today()), -1)
		cls.two_months_ago = add_months(cls.last_month, -1)
		cls.invoice(cls.two_months_ago, 20, 300)  # 6 000 DA HT two months ago
		cls.invoice(cls.last_month, 10, 300)  # 3 000 DA HT last month
		cls.invoice(today(), 5, 300)  # 1 500 DA HT this month

	@classmethod
	def invoice(cls, date, qty, rate, return_against=None, item=None, customer=None):
		doc = frappe.get_doc(
			{
				"doctype": "Sales Invoice",
				"company": cls.company,
				"customer": customer or cls.customer,
				"set_posting_time": 1,
				"posting_date": date,
				"due_date": date,
				"is_return": 1 if return_against else 0,
				"return_against": return_against,
				"items": [{"item_code": item or cls.item, "qty": qty, "rate": rate}],
			}
		).insert()
		doc.submit()
		return doc.name

	def report(self, **filters):
		filters = {"from_month": self.last_month, "to_month": today(), **filters}
		_columns, rows, _message, _chart, _summary = ventes_par_mois.execute(filters)
		return rows

	def test_totals_equal_the_invoices(self):
		rows = self.report()
		total = next(row for row in rows if row.get("is_total_row"))
		invoiced = frappe.db.sql(
			"""SELECT SUM(base_net_total) FROM `tabSales Invoice`
			WHERE docstatus = 1 AND company = %s AND posting_date BETWEEN %s AND %s""",
			(self.company, self.last_month, get_last_day(today())),
		)[0][0]
		self.assertAlmostEqual(total["total"], flt(invoiced), places=2)

		row = next(row for row in rows if row["name"] == self.item)
		months = ventes_par_mois.get_months(self.last_month, today())
		self.assertEqual(row[months[0][0]], 3000)
		self.assertEqual(row[months[1][0]], 1500)
		# this month is not over: no full month to compare last month with
		self.assertIsNone(row["evolution"])

	def test_evolution_compares_the_last_two_full_months(self):
		rows = self.report(from_month=self.two_months_ago)
		row = next(row for row in rows if row["name"] == self.item)
		self.assertEqual(row["evolution"], -50)  # 6 000 then 3 000; this month left out

	def test_by_customer(self):
		row = next(row for row in self.report(by=ventes_par_mois.CUSTOMER) if row["name"] == self.customer)
		self.assertEqual(row["total"], 4500)
		self.assertEqual(row["title"], frappe.db.get_value("Customer", self.customer, "customer_name"))

	def test_credit_note_counts_negative(self):
		# its own product and customer, so the other tests' figures stay put
		t = random_string(5).upper()
		item, customer = make_item(f"FG-{t}", "Produits finis", "Nos"), make_customer(f"Client {t}")
		sold = self.invoice(today(), 5, 300, item=item, customer=customer)
		self.invoice(today(), -2, 300, return_against=sold, item=item, customer=customer)
		row = next(row for row in self.report() if row["name"] == item)
		self.assertEqual(row["total"], 1500 - 600)
		cancelled = frappe.get_doc(
			"Sales Invoice", self.invoice(today(), 1, 300, item=item, customer=customer)
		)
		cancelled.cancel()
		row = next(row for row in self.report() if row["name"] == item)
		self.assertEqual(row["total"], 1500 - 600, "a cancelled invoice counts for nothing")


def make_item(code, group, uom):
	frappe.get_doc(
		{
			"doctype": "Item",
			"item_code": code,
			"item_name": code,
			"item_group": group,
			"stock_uom": uom,
			"is_stock_item": 1,
		}
	).insert()
	return code


def make_customer(name):
	return (
		frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": name,
				"customer_group": frappe.db.get_value("Customer Group", {"is_group": 0}),
			}
		)
		.insert()
		.name
	)
