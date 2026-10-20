"""Report "À acheter": the materials under their reorder level.

Reorder levels come from the import workbook (columns "Seuil de
réapprovisionnement" and "Quantité à commander") or the item's form. A row is
"À commander" when stock plus what is already ordered stays under the level
(ERPNext's own rule), and "Commandé" when an order on the way covers it.
ERPNext's automatic material requests stay off (DECISIONS.md).

The chart (stock against level, per material) is the low stock alert on the
Atelier home page (dashboard chart "Atelier To Buy").
"""

import frappe
from frappe import _
from frappe.utils import flt

from dz_core.reports import Rates, get_company

TO_ORDER = "À commander"
ORDERED = "Commandé"


def execute(filters=None):
	filters = frappe._dict(filters or {})
	filters.company = get_company(filters)
	rows = get_rows(filters)
	if filters.only_to_order:
		rows = [row for row in rows if row["status"] == TO_ORDER]
	return get_columns(), rows, None, get_chart(rows), get_summary(rows)


def get_columns():
	return [
		{"fieldname": "item", "label": _("Article"), "fieldtype": "Link", "options": "Item", "width": 160},
		{"fieldname": "item_name", "label": _("Désignation"), "fieldtype": "Data", "width": 200},
		{"fieldname": "status", "label": _("État"), "fieldtype": "Data", "width": 105},
		{"fieldname": "actual", "label": _("En stock"), "fieldtype": "Float", "width": 90},
		{"fieldname": "level", "label": _("Seuil"), "fieldtype": "Float", "width": 80},
		{"fieldname": "ordered", "label": _("Déjà commandé"), "fieldtype": "Float", "width": 115},
		{"fieldname": "to_order", "label": _("À commander"), "fieldtype": "Float", "width": 105},
		{"fieldname": "uom", "label": _("Unité"), "fieldtype": "Data", "width": 70},
		{
			"fieldname": "supplier",
			"label": _("Fournisseur habituel"),
			"fieldtype": "Link",
			"options": "Supplier",
			"width": 190,
		},
		{"fieldname": "rate", "label": _("Dernier prix"), "fieldtype": "Currency", "width": 100},
		{
			"fieldname": "warehouse",
			"label": _("Entrepôt"),
			"fieldtype": "Link",
			"options": "Warehouse",
			"width": 160,
		},
	]


def get_rows(filters):
	lines = frappe.db.sql(
		"""
		SELECT r.parent AS item, i.item_name, i.stock_uom AS uom, r.warehouse,
			r.warehouse_reorder_level AS level, r.warehouse_reorder_qty AS reorder_qty,
			IFNULL(b.actual_qty, 0) AS actual, IFNULL(b.ordered_qty, 0) AS ordered
		FROM `tabItem Reorder` r
		JOIN tabItem i ON i.name = r.parent AND i.disabled = 0
		JOIN tabWarehouse w ON w.name = r.warehouse AND w.company = %(company)s
		LEFT JOIN tabBin b ON b.item_code = r.parent AND b.warehouse = r.warehouse
		WHERE r.parenttype = 'Item' AND r.warehouse_reorder_level > 0
			AND IFNULL(b.actual_qty, 0) < r.warehouse_reorder_level
		ORDER BY i.item_name
		""",
		{"company": filters.company},
		as_dict=True,
	)
	rates = Rates()
	rows = []
	for line in lines:
		short = flt(line.actual) + flt(line.ordered) < flt(line.level)
		to_order = max(flt(line.reorder_qty), flt(line.level) - flt(line.actual) - flt(line.ordered))
		rows.append(
			{
				**line,
				"status": TO_ORDER if short else ORDERED,
				"to_order": to_order if short else 0,
				"supplier": usual_supplier(line.item),
				"rate": rates.get(line.item),
			}
		)
	return rows


def usual_supplier(item_code):
	"""The supplier of the item's last purchase order, else its default supplier."""
	last = frappe.db.sql(
		"""
		SELECT po.supplier FROM `tabPurchase Order Item` poi
		JOIN `tabPurchase Order` po ON po.name = poi.parent
		WHERE poi.item_code = %s AND po.docstatus = 1
		ORDER BY po.transaction_date DESC, po.creation DESC LIMIT 1
		""",
		item_code,
	)
	return (
		last[0][0] if last else frappe.db.get_value("Item Default", {"parent": item_code}, "default_supplier")
	)


def count_under_level():
	"""For the home page: how many materials are under their reorder level."""
	return len(get_rows(frappe._dict(company=get_company({}))))


def get_chart(rows):
	"""Bars: what is in stock against the level, for each material under it."""
	return {
		"data": {
			"labels": [row["item_name"] for row in rows],
			"datasets": [
				{"name": _("En stock"), "values": [flt(row["actual"]) for row in rows]},
				{"name": _("Seuil"), "values": [flt(row["level"]) for row in rows]},
			],
		},
		"type": "bar",
		"colors": ["#E24C4C", "#C0C6CC"],
	}


def get_summary(rows):
	return [
		{"label": _("Sous le seuil"), "value": len(rows), "datatype": "Int", "indicator": "orange"},
		{
			"label": _("À commander"),
			"value": sum(1 for row in rows if row["status"] == TO_ORDER),
			"datatype": "Int",
			"indicator": "red",
		},
	]
