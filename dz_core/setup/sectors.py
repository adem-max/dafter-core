"""Sector templates: what a new client gets prepared for their trade.

A template is plain data (the dicts below) plus apply_sector(), which creates
what is missing and never overwrites what exists. Adding a sector means adding
one entry to SECTORS: no new code.

What a template does NOT contain: the client's own items, recipes (BOMs),
prices or stock. Those are data the client provides through the import
templates (dz_core/imports).
"""

import frappe
from frappe.utils.nestedset import get_root_of

FOOD = "Alimentaire et cosmétique"
CLOTHING = "Confection"

# The three warehouses every producer uses (name, setting field in DZ Core Settings).
# ERPNext's setup wizard (in French) already makes "Travaux en cours" and
# "Produits finis", plus "Magasins" and "Les marchandises en transit": we reuse
# them and only add "Matières premières".
WAREHOUSES = [
	("Matières premières", "raw_materials_warehouse"),
	("Travaux en cours", "wip_warehouse"),
	("Produits finis", "finished_goods_warehouse"),
]

# Item groups whose items are stored in Produits finis; every other group of the
# template goes to Matières premières (fabric, trims, packaging...)
FINISHED_GROUPS = ["Produits finis"]

SECTORS = {
	FOOD: {
		# Item groups under "All Item Groups"
		"item_groups": ["Matières premières", "Emballages", "Produits finis"],
		# Units the trade counts in, on top of ERPNext's own (Kg, Gram, Litre...)
		# (name, whole number only?)
		"uoms": [("Pot", 1), ("Flacon", 1), ("Sachet", 1), ("Carton", 1), ("Bocal", 1)],
		# Batch and expiry tracking: applied by the importer to items of these groups
		"batch_groups": ["Matières premières", "Produits finis"],
		"item_attributes": {},
		# Stock Settings switched on (never switched off). ERPNext v16 refuses
		# batch tracking on any item until this one is on.
		"stock_settings": {"enable_serial_and_batch_no_for_item": 1},
	},
	CLOTHING: {
		"item_groups": ["Tissus", "Fournitures", "Emballages", "Produits finis"],
		"uoms": [("Pièce", 1), ("Rouleau", 1), ("Carton", 1), ("Cône", 0)],
		"batch_groups": [],
		# One BOM per model (template item), the variants carry size and colour
		"item_attributes": {
			"Taille": [("XS", "XS"), ("S", "S"), ("M", "M"), ("L", "L"), ("XL", "XL"), ("XXL", "XXL")],
			"Couleur": [
				("Noir", "NOI"),
				("Blanc", "BLA"),
				("Gris", "GRI"),
				("Bleu", "BLE"),
				("Rouge", "ROU"),
				("Vert", "VER"),
				("Beige", "BEI"),
			],
		},
		"stock_settings": {},
	},
}


def apply_sector(sector, company):
	"""Create the sector's item groups, units, attributes and the warehouses.
	Returns {setting field: warehouse name} for DZ Core Settings."""
	if sector not in SECTORS:
		frappe.throw(f"Secteur inconnu : {sector}. Choix : {', '.join(SECTORS)}")
	template = SECTORS[sector]
	create_item_groups(template["item_groups"])
	create_uoms(template["uoms"])
	create_item_attributes(template["item_attributes"])
	switch_on_stock_settings(template["stock_settings"])
	warehouses = create_warehouses(company)
	setup_company_warehouses(company, warehouses)
	setup_item_group_warehouses(company, template["item_groups"], warehouses)
	remove_wizard_item_groups()
	return warehouses


# Item groups ERPNext's setup wizard creates in English. They confuse a client
# choosing a group next to the sector's French ones. "Services" stays: a
# producer still bills services, and the word is the same in French.
WIZARD_ITEM_GROUPS = ["Products", "Raw Material", "Sub Assemblies", "Consumable"]


def remove_wizard_item_groups():
	"""Delete the wizard's English groups nobody uses. A group still used by an
	item (or anything else) is kept: Frappe refuses to delete a linked record."""
	for name in WIZARD_ITEM_GROUPS:
		if not frappe.db.exists("Item Group", name) or frappe.db.exists("Item", {"item_group": name}):
			continue
		try:
			frappe.delete_doc("Item Group", name, ignore_permissions=True)
		except frappe.LinkExistsError:
			frappe.clear_messages()
			frappe.logger("dz_core").info(f"Item Group {name} kept: still linked")


def create_item_groups(names):
	root = get_root_of("Item Group")
	for name in names:
		if not frappe.db.exists("Item Group", name):
			frappe.get_doc(
				{"doctype": "Item Group", "item_group_name": name, "parent_item_group": root, "is_group": 0}
			).insert(ignore_permissions=True)


def create_uoms(uoms):
	for name, whole in uoms:
		if not frappe.db.exists("UOM", name):
			frappe.get_doc({"doctype": "UOM", "uom_name": name, "must_be_whole_number": whole}).insert(
				ignore_permissions=True
			)


def create_item_attributes(attributes):
	for name, values in attributes.items():
		if frappe.db.exists("Item Attribute", name):
			continue
		frappe.get_doc(
			{
				"doctype": "Item Attribute",
				"attribute_name": name,
				"item_attribute_values": [{"attribute_value": value, "abbr": abbr} for value, abbr in values],
			}
		).insert(ignore_permissions=True)


def switch_on_stock_settings(settings):
	for field, value in settings.items():
		if not frappe.db.get_single_value("Stock Settings", field):
			frappe.db.set_single_value("Stock Settings", field, value)


def create_warehouses(company):
	abbr = frappe.get_cached_value("Company", company, "abbr")
	root = frappe.db.get_value(
		"Warehouse", {"company": company, "is_group": 1, "parent_warehouse": ["is", "not set"]}
	)
	result = {}
	for name, setting in WAREHOUSES:
		full_name = f"{name} - {abbr}"
		if not frappe.db.exists("Warehouse", full_name):
			frappe.get_doc(
				{"doctype": "Warehouse", "warehouse_name": name, "company": company, "parent_warehouse": root}
			).insert(ignore_permissions=True)
		result[setting] = full_name
	return result


def setup_company_warehouses(company, warehouses):
	"""Work orders work in Travaux en cours and put their output in Produits finis.

	ERPNext v16 keeps these on the Company (section "Warehouse Defaults"), no
	longer in Stock Settings or Manufacturing Settings. Only empty ones are filled.
	The company's general default stays the wizard's "Magasins": items get
	their warehouse from their group instead (setup_item_group_warehouses)."""
	doc = frappe.get_doc("Company", company)
	changed = False
	for field, value in (
		("default_wip_warehouse", warehouses["wip_warehouse"]),
		("default_fg_warehouse", warehouses["finished_goods_warehouse"]),
	):
		if not doc.get(field):
			doc.set(field, value)
			changed = True
	if changed:
		doc.save(ignore_permissions=True)


def setup_item_group_warehouses(company, groups, warehouses):
	"""Item group defaults: raw materials, fabric and packaging are received in
	Matières premières, finished products are stored and sold from Produits finis.
	An item without its own default takes its group's. Existing rows are kept."""
	for group in groups:
		warehouse = (
			warehouses["finished_goods_warehouse"]
			if group in FINISHED_GROUPS
			else warehouses["raw_materials_warehouse"]
		)
		doc = frappe.get_doc("Item Group", group)
		if any(row.company == company for row in doc.item_group_defaults):
			continue
		doc.append("item_group_defaults", {"company": company, "default_warehouse": warehouse})
		doc.save(ignore_permissions=True)
