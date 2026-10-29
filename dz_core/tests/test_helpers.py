"""The test helpers themselves (helpers.py): a permission test is only as good as its user."""

import frappe
from frappe.permissions import AUTOMATIC_ROLES
from frappe.tests import IntegrationTestCase

from dz_core.tests.helpers import user_with_roles


def own_roles(user):
	return set(frappe.get_roles(user)) - set(AUTOMATIC_ROLES)


class TestUserWithRoles(IntegrationTestCase):
	def test_exactly_the_roles_asked(self):
		user = user_with_roles("Stock User")
		self.assertEqual(own_roles(user), {"Stock User"})
		both = user_with_roles("Accounts User", "Stock User")
		self.assertEqual(user_with_roles("Stock User", "Accounts User"), both)

	def test_a_role_added_by_hand_is_taken_away(self):
		user = user_with_roles("Stock User")
		frappe.get_doc("User", user).add_roles("Sales Manager")
		self.assertIn("Sales Manager", own_roles(user))
		user_with_roles("Stock User")
		self.assertEqual(own_roles(user), {"Stock User"})

	def test_no_role_is_a_portal_user(self):
		user = user_with_roles()
		self.assertEqual(frappe.db.get_value("User", user, "user_type"), "Website User")
		with self.set_user(user):
			self.assertEqual(frappe.session.user, user)
