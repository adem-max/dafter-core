"""The demo data and its planned story (dz_core/demo), without loading anything.

The full load runs on a dedicated site (docs/DEMO.md); these tests catch a
broken profile before that: an unknown item in a recipe, a wilaya that does
not resolve, a story that sells what was never made.

Run: bench --site <site> run-tests --module dz_core.tests.test_demo
"""

import datetime
import importlib

import frappe
from frappe.tests import IntegrationTestCase, UnitTestCase
from frappe.utils.password import check_password

from dz_core.demo.loader import PROFILES, secure_logins
from dz_core.demo.planner import RAW_WAREHOUSE, Story, plan

TODAY = datetime.date(2026, 10, 19)
START = TODAY - datetime.timedelta(weeks=13)


def profiles():
	for name in PROFILES:
		try:
			yield name, importlib.import_module(f"dz_core.demo.{name}")
		except ModuleNotFoundError:
			continue  # a profile not written yet


class TestProfiles(UnitTestCase):
	def test_every_code_is_an_item(self):
		for name, p in profiles():
			codes = {row["code"] for row in p.ITEMS} | {row["code"] for row in p.MODELS}
			codes |= set(getattr(p, "VARIANT_CODES", []))  # size/colour variants of the models
			with self.subTest(profile=name):
				for product, (batch_qty, components) in p.BOMS.items():
					self.assertIn(product, codes)
					self.assertGreater(batch_qty, 0)
					for component, qty in components:
						self.assertIn(component, codes, product)
						self.assertGreater(qty, 0)
				for code in list(p.RAW) + list(p.PRODUCTION):
					self.assertIn(code, codes)
				for code, *_rest in p.OPENING:
					self.assertIn(code, codes)

	def test_prices_and_suppliers(self):
		for name, p in profiles():
			suppliers = {s["name"] for s in p.SUPPLIERS}
			with self.subTest(profile=name):
				for code, rule in p.RAW.items():
					self.assertIn(rule["supplier"], suppliers, code)
					self.assertGreater(p.buying_rate(code, TODAY), 0)
				for price_list, prices in p.PRICE_LISTS.items():
					for code in p.PRODUCTION:
						self.assertGreater(prices.get(code, 0), 0, f"{price_list} {code}")
				for customer in p.CUSTOMERS:
					self.assertIn(customer["group"], p.PAYMENT)
					self.assertTrue(p.price_list_of(customer["name"]))


class TestStory(UnitTestCase):
	def test_story_never_goes_below_zero(self):
		for name, p in profiles():
			with self.subTest(profile=name):
				story = Story(p, START, TODAY, 2026)
				story.run()
				negative = {key: qty for key, qty in story.stock.items() if qty < -1e-6}
				self.assertFalse(negative)

	def test_story_has_every_kind_of_event(self):
		for name, p in profiles():
			with self.subTest(profile=name):
				kinds = {e["type"] for e in plan(p, START, TODAY, 2026)}
				for kind in (
					"po",
					"receive",
					"pinv",
					"wo",
					"wo_finish",
					"so",
					"dn",
					"si",
					"spay",
					"count",
					"cancel",
					"return",
				):
					self.assertIn(kind, kinds)

	def test_same_story_on_a_later_day_starts_the_same(self):
		# Loading again a few days later must replay the same past, then add days
		for name, p in profiles():
			with self.subTest(profile=name):
				early = [
					e
					for e in plan(p, START, TODAY - datetime.timedelta(days=10), 2026)
					if e["type"] in ("so", "wo", "po")
				]
				later = [e for e in plan(p, START, TODAY, 2026) if e["type"] in ("so", "wo", "po")]
				self.assertEqual(early, later[: len(early)])

	def test_today_shows_low_stock_on_order_and_few_late_orders(self):
		# What docs/DEMO.md shows must not depend on the day the demo is loaded
		for name, p in profiles():
			for offset in range(0, 28, 3):
				today = TODAY + datetime.timedelta(days=offset)
				with self.subTest(profile=name, today=today):
					story = Story(p, today - datetime.timedelta(weeks=13), today, 2026)
					story.run()
					low = [
						code
						for code in p.SHOWN_LOW
						if story.qty(code, RAW_WAREHOUSE) < p.RAW[code]["reorder_level"]
						and story.on_order.get(code, 0) > 0
					]
					self.assertTrue(low)
					late = [order for order in story.backlog if order["due"] < today]
					self.assertLessEqual(len(late), 3)

	def test_events_are_in_date_order_and_refer_to_earlier_ones(self):
		for name, p in profiles():
			with self.subTest(profile=name):
				seen = set()
				events = plan(p, START, TODAY, 2026)
				self.assertEqual(events, sorted(events, key=lambda e: e["date"]))
				for event in events:
					if "ref" in event:
						self.assertIn(event["ref"], seen, event["key"])
					seen.add(event["key"])


class TestWilayas(IntegrationTestCase):
	def test_every_customer_wilaya_resolves(self):
		from dz_core.setup.wilayas import find_wilaya

		for name, p in profiles():
			for customer in p.CUSTOMERS:
				with self.subTest(profile=name, customer=customer["name"]):
					self.assertTrue(find_wilaya(customer["wilaya"]))


class TestPublicLink(IntegrationTestCase):
	"""scripts/demo_tunnels.sh: on a public link, no demo login keeps the
	repo's password or System Manager."""

	def test_demo_logins_get_the_new_password_and_lose_system_manager(self):
		# a domain of its own: CI's site is "test_site", and gerant@test_site is no e-mail address
		domain = "demo-lien-public.test"
		email = f"gerant@{domain}"
		if not frappe.db.exists("User", email):
			frappe.get_doc(
				{"doctype": "User", "email": email, "first_name": "Gérant", "send_welcome_email": 0}
			).insert(ignore_permissions=True)
		frappe.get_doc("User", email).add_roles("System Manager", "Sales Manager")
		password = "Lien-public-2026"
		self.assertIn(email, secure_logins(password, domain=domain))
		roles = frappe.get_roles(email)
		self.assertNotIn("System Manager", roles)
		self.assertIn("Sales Manager", roles)
		self.assertEqual(check_password(email, password), email)

	def test_a_short_password_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			secure_logins("court")
