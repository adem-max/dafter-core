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

	def test_the_books_can_still_be_exported(self):
		"""An export keeps its files on a DZ Archive (books/archive.keep): allowed;
		the same archive written by hand is not (review of 31 October 2026, B)."""
		from frappe.utils import today

		from dz_core.books import archive as archives
		from dz_core.tests.test_core import ensure_prepared

		frappe.local.conf.pop(KEY)
		company = ensure_prepared().company
		frappe.local.conf[KEY] = 1
		kept = archives.keep(
			company, archives.EXPORT, [("ecritures.txt", b"ligne", "Export")], today(), today()
		)
		self.assertEqual(len(kept.files), 2)  # the file and its hash register
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc(
				{
					"doctype": "DZ Archive",
					"company": company,
					"kind": archives.EXPORT,
					"from_date": today(),
					"to_date": today(),
				}
			).insert(ignore_permissions=True)

	def test_reactivated_saves_again(self):
		frappe.local.conf.pop(KEY)
		frappe.get_doc({"doctype": "ToDo", "description": "après la réactivation"}).insert()
