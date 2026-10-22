"""Load a producer demo on a dedicated site (ERPNext + dz_core only).

    bench --site food-demo.localhost execute dz_core.demo.loader.load --kwargs "{'profile': 'food'}"
    bench --site atelier-demo.localhost execute dz_core.demo.loader.load --kwargs "{'profile': 'clothing'}"

Keep `bench start` running: the load posts hundreds of backdated documents and
ERPNext's workers process what follows them.

Steps:
 1. refuse a site that holds another company's data
 2. prepare() the company (wizard, sector, warehouses, tax regime), fiscal
    years, legal mentions, address
 3. masters through the client import workbook (workbook.py), reorder levels
    included, opening stock dated the first day of the story
 4. what the workbook does not hold yet: customer groups, price lists and
    prices, users
 5. the story: planner.py plans it, engine.py posts it, day by day to today

Safe to run again: done steps and events are skipped, and a later run
continues the story up to the new today. The story starts on the date stored
at the first run (dz_demo::<profile>::start).
"""

import importlib

import frappe
from frappe.utils import add_days, getdate, nowdate
from frappe.utils.nestedset import get_root_of

from dz_core.demo.engine import PREFIX, Engine
from dz_core.demo.planner import plan
from dz_core.demo.workbook import import_masters

PROFILES = ("food", "clothing")
DEMO_PASSWORD = "Demo-2026!"  # demo sites only, written in docs/DEMO.md


def load(profile="food", weeks=13, seed=2026):
	if profile not in PROFILES:
		frappe.throw(f"Profil inconnu : {profile}. Choix : {', '.join(PROFILES)}")
	p = importlib.import_module(f"dz_core.demo.{profile}")
	check_site_is_for_demo(p)

	start = story_start(profile, int(weeks))
	print(f"1/5 Société {p.COMPANY} ({p.SECTOR}, {p.TAX_REGIME})...")
	setup_company(p, start)
	print("2/5 Classeur d'import (fournisseurs, clients, articles, nomenclatures, stock initial)...")
	once(profile, "masters", lambda: import_masters(profile, p, start))
	print("3/5 Prix, groupes de clients, utilisateurs...")
	setup_extras(p)
	frappe.db.commit()
	print(f"4/5 Histoire du {start} à aujourd'hui (quelques minutes)...")
	events = plan(p, start, getdate(nowdate()), int(seed))
	posted = Engine(profile, p).run(events)
	print(f"5/5 {posted} événements postés.")
	print_summary(p)


def check_site_is_for_demo(p):
	"""Never load fake data into a client's site."""
	if "dz_core" not in frappe.get_installed_apps():
		frappe.throw("Démo : installez d'abord dz_core sur ce site.")
	company = frappe.db.get_single_value("DZ Core Settings", "company")
	if company and company != p.COMPANY:
		frappe.throw(f"Ce site est préparé pour « {company} ». La démo doit tourner sur un site dédié.")
	for doctype in ("Sales Invoice", "Sales Order", "Work Order", "Purchase Invoice"):
		other = frappe.db.count(doctype, {"company": ["!=", p.COMPANY]})
		if other:
			frappe.throw(f"Ce site contient {other} documents « {doctype} » d'une autre société.")
	if "dz_cod" in frappe.get_installed_apps():
		print("Attention : dz_cod est installé ; ces démos montrent le Pack Atelier seul.")


def story_start(profile, weeks):
	key = f"{PREFIX}::{profile}::start"
	start = frappe.db.get_default(key)
	if not start:
		start = str(add_days(nowdate(), -7 * weeks))
		frappe.db.set_default(key, start)
	return getdate(start)


def once(profile, step, function):
	key = f"{PREFIX}::{profile}::step::{step}"
	if frappe.db.get_default(key):
		return
	function()
	frappe.db.set_default(key, "1")
	frappe.db.commit()


# ------------------------------------------------------------ company


def setup_company(p, start):
	from dz_core.setup.new_client import make_atelier_the_home_page, prepare

	if frappe.db.get_single_value("DZ Core Settings", "company") != p.COMPANY:
		prepare(p.COMPANY, p.ABBR, p.SECTOR, p.TAX_REGIME)
	demo_accounting(p.COMPANY, p.SECTOR)
	# a demo prepared before the home page existed lands there too
	make_atelier_the_home_page()
	ensure_fiscal_years(start)
	company = frappe.get_doc("Company", p.COMPANY)
	company.update(p.LEGAL)
	company.save(ignore_permissions=True)
	ensure_address(p)


def demo_accounting(company, sector):
	"""The SCF set-up (again, for a demo built before it), with one demo-only
	difference: no immutable ledger. A demo is wiped and replayed, and an
	immutable ledger would leave each wiped document's lines in its month and
	their reversal on the day of the wipe. Returns the set-up's log."""
	from dz_core.dz_core.doctype.dz_core_settings.dz_core_settings import REEL
	from dz_core.setup.scf import apply_scf_setup

	log = apply_scf_setup(company, sector)
	frappe.db.set_single_value("Accounts Settings", "enable_immutable_ledger", 0)
	# a régime réel demo shows the stamp duty on its cash invoices (stamp.py)
	settings = frappe.get_single("DZ Core Settings")
	if settings.company == company and settings.tax_regime == REEL and not settings.stamp_duty:
		settings.stamp_duty = 1
		settings.save(ignore_permissions=True)
		log.append("stamp duty on")
	return log


def ensure_fiscal_years(start):
	for year in range(start.year, getdate(nowdate()).year + 1):
		if not frappe.db.exists("Fiscal Year", {"year_start_date": f"{year}-01-01"}):
			frappe.get_doc(
				{
					"doctype": "Fiscal Year",
					"year": str(year),
					"year_start_date": f"{year}-01-01",
					"year_end_date": f"{year}-12-31",
				}
			).insert(ignore_permissions=True)


def ensure_address(p):
	title = f"{p.COMPANY} - Siège"
	if frappe.db.exists("Address", {"address_title": p.COMPANY}):
		return
	frappe.get_doc(
		{
			"doctype": "Address",
			"address_title": p.COMPANY,
			"address_type": "Billing",
			"address_line1": p.ADDRESS["line"],
			"city": p.ADDRESS["city"],
			"state": p.ADDRESS["wilaya"],
			"country": "Algeria",
			"is_your_company_address": 1,
			"is_primary_address": 1,
			"links": [{"link_doctype": "Company", "link_name": p.COMPANY}],
		}
	).insert(ignore_permissions=True)
	return title


# ------------------------------------------------------------ extras


def setup_extras(p):
	setup_customer_groups(p)
	setup_prices(p)
	setup_users(p)


def setup_customer_groups(p):
	root = get_root_of("Customer Group")
	for customer in p.CUSTOMERS:
		group = customer["group"]
		if not frappe.db.exists("Customer Group", group):
			frappe.get_doc(
				{"doctype": "Customer Group", "customer_group_name": group, "parent_customer_group": root}
			).insert(ignore_permissions=True)
		name = frappe.db.get_value("Customer", {"customer_name": customer["name"]})
		if name:
			frappe.db.set_value("Customer", name, "customer_group", group)


def setup_prices(p):
	for price_list, prices in p.PRICE_LISTS.items():
		if not frappe.db.exists("Price List", price_list):
			frappe.get_doc(
				{
					"doctype": "Price List",
					"price_list_name": price_list,
					"currency": "DZD",
					"selling": 1,
					"enabled": 1,
				}
			).insert(ignore_permissions=True)
		for item_code, rate in prices.items():
			existing = frappe.db.get_value("Item Price", {"item_code": item_code, "price_list": price_list})
			if existing:
				continue
			frappe.get_doc(
				{
					"doctype": "Item Price",
					"item_code": item_code,
					"price_list": price_list,
					"price_list_rate": rate,
				}
			).insert(ignore_permissions=True)


def setup_users(p):
	from frappe.utils.password import update_password

	site = frappe.local.site
	for login, first_name, roles, language in p.USERS:
		email = f"{login}@{site}"
		if frappe.db.exists("User", email):
			# a role added to the profile later reaches the existing login
			user = frappe.get_doc("User", email)
			missing = set(roles) - {row.role for row in user.roles}
			if missing:
				user.add_roles(*sorted(missing))
			continue
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": first_name,
				"user_type": "System User",
				"language": language,
				"send_welcome_email": 0,
				"roles": [{"role": role} for role in roles],
			}
		)
		user.flags.no_welcome_mail = True
		user.insert(ignore_permissions=True)
		update_password(email, DEMO_PASSWORD)


# ------------------------------------------------------------ summary


def print_summary(p):
	print(f"\n{p.COMPANY}")
	for doctype in (
		"Purchase Order",
		"Purchase Receipt",
		"Purchase Invoice",
		"Work Order",
		"Sales Order",
		"Delivery Note",
		"Sales Invoice",
		"Payment Entry",
		"Stock Reconciliation",
	):
		print(f"  {doctype:22} {frappe.db.count(doctype, {'docstatus': 1})}")
	print(
		f"  Connexion : <login>@{frappe.local.site} / {DEMO_PASSWORD}  ({', '.join(u[0] for u in p.USERS)})"
	)
