"""The audit trail's hash chain (dz_core/books/audit_chain.py; review of 27
October 2026, 4.3). Every change here is rolled back with the test.

Run: bench --site <site> run-tests --module dz_core.tests.test_audit_chain
"""

import frappe
from frappe.tests import IntegrationTestCase

from dz_core.books import audit
from dz_core.books.audit_chain import GENESIS, chain_existing, verify_chain
from dz_core.tests.test_core import ensure_prepared


class TestAuditChain(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.company = ensure_prepared().company

	def setUp(self):
		# the tampering tests break the chain on purpose: each test is undone
		frappe.db.savepoint("audit_chain_test")
		self.addCleanup(frappe.db.rollback, save_point="audit_chain_test")

	def rows(self, count):
		before = frappe.get_all("DZ Audit Log", filters={"company": self.company}, pluck="name")
		for number in range(count):
			audit.write("Test", "Company", self.company, self.company, f"ligne de test {number}")
		return frappe.get_all(
			"DZ Audit Log",
			filters={"company": self.company, "name": ["not in", before or [""]]},
			fields=["name", "seq", "previous_hash", "row_hash"],
			order_by="seq",
		)

	def test_each_row_carries_the_hash_of_the_one_before(self):
		first, second, third = self.rows(3)
		self.assertEqual((second.seq, third.seq), (first.seq + 1, first.seq + 2))
		self.assertEqual(second.previous_hash, first.row_hash)
		self.assertEqual(third.previous_hash, second.row_hash)
		chain = verify_chain(self.company)
		self.assertTrue(chain["ok"], chain["broken_at"])
		self.assertEqual(chain["head"], third.row_hash)

	def test_a_row_changed_in_the_database_is_found(self):
		_first, second, _third = self.rows(3)
		frappe.db.sql("UPDATE `tabDZ Audit Log` SET details = 'réécrit' WHERE name = %s", second.name)
		chain = verify_chain(self.company)
		self.assertFalse(chain["ok"])
		self.assertIn(second.name, chain["broken_at"])
		self.assertIn("contenu modifié", chain["broken_at"])

	def test_a_row_removed_from_the_database_is_found(self):
		_first, second, third = self.rows(3)
		frappe.db.sql("DELETE FROM `tabDZ Audit Log` WHERE name = %s", second.name)
		chain = verify_chain(self.company)
		self.assertFalse(chain["ok"])
		self.assertIn(third.name, chain["broken_at"])

	def test_the_year_end_checks_show_the_chain(self):
		from erpnext.accounts.utils import get_fiscal_year
		from frappe.utils import today

		from dz_core.books.year_end import year_checks

		self.rows(1)
		rows = year_checks(self.company, get_fiscal_year(today(), company=self.company)[0])
		self.assertEqual(next(r for r in rows if r["code"] == "audit")["status"], "OK")

	def test_rows_written_before_the_chain_are_chained_in_order(self):
		"""patch chain_audit_log: rows of a company with no chained row yet."""
		if frappe.db.exists("DZ Audit Log", {"company": ["is", "not set"], "seq": [">", 0]}):
			self.skipTest("rows without a company are already chained on this site")
		for number in range(3):
			frappe.db.sql(
				"""INSERT INTO `tabDZ Audit Log` (name, creation, modified, owner, modified_by,
					operation, reference_doctype, reference_name, user, device)
				VALUES (%s, NOW(6) + INTERVAL %s SECOND, NOW(6), 'Administrator', 'Administrator',
					'Ancienne ligne', 'User', 'Administrator', 'Administrator', 'test')""",
				(frappe.generate_hash(length=10), number),
			)
		chain_existing()
		chain = verify_chain(None)
		self.assertTrue(chain["ok"], chain["broken_at"])
		self.assertGreaterEqual(chain["rows"], 3)
		first = frappe.db.get_value("DZ Audit Log", {"company": ["is", "not set"], "seq": 1}, "previous_hash")
		self.assertEqual(first or GENESIS, GENESIS)
