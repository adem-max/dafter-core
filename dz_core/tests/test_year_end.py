"""SCF statements, year end, closing file and yearly archive (dz_core/books/).

The year is never closed here: a Period Closing Voucher on a test site would
stop every later test from posting in that year. The closing is tested up to
its refusals and its choice of account.

Run: bench --site <site> run-tests --module dz_core.tests.test_year_end
"""

import io

import frappe
from erpnext.accounts.utils import get_fiscal_year
from frappe.tests import IntegrationTestCase
from frappe.utils import today

from dz_core.books import archive as archives
from dz_core.books import statements as st
from dz_core.books.closing_file import make_closing_file
from dz_core.books.year_end import close_year, closing_account, year_bounds, year_checks, year_result
from dz_core.setup.accounts import account_by_number
from dz_core.setup.scf import apply_scf_setup
from dz_core.tests.test_core import ensure_prepared


class TestYearEnd(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.company = ensure_prepared().company
		apply_scf_setup(cls.company)
		st.setup_statements()
		cls.fiscal_year = get_fiscal_year(today(), company=cls.company)[0]
		cls.start, cls.end = year_bounds(cls.fiscal_year)

	def journal(self, debit, credit, amount):
		entry = frappe.get_doc(
			{
				"doctype": "Journal Entry",
				"company": self.company,
				"posting_date": today(),
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

	def test_statements_balance_and_give_the_ledger_result(self):
		self.journal("5121", "7011", 1000)
		self.journal("6132", "5121", 300)
		income = st.amounts(self.company, st.INCOME_STATEMENT, self.start, self.end)
		self.assertAlmostEqual(income["RNET"], year_result(self.company, self.start, self.end), 2)
		sheet = st.amounts(self.company, st.BALANCE_SHEET, self.start, self.end)
		self.assertAlmostEqual(sheet["TA"], sheet["TP"], 2)

	def test_the_result_goes_to_120_or_129(self):
		self.assertIn("120", closing_account(self.company, 10))
		self.assertIn("129", closing_account(self.company, -10))

	def test_closing_is_refused_while_a_check_fails(self):
		self.journal("6589", "5121", 75)  # left to reclassify
		rows = year_checks(self.company, self.fiscal_year)
		self.assertEqual(next(r for r in rows if r["code"] == "6589")["status"], "À voir")
		with self.assertRaises(frappe.ValidationError):
			close_year(self.company, self.fiscal_year)

	def test_the_archive_needs_a_frozen_year(self):
		with self.assertRaises(frappe.ValidationError):
			archives.make_archive(self.company, self.fiscal_year)

	def test_closing_file_refused_then_made_as_a_draft(self):
		from openpyxl import load_workbook

		self.journal("6589", "5121", 75)
		with self.assertRaises(frappe.ValidationError):
			make_closing_file(self.company, self.fiscal_year)
		name = make_closing_file(self.company, self.fiscal_year, draft=1)
		archive = frappe.get_doc("DZ Archive", name)
		self.assertEqual((archive.kind, archive.draft), (archives.CLOSING_FILE, 1))
		self.assertEqual([file for file, ok in archives.verify(name) if not ok], [])
		workbook = next(
			row for row in archive.files if row.file_name.endswith(".xlsx") and "cloture" in row.file_name
		)
		content = frappe.get_doc("File", {"file_url": workbook.file, "attached_to_name": name}).get_content()
		book = load_workbook(io.BytesIO(content))
		for sheet in (
			"Contrôles",
			"Balance générale",
			"Grand livre",
			"Journal centralisateur",
			st.BALANCE_SHEET,
		):
			self.assertIn(sheet, book.sheetnames)
		self.assertIn("BROUILLON", str(book["Contrôles"]["A1"].value))
