"""Integration tests: what scripts/restore_test.sh compares after a restore.
Moved from dz_cod (October 2026).

Run: bench --site <site> run-tests --module dz_core.tests.test_restore_check
"""

import frappe
from cryptography.fernet import Fernet
from frappe.tests import IntegrationTestCase
from frappe.utils.password import set_encrypted_password

from dz_core.setup.restore_check import summary


class TestRestoreCheck(IntegrationTestCase):
	def test_summary_counts_records(self):
		result = summary()
		self.assertEqual(result["Sales Invoice"], frappe.db.count("Sales Invoice"))
		self.assertIn("last Sales Invoice", result)

	def test_until_counts_what_existed_at_the_backup(self):
		"""restore_test.sh compares the copy with the live site as it was at the
		backup's time (review of 20 October 2026, 3.2)."""
		before = summary(until="2000-01-01 00:00:00")
		now = summary()
		self.assertEqual(before["Item"], 0)
		self.assertGreaterEqual(now["Item"], before["Item"])
		self.assertEqual(summary(until="2999-12-31 00:00:00")["Item"], now["Item"])

	def test_apps_on_top_add_their_records(self):
		# dz_cod's hooks.py adds its orders and Versements
		for doctype in frappe.get_hooks("dz_restore_check_counted"):
			self.assertIn(doctype, summary())

	def test_a_password_from_another_key_is_reported(self):
		set_encrypted_password("Supplier", "Restore check", "token", "dz_test_secret")
		before = summary()
		self.assertEqual(before["passwords_unreadable"], 0)

		# Same stored value, but this site now has another encryption key,
		# as after a restore without the original site_config
		original_key = frappe.local.conf.encryption_key
		frappe.local.conf.encryption_key = Fernet.generate_key().decode()
		try:
			after = summary()
		finally:
			frappe.local.conf.encryption_key = original_key
		self.assertEqual(after["passwords_unreadable"], after["passwords"])
		self.assertEqual(after["passwords"], before["passwords"])
