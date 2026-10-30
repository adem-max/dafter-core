"""A suspended client reads, saves nothing (dz_core/suspension.py; review of
27 October 2026, 3.5).

Run: bench --site <site> run-tests --module dz_core.tests.test_suspension
"""

import frappe
from frappe.tests import IntegrationTestCase

from dz_core.suspension import KEY


class TestSuspension(IntegrationTestCase):
	def setUp(self):
		frappe.local.conf[KEY] = 1
		self.addCleanup(frappe.local.conf.pop, KEY, None)

	def test_nothing_is_saved_while_suspended(self):
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc({"doctype": "ToDo", "description": "pendant la suspension"}).insert()

	def test_reading_and_its_logs_still_work(self):
		self.assertIsInstance(frappe.get_all("Item", limit=1), list)
		frappe.get_doc(
			{"doctype": "Access Log", "user": "Administrator", "export_from": "Item", "file_type": "CSV"}
		).insert(ignore_permissions=True)

	def test_reactivated_saves_again(self):
		frappe.local.conf.pop(KEY)
		frappe.get_doc({"doctype": "ToDo", "description": "après la réactivation"}).insert()
