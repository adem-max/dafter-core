"""The optional-features mechanism (dz_core/features.py), with a fake app's
feature so these tests do not depend on dz_cod. dz_cod tests its own four.

Run: bench --site <site> run-tests --module dz_core.tests.test_features
"""

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from dz_core import features as F

# What an app would point its `dz_features` hook at
FAKE = {
	"demo_feature": {"label": "Démo", "description": "Pour les tests", "reports": [], "print_formats": []}
}
FAKE_PATH = "dz_core.tests.test_features.FAKE"
real_get_hooks = frappe.get_hooks


def fake_hooks(hook=None, *args, **kwargs):
	if hook == F.HOOK and not kwargs.get("app_name"):
		return [FAKE_PATH]
	return real_get_hooks(hook, *args, **kwargs)


def site_list(value=None, key=F.CONFIG_KEY):
	"""The site's list for one `with` block (None = no key at all)."""
	conf = {name: None for name in (F.CONFIG_KEY, *F.LEGACY_KEYS)}
	conf[key] = value
	return patch.dict(frappe.local.conf, {k: v for k, v in conf.items() if v is not None}, clear=False)


class TestFeatures(IntegrationTestCase):
	def setUp(self):
		patcher = patch("frappe.get_hooks", side_effect=fake_hooks)
		patcher.start()
		self.addCleanup(patcher.stop)
		saved = {key: frappe.local.conf.pop(key, None) for key in (F.CONFIG_KEY, *F.LEGACY_KEYS)}
		self.addCleanup(lambda: frappe.local.conf.update({k: v for k, v in saved.items() if v is not None}))

	def test_catalog_knows_which_app_declared_each_feature(self):
		self.assertEqual(F.catalog()["demo_feature"]["app"], "dz_core")

	def test_missing_key_means_the_base_only(self):
		self.assertEqual(F.enabled(), set())

	def test_all_means_every_feature(self):
		with site_list(F.ALL):
			self.assertEqual(F.enabled(), {"demo_feature"})

	def test_list_is_followed_and_unknown_names_ignored(self):
		with site_list([]):
			self.assertFalse(F.is_enabled("demo_feature"))
		with site_list(["demo_feature", "teleportation"]):
			self.assertEqual(F.enabled(), {"demo_feature"})

	def test_old_dz_cod_key_is_still_read(self):
		with site_list([], key="dz_cod_features"):
			self.assertEqual(F.enabled(), set())

	def test_requires_feature_refuses_with_the_offer_message(self):
		@F.requires_feature("demo_feature")
		def action():
			return "done"

		with site_list(["demo_feature"]):
			self.assertEqual(action(), "done")
		with site_list([]), self.assertRaises(F.FeatureNotEnabled):
			action()
		with self.assertRaises(F.FeatureNotEnabled):
			action()  # no list at all

	def test_boot_lists_the_features(self):
		bootinfo = frappe._dict()
		with site_list(F.ALL):
			F.boot(bootinfo)
		self.assertEqual(bootinfo.dz_features, ["demo_feature"])

	def test_sites_made_before_keep_every_feature(self):
		# patches/keep_all_features_on_existing_sites.py: no list becomes "all"
		from dz_core.patches import keep_all_features_on_existing_sites as old_sites

		with (
			patch("frappe.installer.update_site_config") as write,
			patch("frappe.get_site_config", return_value=dict(frappe.local.conf)),
		):
			old_sites.execute()
			write.assert_called_once_with(F.CONFIG_KEY, F.ALL)
			write.reset_mock()
			with site_list([]):
				old_sites.execute()  # a site with a list (a client's) is left alone
			write.assert_not_called()


class TestBenchCatalog(IntegrationTestCase):
	def test_reads_apps_that_are_not_installed_here(self):
		# The hub sells features of apps it does not install on its own site
		catalog = F.bench_catalog()
		if "dz_cod" in frappe.get_all_apps():
			self.assertEqual(catalog["courier_api"]["app"], "dz_cod")
		for feature in catalog.values():
			self.assertIn("label", feature)
