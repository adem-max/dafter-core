"""Journals, entry export, archive and audit trail (dz_core/books/).

Run: bench --site <site> run-tests --module dz_core.tests.test_books
"""

import frappe
from frappe.tests import IntegrationTestCase, UnitTestCase
from frappe.utils import add_days, flt, get_year_start, getdate, today

from dz_core.books import archive as archives
from dz_core.books.export import as_text, entry_rows, export_entries, opening_lines
from dz_core.books.journals import journal_of, treasury_journals
from dz_core.setup.accounts import account_by_number
from dz_core.setup.scf import apply_scf_setup
from dz_core.tests.test_core import ensure_prepared


def line(voucher_type, voucher_no, account_number, is_opening="No"):
	return frappe._dict(
		voucher_type=voucher_type, voucher_no=voucher_no, account_number=account_number, is_opening=is_opening
	)


class TestJournals(UnitTestCase):
	def test_each_voucher_gets_its_journal(self):
		lines = [
			line("Sales Invoice", "SI-1", "4111"),
			line("Purchase Invoice", "PI-1", "40132"),
			line("Stock Entry", "SE-1", "311"),
			line("Payment Entry", "PE-1", "5311"),
			line("Payment Entry", "PE-1", "4111"),
			line("Payment Entry", "PE-2", "5121"),
			line("Journal Entry", "JE-1", "5121"),
			line("Journal Entry", "JE-1", "5311"),  # cash to bank: the cash journal
			line("Payment Entry", "PE-3", "46711"),  # a COD collection into the courier's account
			line("Journal Entry", "JE-2", "445711", is_opening="Yes"),
		]
		treasury = treasury_journals(lines)
		self.assertEqual(
			[journal_of(row, treasury) for row in lines],
			["VE", "AC", "ST", "CA", "CA", "BQ", "CA", "CA", "OD", "AN"],
		)


class TestBooks(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.company = ensure_prepared().company
		apply_scf_setup(cls.company)

	def journal(self, debit, credit, amount, posting_date=None):
		entry = frappe.get_doc(
			{
				"doctype": "Journal Entry",
				"company": self.company,
				"posting_date": posting_date or today(),
				"accounts": [
					{"account": account_by_number(self.company, debit), "debit_in_account_currency": amount},
					{
						"account": account_by_number(self.company, credit),
						"credit_in_account_currency": amount,
					},
				],
			}
		).insert()
		entry.submit()
		return entry

	def test_a_cancelled_entry_is_exported_with_its_reversal(self):
		self.assertTrue(frappe.db.get_single_value("Accounts Settings", "enable_immutable_ledger"))
		entry = self.journal("5311", "5121", 1234.5)
		entry.cancel()
		rows = [row for row in entry_rows(self.company, today(), today()) if row["EcritureNum"] == entry.name]
		self.assertEqual(len(rows), 4, rows)
		self.assertEqual({row["JournalCode"] for row in rows}, {"CA"})
		self.assertEqual(sum(row["Debit"] for row in rows), sum(row["Credit"] for row in rows))
		self.assertTrue(any(row["EcritureLib"].startswith("Annulation de") for row in rows))

	def test_opening_lines_carry_the_balance_sheet(self):
		start = getdate(get_year_start(today()))
		before = add_days(start, -1)
		if not frappe.db.exists(
			"Fiscal Year", {"year_start_date": ["<=", before], "year_end_date": [">=", before]}
		):
			frappe.get_doc(
				{
					"doctype": "Fiscal Year",
					"year": str(before.year),
					"year_start_date": get_year_start(before),
					"year_end_date": before,
				}
			).insert()
		self.journal("5311", "7011", 700, posting_date=before)
		lines = opening_lines(self.company, start)
		self.assertAlmostEqual(sum(row.debit for row in lines), sum(row.credit for row in lines), 2)
		cash = account_by_number(self.company, "5311")
		cash_before = flt(
			frappe.db.sql(
				"""SELECT SUM(debit - credit) FROM `tabGL Entry`
				WHERE account = %s AND is_cancelled = 0 AND posting_date < %s""",
				(cash, start),
			)[0][0]
		)
		carried = sum(row.debit - row.credit for row in lines if row.account_number == "5311")
		self.assertAlmostEqual(carried, cash_before, 2)
		self.assertTrue(all(row.is_opening == "Yes" for row in lines))

	def test_export_files_are_kept_with_their_hash(self):
		self.journal("5121", "7011", 50)
		result = export_entries(self.company, today(), today())
		archive = frappe.get_doc("DZ Archive", result["archive"])
		self.assertEqual(archive.kind, archives.EXPORT)
		self.assertEqual([name for name, ok in archives.verify(archive.name) if not ok], [])
		self.assertIn(archives.REGISTER, [row.file_name for row in archive.files])
		text = archive.files[0]
		self.assertTrue(text.file_name.endswith(".txt"))
		with self.assertRaises(frappe.ValidationError):
			archive.save()
		with self.assertRaises(frappe.ValidationError):
			frappe.delete_doc("DZ Archive", archive.name)

	def test_text_layout(self):
		rows = entry_rows(self.company, today(), today())
		header, *lines = as_text(rows).decode("utf-8").splitlines()
		self.assertTrue(header.startswith("JournalCode\tJournalLib\tEcritureNum\tEcritureDate"))
		if lines:
			cells = lines[0].split("\t")
			self.assertEqual(len(cells), len(header.split("\t")))
			self.assertRegex(cells[3], r"^\d{8}$")
			self.assertIn(",", cells[11])

	def test_validation_and_cancellation_are_audited(self):
		entry = self.journal("5311", "5121", 10)
		entry.cancel()
		operations = frappe.get_all(
			"DZ Audit Log",
			filters={"reference_doctype": "Journal Entry", "reference_name": entry.name},
			fields=["operation", "user", "device"],
			order_by="creation",
		)
		self.assertEqual([row.operation for row in operations], ["Validation", "Annulation"])
		self.assertEqual(operations[0].user, frappe.session.user)
		self.assertTrue(operations[0].device)

	def test_a_deletion_is_audited(self):
		"""Only the Administrator may delete (setup/permissions.py): it leaves a trace,
		and the trace does not block the deletion (hooks.py ignore_links_on_delete).
		A draft: under the immutable ledger a cancelled entry keeps its ledger lines."""
		entry = frappe.get_doc(
			{
				"doctype": "Journal Entry",
				"company": self.company,
				"posting_date": today(),
				"accounts": [
					{"account": account_by_number(self.company, "5311"), "debit_in_account_currency": 10},
					{"account": account_by_number(self.company, "5121"), "credit_in_account_currency": 10},
				],
			}
		).insert()
		frappe.delete_doc("Journal Entry", entry.name)
		self.assertFalse(frappe.db.exists("Journal Entry", entry.name))
		row = frappe.get_all(
			"DZ Audit Log",
			filters={"reference_doctype": "Journal Entry", "reference_name": entry.name},
			fields=["operation", "details"],
			order_by="creation desc",
			limit=1,
		)[0]
		self.assertEqual(row.operation, "Suppression")
		self.assertIn("brouillon", row.details)
