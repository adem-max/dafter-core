"""Changes to ERPNext's Algerian chart of accounts ("Algerie - Plan Comptable
General 2 avec code") that every Daftar company gets, from the SCF advice
of 21 October 2026 (DECISIONS.md, "Chart of accounts and default accounts").

The chart lacks accounts a small Algerian business needs (reserves, the
owner's account, machines, courier collections, IFU...), types some accounts
oddly (666 / 766 as "Round Off") and still carries the TAP, repealed by the
2024 finance law. `apply_chart_changes` fixes that, idempotently:

- creates the missing accounts (CREATE), under their SCF parent;
- turns five ledgers into groups (CONVERT), which ERPNext allows only while
  the account has no ledger entry at all: a non-empty one is skipped, and
  the accounts meant to sit under it wait until it can be converted;
- re-types accounts (RETYPE) so ERPNext's pickers offer them;
- moves "Ouverture temporaire" to 479 under a class 47 liability group;
- disables accounts nobody should post to (DISABLE), unless one is in use
  as a default somewhere.
"""

import frappe

# Group made by us (no number in the chart, named like its asset twin)
TRANSIT_LIABILITIES = "47-Comptes transitoires ou d'attente (PASSIF)"
LIABILITIES_ROOT = "CLASSE 4 : TIERS (PASSIF)"
SUNDRY_ASSETS = "46-Débiteurs divers et créditeurs divers (ACTIF)"

# Ledgers that become groups (only while they have no entry at all)
CONVERT = ["11", "12", "5118", "6588", "7588"]

# (number, name, parent: a number or a group name, is_group, account type)
CREATE = [
	("106", "Réserves", "10", 1, None),
	("1061", "Réserve légale", "106", 0, None),
	("1063", "Réserves statutaires ou contractuelles", "106", 0, None),
	("1068", "Autres réserves", "106", 0, None),
	("108", "Compte de l'exploitant", "10", 0, None),
	("1018", "Fonds d'exploitation (exploitant individuel)", "101", 0, None),
	("110", "Report à nouveau (solde créditeur)", "11", 0, None),
	("119", "Report à nouveau (solde débiteur)", "11", 0, None),
	("120", "Résultat de l'exercice (bénéfice)", "12", 0, None),
	("129", "Résultat de l'exercice (perte)", "12", 0, None),
	("215", "Installations techniques, matériel et outillage industriels", "21", 0, "Fixed Asset"),
	("35831", "Chutes et déchets de production", "3583", 0, "Stock"),
	("35511", "Produits finis", "3551", 0, "Stock"),
	("35519", "Produits finis : complément de coût d'inventaire", "3551", 0, None),
	("445711", "TVA collectée sur livraisons de biens - 19 %", "44571", 0, "Tax"),
	("445712", "TVA collectée sur livraisons de biens - 9 %", "44571", 0, "Tax"),
	("445751", "Droits de timbre de quittance à reverser", "44575", 0, "Tax"),
	("467", "Autres comptes débiteurs ou créditeurs", SUNDRY_ASSETS, 1, None),
	("4671", "Transporteurs : encaissements à reverser", "467", 1, None),
	("4477", "IFU à payer", "447", 0, None),
	("6428", "IFU", "642", 0, None),
	("4781", "Versements à identifier", TRANSIT_LIABILITIES, 0, None),
	("6132", "Locations immobilières", "613", 0, None),
	("6135", "Locations mobilières", "613", 0, None),
	("6589", "Charges à reclasser (contrôle Daftar)", "658", 0, None),
	("65881", "Écarts d'arrondi", "6588", 0, None),
	("65882", "Écarts de règlement et sur versements (pertes)", "6588", 0, None),
	("65888", "Autres charges diverses de gestion courante", "6588", 0, None),
	("75882", "Écarts de règlement et sur versements (gains)", "7588", 0, None),
	("75888", "Autres produits divers de gestion courante", "7588", 0, None),
	("51181", "Paiements par carte (TPE) à encaisser", "5118", 0, "Bank"),
]

# number -> ERPNext account type ("" = none)
RETYPE = {
	"4083": "Asset Received But Not Billed",
	"6571": "Stock Adjustment",
	"6572": "Stock Adjustment",
	"666": "",
	"766": "",
	"5111": "Bank",
	"7088": "Income Account",
	# ERPNext's advance-account pickers ask for these types
	"4191": "Receivable",
	"40913": "Payable",
	"40916": "Payable",
}

OPENING = ("479", "Ouverture temporaire")

# TAP (repealed by LF 2024 art. 14), works and studies income, and the
# accounts the setup wizard used to pick as defaults
DISABLE = ["6421", "6422", "4471", "5176", "3451", "4172", "72235"]
DISABLE_PREFIXES = ["704", "705"]


def by_number(company, number, is_group=None):
	filters = {"company": company, "account_number": number}
	if is_group is not None:
		filters["is_group"] = is_group
	return frappe.db.get_value("Account", filters)


def parent_of(company, parent):
	"""A parent given by number, else by its name (the unnumbered groups)."""
	return by_number(company, parent, is_group=1) or frappe.db.get_value(
		"Account", {"company": company, "account_name": parent, "is_group": 1}
	)


def apply_chart_changes(company):
	"""Returns the list of what was done or skipped, for the patch's log."""
	log = []
	transit_group(company)
	for number in CONVERT:
		convert_to_group(company, number, log)
	for number, name, parent, is_group, account_type in CREATE:
		create(company, number, name, parent, is_group, account_type, log)
	for number, account_type in RETYPE.items():
		account = by_number(company, number, is_group=0)
		if account and (frappe.db.get_value("Account", account, "account_type") or "") != account_type:
			frappe.db.set_value("Account", account, "account_type", account_type or None)
			log.append(f"re-typed {number}: {account_type or 'none'}")
	move_opening_account(company, log)
	disable_unused(company, log)
	frappe.clear_cache(doctype="Account")
	return log


def transit_group(company):
	if frappe.db.exists("Account", {"company": company, "account_name": TRANSIT_LIABILITIES}):
		return
	root = frappe.db.get_value(
		"Account", {"company": company, "account_name": LIABILITIES_ROOT, "is_group": 1}
	)
	if root:
		insert(company, None, TRANSIT_LIABILITIES, root, 1, None)


def convert_to_group(company, number, log):
	account = by_number(company, number, is_group=0)
	if not account:
		return
	if frappe.db.exists("GL Entry", {"account": account}):
		log.append(f"{number} not converted to a group: it has ledger entries")
		return
	doc = frappe.get_doc("Account", account)
	doc.flags.ignore_permissions = True
	doc.convert_ledger_to_group()
	log.append(f"{number} converted to a group")


def create(company, number, name, parent, is_group, account_type, log):
	if by_number(company, number):
		return
	parent_account = parent_of(company, parent)
	if not parent_account:
		log.append(f"{number} not created: no group {parent} (yet)")
		return
	insert(company, number, name, parent_account, is_group, account_type)
	log.append(f"created {number} {name}")


def insert(company, number, name, parent_account, is_group, account_type):
	return (
		frappe.get_doc(
			{
				"doctype": "Account",
				"company": company,
				"account_name": name,
				"account_number": number,
				"parent_account": parent_account,
				"is_group": is_group,
				"account_type": account_type,
			}
		)
		.insert(ignore_permissions=True)
		.name
	)


def move_opening_account(company, log):
	"""dz_core's "Ouverture temporaire" (setup/accounts.py) becomes 479 under
	the class 47 liability group, keeping its type Temporary."""
	number, name = OPENING
	account = frappe.db.get_value(
		"Account",
		{"company": company, "account_type": "Temporary", "is_group": 0},
		["name", "account_number"],
		as_dict=True,
	)
	group = frappe.db.get_value("Account", {"company": company, "account_name": TRANSIT_LIABILITIES})
	if not account or not group or account.account_number == number:
		return
	from erpnext.accounts.doctype.account.account import update_account_number

	update_account_number(account.name, name, number)
	renamed = by_number(company, number)
	doc = frappe.get_doc("Account", renamed)
	if doc.parent_account != group:
		doc.parent_account = group
		doc.save(ignore_permissions=True)
	log.append(f"{name} is now {number}, under class 47")


def in_use(account):
	"""Is the account a default somewhere (company, item group, mode of payment...)?"""
	company = frappe.db.get_value("Account", account, "company")
	company_fields = [
		f.fieldname
		for f in frappe.get_meta("Company").fields
		if f.fieldtype == "Link" and f.options == "Account"
	]
	if any(frappe.db.get_value("Company", company, field) == account for field in company_fields):
		return True
	for doctype, field in (
		("Item Default", "default_inventory_account"),
		("Item Default", "default_cogs_account"),
		("Item Default", "expense_account"),
		("Item Default", "income_account"),
		("Mode of Payment Account", "default_account"),
		("Party Account", "account"),
		("Warehouse", "account"),
	):
		if frappe.db.exists(doctype, {field: account}):
			return True
	return False


def disable_unused(company, log):
	numbers = list(DISABLE)
	for prefix in DISABLE_PREFIXES:
		numbers += frappe.get_all(
			"Account",
			filters={"company": company, "is_group": 0, "account_number": ["like", f"{prefix}%"]},
			pluck="account_number",
		)
	for number in numbers:
		account = by_number(company, number, is_group=0)
		if not account or frappe.db.get_value("Account", account, "disabled"):
			continue
		if in_use(account):
			log.append(f"{number} left enabled: still a default somewhere")
			continue
		frappe.db.set_value("Account", account, "disabled", 1)
		log.append(f"disabled {number}")
