"""Every whitelisted function of dz_core, called by a user who should get
nothing (review of 27 October 2026, 1.3 and 2.6).

Run: bench --site <site> run-tests --module dz_core.tests.test_endpoints
"""

import json

import frappe
from erpnext.accounts.utils import get_fiscal_year
from frappe.tests import IntegrationTestCase
from frappe.utils import today

from dz_core.closing import check_company
from dz_core.tests.helpers import user_with_roles, whitelisted
from dz_core.tests.test_core import ensure_prepared


def endpoints(company):
	"""{dotted path: arguments}: one line per whitelisted function. A new
	endpoint fails test_every_endpoint_is_listed until it is added here."""
	year = get_fiscal_year(today(), company=company)[0]
	return {
		"dz_core.closing.reclassify_srbnb": {"company": company, "month": today()},
		"dz_core.closing.freeze_month": {"company": company, "month": today()},
		"dz_core.closing.make_tva_settlement": {"company": company, "month": today()},
		"dz_core.tax_checks.make_tva_reversal": {"company": company, "month": today()},
		"dz_core.books.ifu.book_ifu": {"company": company, "fiscal_year": year},
		"dz_core.books.year_end.close_year": {"company": company, "fiscal_year": year},
		"dz_core.books.year_end.freeze_year": {"company": company, "fiscal_year": year},
		"dz_core.books.export.export_entries": {"company": company, "from_date": today(), "to_date": today()},
		"dz_core.books.closing_file.make_closing_file": {"company": company, "fiscal_year": year},
		"dz_core.books.archive.make_archive": {"company": company, "fiscal_year": year},
		"dz_core.books.archive.verify": {"archive": "DZ-ARCHIVE-QUI-N-EXISTE-PAS"},
		"dz_core.books.statements.result_not_closed": {
			"filters": json.dumps({"company": company}),
			"periods": [{"to_date": today()}],
		},
		"dz_core.reports.get_to_buy_card": {},
	}


class TestEndpoints(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.company = ensure_prepared().company

	def test_every_endpoint_is_listed(self):
		self.assertEqual(whitelisted("dz_core"), set(endpoints(self.company)))

	def test_a_portal_user_gets_nothing(self):
		user = user_with_roles()  # a Website User: a customer's portal login
		for path, kwargs in endpoints(self.company).items():
			with self.subTest(endpoint=path), self.set_user(user):
				try:
					result = frappe.get_attr(path)(**kwargs)
				except frappe.PermissionError:
					continue
				self.assertFalse(result, f"{path} answered a portal user: {result!r}")

	def test_a_user_kept_to_another_company_is_refused(self):
		other = "Société B test"
		if not frappe.db.exists("Company", other):
			frappe.get_doc(
				{
					"doctype": "Company",
					"company_name": other,
					"abbr": "SBT",
					"default_currency": "DZD",
					"country": "Algeria",
				}
			).insert()
		user = user_with_roles("Accounts Manager", "Accounts User")
		if not frappe.db.exists("User Permission", {"user": user, "allow": "Company"}):
			frappe.get_doc(
				{"doctype": "User Permission", "user": user, "allow": "Company", "for_value": other}
			).insert(ignore_permissions=True)
		with self.set_user(user):
			check_company(other)  # its own company: allowed
			with self.assertRaises(frappe.PermissionError):
				check_company(self.company)
			with self.assertRaises(frappe.PermissionError):
				frappe.get_attr("dz_core.books.export.export_entries")(self.company, today(), today())
