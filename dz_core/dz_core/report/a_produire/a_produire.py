"""Report "À produire": what to make for the orders already taken.

Per product (clothing: per size and colour): what open sales orders still
wait for, what is in the finished goods warehouse, what work orders are
already making. À produire = ordered - in stock - in production, when above 0.
Every ordered product is listed, so a covered order shows as covered;
"Seulement ce qui manque" keeps the shortfalls.
The work order itself is made from the sales order, as in ERPNext.
"""

import frappe
from frappe import _
from frappe.utils import flt

from dz_core.reports import get_company


def execute(filters=None):
	filters = frappe._dict(filters or {})
	filters.company = get_company(filters)
	rows = get_rows(filters)
	if filters.only_missing:
		rows = [row for row in rows if row["to_produce"] > 0]
	return get_columns(), rows, None, None, get_summary(rows)


def get_columns():
	return [
		{"fieldname": "item", "label": _("Article"), "fieldtype": "Link", "options": "Item", "width": 180},
		{"fieldname": "item_name", "label": _("Désignation"), "fieldtype": "Data", "width": 230},
		{"fieldname": "ordered", "label": _("Commandé, à livrer"), "fieldtype": "Float", "width": 130},
		{"fieldname": "in_stock", "label": _("En stock"), "fieldtype": "Float", "width": 90},
		{"fieldname": "in_production", "label": _("En fabrication"), "fieldtype": "Float", "width": 115},
		{"fieldname": "to_produce", "label": _("À produire"), "fieldtype": "Float", "width": 100},
		{"fieldname": "uom", "label": _("Unité"), "fieldtype": "Data", "width": 70},
		{"fieldname": "first_delivery", "label": _("Première livraison"), "fieldtype": "Date", "width": 125},
		{"fieldname": "orders", "label": _("Commandes"), "fieldtype": "Int", "width": 95},
	]


def get_rows(filters):
	ordered = frappe.db.sql(
		"""
		SELECT soi.item_code AS item, soi.item_name, soi.stock_uom AS uom,
			SUM((soi.qty - soi.delivered_qty) * soi.conversion_factor) AS ordered,
			MIN(IFNULL(soi.delivery_date, so.delivery_date)) AS first_delivery,
			COUNT(DISTINCT so.name) AS orders
		FROM `tabSales Order Item` soi
		JOIN `tabSales Order` so ON so.name = soi.parent
		WHERE so.docstatus = 1 AND so.company = %(company)s
			AND so.status NOT IN ('Closed', 'Completed', 'On Hold')
			AND soi.qty > soi.delivered_qty
		GROUP BY soi.item_code, soi.item_name, soi.stock_uom
		""",
		{"company": filters.company},
		as_dict=True,
	)
	if not ordered:
		return []
	items = [line.item for line in ordered]
	stock = dict(
		frappe.db.sql(
			"""
			SELECT b.item_code, SUM(b.actual_qty) FROM tabBin b
			JOIN tabWarehouse w ON w.name = b.warehouse AND w.company = %(company)s
			WHERE b.item_code IN %(items)s AND (%(warehouse)s = '' OR b.warehouse = %(warehouse)s)
			GROUP BY b.item_code
			""",
			{"company": filters.company, "items": items, "warehouse": finished_goods_warehouse()},
		)
	)
	in_production = dict(
		frappe.db.sql(
			"""
			SELECT production_item, SUM(qty - produced_qty) FROM `tabWork Order`
			WHERE docstatus = 1 AND company = %(company)s AND production_item IN %(items)s
				AND status IN ('Not Started', 'In Process')
			GROUP BY production_item
			""",
			{"company": filters.company, "items": items},
		)
	)
	rows = []
	for line in ordered:
		line.in_stock = max(flt(stock.get(line.item)), 0)
		line.in_production = flt(in_production.get(line.item))
		line.to_produce = max(flt(line.ordered) - line.in_stock - line.in_production, 0)
		rows.append(line)
	return sorted(rows, key=lambda row: (-row.to_produce, str(row.first_delivery)))


def finished_goods_warehouse():
	"""Where finished products wait (DZ Core Settings); empty = all warehouses."""
	return frappe.db.get_single_value("DZ Core Settings", "finished_goods_warehouse") or ""


def get_summary(rows):
	return [
		{
			"label": _("Articles à produire"),
			"value": sum(1 for row in rows if row["to_produce"] > 0),
			"datatype": "Int",
			"indicator": "orange",
		},
	]
