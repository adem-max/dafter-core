"""Helpers shared by dz_core's tests and the apps on top (dz_cod imports them)."""

import frappe


def user_with_roles(*roles):
	"""A login holding exactly these roles: made once, and its roles reset on
	every call, so a role added by hand cannot widen a test. The email names
	the roles (stock_user@test.dz); no role at all gives a portal Website User
	(website_user@test.dz). Enter it with `with self.set_user(user):`."""
	roles = sorted(roles)
	email = ("-".join(frappe.scrub(role) for role in roles) or "website_user") + "@test.dz"
	if frappe.db.exists("User", email):
		user = frappe.get_doc("User", email)
	else:
		user = frappe.new_doc("User")
		user.update({"email": email, "first_name": email.split("@")[0], "send_welcome_email": 0})
	user.set("roles", [{"role": role} for role in roles])
	user.save(ignore_permissions=True)
	return email
