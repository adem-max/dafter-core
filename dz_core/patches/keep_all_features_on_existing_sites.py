"""Until 20 October 2026 a site without a feature list had every feature on.
The rule is now "no list = the base only", so that a client site made by hand
or restored without its site_config gets no paid option for free. This keeps
the sites made before as they were (demo, test and dev sites): no list
becomes "all".

New sites skip it: Frappe marks an app's patches as done when it installs it.
"""

import frappe

from dz_core.features import ALL, CONFIG_KEY, LEGACY_KEYS


def execute():
	if any(frappe.conf.get(key) is not None for key in (CONFIG_KEY, *LEGACY_KEYS)):
		return  # the site already has a list (a client site set up by the hub)
	from frappe.installer import update_site_config

	update_site_config(CONFIG_KEY, ALL)
	frappe.local.conf = frappe._dict(frappe.get_site_config())
