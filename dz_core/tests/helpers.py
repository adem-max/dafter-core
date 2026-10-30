"""Helpers shared by dz_core's tests and the apps on top (dz_cod imports them)."""

import ast
import os

import frappe


def whitelisted(app):
	"""Dotted paths of the app's module-level functions under @frappe.whitelist,
	read from the source. The endpoint sweeps (test_endpoints) fail when one is
	not listed there, so nobody adds an endpoint without saying how it is
	protected. Doctype methods are left out: Frappe checks the document's
	permission before running them."""
	root = frappe.get_app_path(app)
	found = set()
	for folder, _dirs, files in os.walk(root):
		if f"{os.sep}tests" in folder:
			continue
		for name in files:
			if not name.endswith(".py"):
				continue
			path = os.path.join(folder, name)
			with open(path, encoding="utf-8") as handle:
				tree = ast.parse(handle.read())
			module = app + "." + os.path.relpath(path, root)[:-3].replace(os.sep, ".")
			for node in tree.body:
				if isinstance(node, ast.FunctionDef) and any(
					"whitelist" in ast.unparse(decorator) for decorator in node.decorator_list
				):
					found.add(f"{module}.{node.name}")
	return found


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
