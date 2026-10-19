"""Bench command: which optional features a client site has (dz_core/features.py).

    bench --site client1.localhost dz-features --list
    bench --site client1.localhost dz-features --enable phone_checks --enable courier_api
    bench --site client1.localhost dz-features --disable labels_reports
    bench --site client1.localhost dz-features --set courier_api,phone_checks
    bench --site client1.localhost dz-features --set ""      # base only
    bench --site client1.localhost dz-features --all         # everything (removes the key)

Add --json for a machine-readable answer (used by the hub). dz_cod keeps the
old name `dz-cod-features` as an alias of this command.
"""

import json

import click
from frappe.commands import get_site, pass_context


@click.command("dz-features")
@click.option("--list", "show", is_flag=True, help="Show each feature, on or off")
@click.option("--enable", multiple=True, help="Switch a feature on (repeatable)")
@click.option("--disable", multiple=True, help="Switch a feature off (repeatable)")
@click.option("--set", "exact", default=None, help='Exact list, comma separated ("" = base only)')
@click.option("--all", "everything", is_flag=True, help="Every feature (removes the key)")
@click.option("--json", "as_json", is_flag=True, help="Answer in JSON")
@pass_context
def dz_features(context, show, enable, disable, exact, everything, as_json):
	"""Optional features of a client site (the apps declare them, dz_core switches them)."""
	import frappe

	from dz_core import features as F

	site = get_site(context)
	frappe.init(site=site)
	frappe.connect()
	try:
		if "dz_core" not in frappe.get_installed_apps():
			raise click.ClickException(f"dz_core is not installed on {site}")

		changed = everything or exact is not None or enable or disable
		if everything:
			F.set_features(None)
		elif exact is not None or enable or disable:
			current = set(F.enabled()) if exact is None else set()
			if exact:
				current |= {name.strip() for name in exact.split(",") if name.strip()}
			current |= set(enable)
			current -= set(disable)
			F.set_features(sorted(current))
		if changed:
			frappe.db.commit()

		on = F.enabled()
		known = F.catalog()
		result = {
			"site": site,
			"apps": frappe.get_installed_apps(),
			"configured": F.configured() is not None,
			"features": {name: name in on for name in known},
		}
		if as_json:
			click.echo(json.dumps(result))
		elif show or changed:
			origin = "list in site_config" if result["configured"] else "no list: everything is on"
			click.echo(f"{site} ({origin})")
			if not known:
				click.echo("  no optional features in this site's apps")
			for name, feature in known.items():
				click.echo(
					f"  [{'x' if name in on else ' '}] {name:16} {feature['label']} ({feature['app']})"
				)
		else:
			click.echo(click.get_current_context().get_help())
	finally:
		frappe.destroy()


commands = [dz_features]
