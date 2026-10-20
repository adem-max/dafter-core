"""Report "Coût de revient": what one unit of each product costs, and earns.

One row per product with a default recipe (BOM): its materials at today's
prices, its labour, the selling price and the margin. Open a row to see the
materials one by one. Clothing: one row per model (one recipe for all its
sizes and colours, DECISIONS.md).

Materials are priced at the last receipt by default, so a dearer sugar
delivery shows in every jam at once; "Coût moyen en stock" prices them at
what the stock is worth instead. Labour is what the manufacture entries of
the last 90 days added per unit (dz_core does not use BOM operations).
"""

import frappe
from frappe import _
from frappe.utils import add_days, flt, nowdate

from dz_core.reports import LAST_PURCHASE, Rates, get_company

LABOUR_DAYS = 90


def execute(filters=None):
	filters = frappe._dict(filters or {})
	filters.company = get_company(filters)
	filters.price_list = filters.price_list or "Standard Selling"
	rates = Rates(filters.rate_basis or LAST_PURCHASE)
	rows = get_rows(filters, rates)
	products = [row for row in rows if not row["indent"]]
	return get_columns(), rows, None, get_chart(products), get_summary(products)


def get_columns():
	return [
		{"fieldname": "item", "label": _("Article"), "fieldtype": "Link", "options": "Item", "width": 190},
		{"fieldname": "item_name", "label": _("Désignation"), "fieldtype": "Data", "width": 210},
		{"fieldname": "qty", "label": _("Qté par unité"), "fieldtype": "Float", "precision": 4, "width": 105},
		{"fieldname": "uom", "label": _("Unité"), "fieldtype": "Data", "width": 75},
		{"fieldname": "rate", "label": _("Prix unitaire"), "fieldtype": "Currency", "width": 105},
		{"fieldname": "materials", "label": _("Coût matières"), "fieldtype": "Currency", "width": 115},
		{"fieldname": "labour", "label": _("Main-d'œuvre"), "fieldtype": "Currency", "width": 110},
		{"fieldname": "cost", "label": _("Coût de revient"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "price", "label": _("Prix de vente"), "fieldtype": "Currency", "width": 110},
		{"fieldname": "margin", "label": _("Marge"), "fieldtype": "Currency", "width": 100},
		{"fieldname": "margin_pct", "label": _("Marge %"), "fieldtype": "Percent", "width": 85},
		{
			"fieldname": "last_cost",
			"label": _("Dernier lot : coût réel"),
			"fieldtype": "Currency",
			"width": 140,
		},
		{"fieldname": "last_date", "label": _("Dernier lot : date"), "fieldtype": "Date", "width": 115},
	]


def get_rows(filters, rates):
	conditions = {"is_active": 1, "is_default": 1, "docstatus": 1, "company": filters.company}
	if filters.item:
		conditions["item"] = filters.item
	rows = []
	for bom in frappe.get_all("BOM", conditions, ["name", "item", "item_name", "uom"], order_by="item"):
		components = materials_of(bom.name, rates)
		materials = sum(line["amount"] for line in components)
		made = manufactured(bom.item)
		labour = made["labour"]
		price = selling_price(bom.item, filters.price_list)
		cost = materials + labour
		rows.append(
			{
				"id": bom.item,
				"indent": 0,
				"item": bom.item,
				"item_name": bom.item_name,
				"uom": bom.uom,
				"materials": materials,
				"labour": labour,
				"cost": cost,
				"price": price,
				"margin": price - cost if price else None,
				"margin_pct": 100 * (price - cost) / price if price else None,
				"last_cost": made["last_cost"],
				"last_date": made["last_date"],
			}
		)
		for line in components:
			rows.append(
				{
					"id": f"{bom.item}/{line['item']}",
					"parent_id": bom.item,
					"indent": 1,
					"item": line["item"],
					"item_name": line["item_name"],
					"qty": line["qty"],
					"uom": line["uom"],
					"rate": line["rate"],
					"materials": line["amount"],
				}
			)
	return rows


def materials_of(bom_name, rates, depth=0):
	"""The materials of one unit, priced: [{item, item_name, qty, uom, rate, amount}].
	A component made in-house (it has its own default recipe) is priced from
	that recipe."""
	bom = frappe.get_cached_doc("BOM", bom_name)
	lines = []
	for row in bom.items:
		qty = flt(row.stock_qty) / flt(bom.quantity or 1)
		sub_bom = frappe.db.get_value("BOM", {"item": row.item_code, "is_default": 1, "is_active": 1})
		if sub_bom and depth < 5:
			rate = sum(line["amount"] for line in materials_of(sub_bom, rates, depth + 1))
		else:
			rate = rates.get(row.item_code)
		lines.append(
			{
				"item": row.item_code,
				"item_name": row.item_name,
				"qty": qty,
				"uom": row.stock_uom,
				"rate": rate,
				"amount": qty * rate,
			}
		)
	return lines


def manufactured(item_code):
	"""Labour per unit over the last 90 days, and the real cost of the last
	batch made, from the manufacture entries (a model: all its variants)."""
	items = [item_code, *frappe.get_all("Item", {"variant_of": item_code}, pluck="name")]
	entries = frappe.db.sql(
		"""
		SELECT se.posting_date, se.total_additional_costs, sed.transfer_qty, sed.valuation_rate
		FROM `tabStock Entry` se
		JOIN `tabStock Entry Detail` sed ON sed.parent = se.name AND sed.is_finished_item = 1
		WHERE se.purpose = 'Manufacture' AND se.docstatus = 1 AND sed.item_code IN %(items)s
		ORDER BY se.posting_date DESC, se.posting_time DESC, se.creation DESC
		""",
		{"items": items},
		as_dict=True,
	)
	since = add_days(nowdate(), -LABOUR_DAYS)
	recent = [e for e in entries if str(e.posting_date) >= since]
	made = sum(flt(e.transfer_qty) for e in recent)
	return {
		"labour": sum(flt(e.total_additional_costs) for e in recent) / made if made else 0,
		"last_cost": entries[0].valuation_rate if entries else None,
		"last_date": entries[0].posting_date if entries else None,
	}


def selling_price(item_code, price_list):
	"""The item's price in the list; a model without one takes its variants' price."""
	price = frappe.db.get_value(
		"Item Price", {"item_code": item_code, "price_list": price_list}, "price_list_rate"
	)
	if price:
		return flt(price)
	variants = frappe.get_all("Item", {"variant_of": item_code}, pluck="name")
	if variants:
		return flt(
			frappe.db.get_value(
				"Item Price", {"item_code": ["in", variants], "price_list": price_list}, "price_list_rate"
			)
		)
	return 0


def get_chart(products):
	priced = [row for row in products if row["margin_pct"] is not None]
	return {
		"data": {
			"labels": [row["item_name"] for row in priced],
			"datasets": [{"name": _("Marge %"), "values": [round(row["margin_pct"], 1) for row in priced]}],
		},
		"type": "bar",
	}


def get_summary(products):
	priced = [row for row in products if row["margin_pct"] is not None]
	average = sum(row["margin_pct"] for row in priced) / len(priced) if priced else 0
	return [
		{"label": _("Produits"), "value": len(products), "datatype": "Int", "indicator": "blue"},
		{
			"label": _("Marge moyenne"),
			"value": round(average, 1),
			"datatype": "Percent",
			"indicator": "green",
		},
	]
