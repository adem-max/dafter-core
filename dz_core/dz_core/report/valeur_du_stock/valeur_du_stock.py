"""Report "Valeur du stock": what the stock is worth at a date, per warehouse
and item group.

The value is the sum of the Stock Ledger's value changes up to the date, the
same source as ERPNext's Stock Balance, so the two totals match. The quantity
is the balance after the last move up to the date. One row per
warehouse, then one row per item group under it, then the total.
"""

import frappe
from frappe import _
from frappe.utils import flt, today

from dz_core.reports import get_company


def execute(filters=None):
	filters = frappe._dict(filters or {})
	filters.company = get_company(filters)
	filters.date = filters.date or today()
	rows = get_rows(filters)
	return get_columns(), rows, None, get_chart(rows), get_summary(rows)


def get_columns():
	return [
		{
			"fieldname": "warehouse",
			"label": _("Entrepôt"),
			"fieldtype": "Link",
			"options": "Warehouse",
			"width": 200,
		},
		{
			"fieldname": "item_group",
			"label": _("Groupe d'articles"),
			"fieldtype": "Link",
			"options": "Item Group",
			"width": 180,
		},
		{"fieldname": "items", "label": _("Articles"), "fieldtype": "Int", "width": 80},
		{"fieldname": "qty", "label": _("Quantité"), "fieldtype": "Float", "width": 110},
		{"fieldname": "value", "label": _("Valeur"), "fieldtype": "Currency", "width": 150},
		{"fieldname": "share", "label": _("Part"), "fieldtype": "Percent", "width": 80},
	]


def get_rows(filters):
	# One line per item and warehouse: what is left of it at the date. The
	# quantity is the balance after the last move (a stock count posts no
	# actual_qty, only the new balance); the value adds up every change.
	lines = frappe.db.sql(
		"""
		SELECT sle.warehouse, i.item_group, sle.item_code,
			sle.qty_after_transaction AS qty, sle.value
		FROM (
			SELECT item_code, warehouse, qty_after_transaction,
				SUM(stock_value_difference) OVER (PARTITION BY item_code, warehouse) AS value,
				ROW_NUMBER() OVER (
					PARTITION BY item_code, warehouse ORDER BY posting_datetime DESC, creation DESC
				) AS latest
			FROM `tabStock Ledger Entry`
			WHERE company = %(company)s
				AND posting_date <= %(date)s
				AND is_cancelled = 0
				AND docstatus < 2
		) sle
		JOIN `tabItem` i ON i.name = sle.item_code
		WHERE sle.latest = 1
		""",
		{"company": filters.company, "date": filters.date},
		as_dict=True,
	)

	groups = {}  # (warehouse, item group) -> row
	in_stock = set()  # item codes, once even if in two warehouses
	for line in lines:
		row = groups.setdefault(
			(line.warehouse, line.item_group),
			{"warehouse": line.warehouse, "item_group": line.item_group, "items": 0, "qty": 0, "value": 0},
		)
		row["qty"] += flt(line.qty)
		row["value"] += flt(line.value)
		if flt(line.qty, 6) or flt(line.value, 2):
			row["items"] += 1
			in_stock.add(line.item_code)

	warehouses = {}  # warehouse -> its row and its item groups
	for row in groups.values():
		if not row["items"]:
			continue  # everything went out: nothing to show
		row["indent"] = 1
		parent = warehouses.setdefault(
			row["warehouse"],
			{"warehouse": row["warehouse"], "items": 0, "qty": 0, "value": 0, "indent": 0, "groups": []},
		)
		for field in ("items", "qty", "value"):
			parent[field] += row[field]
		parent["groups"].append(row)

	total = sum(parent["value"] for parent in warehouses.values())
	rows = []
	for parent in sorted(warehouses.values(), key=lambda row: row["value"], reverse=True):
		children = sorted(parent.pop("groups"), key=lambda row: row["value"], reverse=True)
		for row in [parent, *children]:
			row["share"] = percent(row["value"], total)
			rows.append(row)
	if rows:
		rows.append(
			{
				"warehouse": _("Total"),
				"items": len(in_stock),
				"qty": sum(row["qty"] for row in rows if not row["indent"]),
				"value": total,
				"share": 100 if total else 0,
				"indent": 0,
				"is_total_row": 1,
			}
		)
	return rows


def get_chart(rows):
	"""Bars: one per warehouse."""
	warehouses = [row for row in rows if not row["indent"] and not row.get("is_total_row")]
	return {
		"data": {
			"labels": [row["warehouse"] for row in warehouses],
			"datasets": [{"name": _("Valeur"), "values": [flt(row["value"], 2) for row in warehouses]}],
		},
		"type": "bar",
		"fieldtype": "Currency",
	}


def get_summary(rows):
	total = next((row for row in rows if row.get("is_total_row")), {"value": 0, "items": 0})
	warehouses = [row for row in rows if not row["indent"] and not row.get("is_total_row")]
	return [
		{"label": _("Valeur du stock"), "value": total["value"], "datatype": "Currency", "indicator": "blue"},
		{"label": _("Entrepôts"), "value": len(warehouses), "datatype": "Int", "indicator": "grey"},
		{"label": _("Articles en stock"), "value": total["items"], "datatype": "Int", "indicator": "green"},
	]


def percent(part, whole):
	return round(100 * part / whole, 1) if whole else 0
