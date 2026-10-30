"""What each client gets: optional features, switched on per site.

The mechanism lives here so that every app (and the vendor's hub) uses one
list and one command. The features themselves belong to the apps that
provide them: an app declares them in its hooks.py,

    dz_features = ["dz_cod.features.FEATURES"]   # dotted path to a dict

where each entry looks like

    "labels_reports": {
        "label": "Bordereau et rapports",
        "description": "...",
        "reports": ["COD Daily Orders"],          # disabled when off
        "print_formats": ["Bordereau COD"],       # disabled when off
        "on_change": "dz_cod.features.apply_webhooks",  # optional, called with on=True/False
    }

The site's list lives in site_config.json, key "dz_features", so only the
vendor (who has the server, or the hub) can change it:

    bench --site <site> dz-features --list
    bench --site <site> dz-features --enable phone_checks
    bench --site <site> dz-features --set courier_api,labels_reports
    bench --site <site> dz-features --all          # "all": demo and test sites

Rules (dafter-cod docs/FEATURES.md):
- key missing: the base only, no option (a client site gets what it pays
  for, even one made by hand or restored without its site_config);
- "all": every feature of the site's apps (demo and test sites);
- a list, even empty: exactly that list.
  Sites made before 20 October 2026 had "key missing = everything": a patch
  wrote "all" on them (patches/keep_all_features_on_existing_sites.py).
- a feature that is off is hidden: buttons (JS reads frappe.boot.dz_features),
  reports and print formats (disabled records drop out of menus), and the
  server refuses its actions with "Fonction non incluse dans votre offre".
- apply_features() makes the site's records match the list. It runs after
  every migrate, because migrate re-imports standard reports and print
  formats and would switch them back on.

Moved from dz_cod (October 2026), where the key was "dz_cod_features": that
key is still read, and moved to "dz_features" on the next migrate.
"""

import functools
import importlib

import frappe
from frappe import _

CONFIG_KEY = "dz_features"
LEGACY_KEYS = ("dz_cod_features",)
ALL = "all"  # site_config value for every feature (demo and test sites)
MESSAGE = "Fonction non incluse dans votre offre"
HOOK = "dz_features"


class FeatureNotEnabled(frappe.PermissionError):
	pass


# ------------------------------------------------------------ the catalogue


def load(path):
	"""The dict at a dotted path. Plain import, not frappe.get_attr: the hub
	reads apps that are on the bench but not installed on its own site."""
	module, name = path.rsplit(".", 1)
	return getattr(importlib.import_module(module), name)


def merge(paths, app=None):
	features = {}
	for path in paths:
		for code, feature in load(path).items():
			features[code] = {**feature, "app": app or path.split(".", 1)[0]}
	return features


def catalog():
	"""{code: feature} of the apps installed on this site."""
	return merge(frappe.get_hooks(HOOK))


def bench_catalog():
	"""{code: feature} of every app on the bench, installed here or not.
	For the hub, which sells features of apps it does not install itself."""
	features = {}
	for app in frappe.get_all_apps():
		# frappe.get_hooks(app_name=...) refuses apps not installed on this
		# site, so read the app's hooks.py module itself
		try:
			hooks = importlib.import_module(f"{app}.hooks")
		except ImportError:
			continue
		features.update(merge(getattr(hooks, HOOK, []), app))
	return features


# ------------------------------------------------------------ the site's list


def configured():
	"""The site's setting: a list, ALL, or None when the key is missing."""
	value = frappe.conf.get(CONFIG_KEY)
	if value is None:
		value = next((frappe.conf.get(key) for key in LEGACY_KEYS if frappe.conf.get(key) is not None), None)
	if value is None or value == ALL:
		return value
	if isinstance(value, str):  # tolerate "a,b" typed by hand
		value = [part.strip() for part in value.split(",") if part.strip()]
	return list(value)


def enabled():
	"""Set of the features this site has."""
	known = catalog()
	value = configured()
	if value is None:
		return set()  # no list: the base only
	if value == ALL:
		return set(known)
	return {name for name in value if name in known}


def is_enabled(feature):
	return feature in enabled()


def check(feature):
	if not is_enabled(feature):
		raise FeatureNotEnabled(_("Fonction non incluse dans votre offre"))


def requires_feature(feature):
	"""Decorator for whitelisted methods: refuse when the feature is off.
	Put it UNDER @frappe.whitelist()."""

	def decorator(function):
		@functools.wraps(function)
		def wrapper(*args, **kwargs):
			check(feature)
			return function(*args, **kwargs)

		return wrapper

	return decorator


def boot(bootinfo):
	"""extend_bootinfo hook: the browser hides what the site doesn't have."""
	bootinfo.dz_features = sorted(enabled())


def keep_switched_off(doc, method=None):
	"""Report and Print Format validate (hooks.py): one that belongs to a
	feature not in this site's offer stays disabled. apply_features() disables
	it; without this a System Manager could tick it back on in the form, and
	Frappe runs a report as soon as it is not disabled (review of 27 October
	2026, 4.5). apply_features() writes the flag directly, so it is not
	stopped here."""
	if doc.disabled:
		return
	key = "reports" if doc.doctype == "Report" else "print_formats"
	on = enabled()
	for name, feature in catalog().items():
		if doc.name in feature.get(key, []) and name not in on:
			frappe.throw(
				_("{0} fait partie d'une fonction non incluse dans votre offre : il reste désactivé.").format(
					doc.name
				),
				FeatureNotEnabled,
			)


# ------------------------------------------------------------ apply to records


def apply_features():
	"""Make reports, print formats (and whatever an app hooks in) match the list."""
	on = enabled()
	for name, feature in catalog().items():
		disabled = 0 if name in on else 1
		for report in feature.get("reports", []):
			if frappe.db.exists("Report", report):
				frappe.db.set_value("Report", report, "disabled", disabled, update_modified=False)
		for print_format in feature.get("print_formats", []):
			if frappe.db.exists("Print Format", print_format):
				frappe.db.set_value("Print Format", print_format, "disabled", disabled, update_modified=False)
		if feature.get("on_change"):
			frappe.get_attr(feature["on_change"])(name in on)
	frappe.clear_cache()


def set_features(features):
	"""Write the site's setting (a list, or ALL for every feature) and apply it."""
	from frappe.installer import update_site_config

	if features == ALL:
		update_site_config(CONFIG_KEY, ALL)
	else:
		known = catalog()
		unknown = [name for name in features if name not in known]
		if unknown:
			frappe.throw(_("Fonctions inconnues : {0}").format(", ".join(unknown)))
		update_site_config(CONFIG_KEY, sorted(set(features)))
	for key in LEGACY_KEYS:
		if frappe.conf.get(key) is not None:
			update_site_config(key, "None")
	frappe.local.conf = frappe._dict(frappe.get_site_config())
	apply_features()


def move_legacy_key():
	"""after_migrate: a site made before the move keeps its list under the new key."""
	if frappe.conf.get(CONFIG_KEY) is None and configured() is not None:
		from frappe.installer import update_site_config

		update_site_config(CONFIG_KEY, configured())
		for key in LEGACY_KEYS:
			update_site_config(key, "None")
		frappe.local.conf = frappe._dict(frappe.get_site_config())
