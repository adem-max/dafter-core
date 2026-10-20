"""The Atelier home page: its records, its counters, the low stock alert and
the landing page after login.

Run: bench --site <site> run-tests --module dz_core.tests.test_home
"""

import json

import frappe
from frappe.apps import get_default_path
from frappe.desk.doctype.number_card.number_card import get_result
from frappe.tests import IntegrationTestCase
from frappe.utils import flt, random_string, today
from frappe.website.utils import get_home_page

from dz_core.dz_core.report.a_acheter import a_acheter
from dz_core.reports import get_to_buy_card
from dz_core.setup.new_client import make_atelier_the_home_page
from dz_core.tests.test_core import ensure_prepared
from dz_core.tests.test_reports import item

CARDS = [
	"Atelier Sales Today",
	"Atelier Orders To Deliver",
	"Atelier Work In Progress",
	"Atelier To Buy",
	"Atelier Overdue Invoices",
]
CHARTS = ["Atelier Sales Per Month", "Atelier Stock Value", "Atelier To Buy"]


class TestAtelierHome(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.settings = ensure_prepared()
		cls.company = cls.settings.company

	def card(self, name):
		doc = frappe.get_doc("Number Card", name)
		return flt(get_result(doc.as_dict(), doc.filters_json))

	def test_records_are_loaded(self):
		workspace = frappe.get_doc("Workspace", "Atelier")
		self.assertEqual([row.number_card_name for row in workspace.number_cards], CARDS)
		self.assertEqual([row.chart_name for row in workspace.charts], CHARTS)
		# every block of the page points at a card, chart or link card of the workspace
		labels = {row.label for row in workspace.number_cards + workspace.charts}
		labels |= {row.label for row in workspace.links if row.type == "Card Break"}
		for block in json.loads(workspace.content):
			name = next(value for key, value in block["data"].items() if key.endswith("_name"))
			self.assertIn(name, labels)
		for report in (row.link_to for row in workspace.links if row.link_type == "Report"):
			self.assertTrue(frappe.db.exists("Report", report), report)
		self.assertEqual(frappe.db.get_value("Dock", "dz_core", "mount_on"), "erpnext")
		self.assertTrue(frappe.db.exists("Sidebar", "Atelier"))

	def test_sales_today_is_the_sum_of_todays_invoices(self):
		expected = frappe.db.sql(
			"""SELECT IFNULL(SUM(base_net_total), 0) FROM `tabSales Invoice`
			WHERE docstatus = 1 AND posting_date = %s""",
			today(),
		)[0][0]
		self.assertAlmostEqual(self.card("Atelier Sales Today"), flt(expected), places=2)

	def test_counts_match_the_lists(self):
		self.assertEqual(
			self.card("Atelier Orders To Deliver"),
			frappe.db.count(
				"Sales Order", {"docstatus": 1, "status": ("in", ["To Deliver and Bill", "To Deliver"])}
			),
		)
		self.assertEqual(
			self.card("Atelier Work In Progress"),
			frappe.db.count("Work Order", {"docstatus": 1, "status": ("in", ["Not Started", "In Process"])}),
		)

	def test_a_material_under_its_level_shows_on_the_page(self):
		before = get_to_buy_card()["value"]
		code = item(
			f"RM-{random_string(5).upper()}-SEUIL",
			"Matières premières",
			"Kg",
			reorder=(self.settings.raw_materials_warehouse, 50, 100),
		)
		card = get_to_buy_card()
		self.assertEqual(card["value"], before + 1)
		self.assertEqual(card["route"], ["query-report", "A acheter"])
		# the chart of "À acheter" is the one on the home page: the material is named there
		_columns, _rows, _message, chart, _summary = a_acheter.execute({})
		self.assertIn(code, chart["data"]["labels"])

	def test_login_opens_the_atelier_home_page(self):
		make_atelier_the_home_page()
		frappe.db.set_value("User", frappe.session.user, "default_app", "")
		self.assertEqual(get_default_path(), "/desk/atelier")
		# what the login answer sends a desk user to (Frappe alone says "desk", its app list)
		frappe.cache.delete_key("home_page")
		self.assertEqual(get_home_page(), "desk/atelier")
