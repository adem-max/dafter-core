"""Wilayas and phone numbers: moved from dz_cod with their tests (October 2026).

Run: bench --site <site> run-tests --module dz_core.tests.test_places_and_phones
"""

import frappe
from frappe.tests import IntegrationTestCase, UnitTestCase
from frappe.utils import random_string

from dz_core.phone import is_valid_phone, normalize_phone
from dz_core.setup.wilayas import WILAYAS, find_wilaya, simplify


class TestPhone(UnitTestCase):
	def test_normalize_international_formats(self):
		self.assertEqual(normalize_phone("+213 555 12 34 56"), "0555123456")
		self.assertEqual(normalize_phone("00213-661-12-34-56"), "0661123456")
		self.assertEqual(normalize_phone("0770 12 34 56"), "0770123456")

	def test_unknown_format_is_kept(self):
		# We never destroy what the operator typed
		self.assertEqual(normalize_phone(" 12345 "), "12345")
		self.assertIsNone(normalize_phone(None))

	def test_validity(self):
		self.assertTrue(is_valid_phone("0555123456"))  # mobile
		self.assertTrue(is_valid_phone("021234567"))  # landline (9 digits)
		self.assertFalse(is_valid_phone("0855123456"))  # 08 is not a mobile prefix
		self.assertFalse(is_valid_phone("055512345"))  # too short for a mobile
		self.assertFalse(is_valid_phone(""))


class TestWilayaList(UnitTestCase):
	def test_69_wilayas_in_order(self):
		codes = [code for code, *_ in WILAYAS]
		self.assertEqual(codes, [f"{n:02d}" for n in range(1, 70)])

	def test_new_wilayas_have_an_existing_parent(self):
		codes = {code for code, *_ in WILAYAS}
		for code, _name, parent in WILAYAS:
			if int(code) > 58:
				self.assertIn(parent, codes)
				self.assertLessEqual(int(parent), 58)

	def test_simplify(self):
		self.assertEqual(simplify("Béjaïa"), "bejaia")
		self.assertEqual(simplify("M'Sila"), simplify("msila"))


class TestWilayasOnSite(IntegrationTestCase):
	def test_created_on_install(self):
		self.assertEqual(frappe.db.count("DZ Wilaya"), 69)
		self.assertEqual(frappe.db.get_value("DZ Wilaya", "60 - Barika", "parent_wilaya"), "05 - Batna")

	def test_find_wilaya(self):
		for text in ("16", "16 - Alger", "alger", " ALGER "):
			self.assertEqual(find_wilaya(text), "16 - Alger", text)
		self.assertEqual(find_wilaya("Bejaia"), "06 - Béjaïa")
		self.assertEqual(find_wilaya("9"), "09 - Blida")
		self.assertIsNone(find_wilaya("Paris"))
		self.assertIsNone(find_wilaya(""))

	def test_customer_phone_is_normalized(self):
		customer = frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": f"Client tel {random_string(5)}",
				"dz_phone": "+213 555 98 76 54",
				"dz_wilaya": "31 - Oran",
			}
		).insert()
		self.assertEqual(customer.dz_phone, "0555987654")
