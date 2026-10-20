"""Report "Ventes par mois": what sells, who buys, and is it growing.

One row per product (or customer, or customer group), one column per month
with the amount HT (net of discounts, before VAT) of the submitted Sales
Invoices. Credit notes carry negative amounts, so they come off by
themselves; cancelled invoices are left out. "Évolution" compares the last
full month with the one before it (the current month is not over yet).

Clothing: variants are added up under their model (Item.variant_of), unless
"Voir les variantes" is ticked.
"""

import frappe
from frappe import _
from frappe.utils import add_months, flt, get_first_day, get_last_day, getdate, today

from dz_core.reports import get_company

PRODUCT = "Produit"
CUSTOMER = "Client"
CUSTOMER_GROUP = "Groupe de clients"


def month_name(month):
	"""Short French name of a month (1-12), translated when the page is read."""
	return (
		_("Janv."),
		_("Févr."),
		_("Mars"),
		_("Avr."),
		_("Mai"),
		_("Juin"),
		_("Juil."),
		_("Août"),
		_("Sept."),
		_("Oct."),
		_("Nov."),
		_("Déc."),
	)[month - 1]


def execute(filters=None):
	filters = frappe._dict(filters or {})
	filters.company = get_company(filters)
	filters.by = filters.by or PRODUCT
	filters.from_date = get_first_day(filters.from_month or add_months(today(), -3))
	filters.to_date = get_last_day(filters.to_month or today())
	months = get_months(filters.from_date, filters.to_date)
	rows = get_rows(filters, months)
	return get_columns(filters, months), rows, None, get_chart(rows, months), get_summary(rows, months)


def get_months(from_date, to_date):
	"""[(column name, label), ...] for every month from one date to the other."""
	months = []
	month = getdate(from_date)
	while month <= getdate(to_date):
		months.append((f"m_{month.year}_{month.month:02d}", f"{month_name(month.month)} {month.year}"))
		month = add_months(month, 1)
	return months


def get_columns(filters, months):
	doctype = {PRODUCT: "Item", CUSTOMER: "Customer", CUSTOMER_GROUP: "Customer Group"}[filters.by]
	columns = [
		{"fieldname": "name", "label": _(filters.by), "fieldtype": "Link", "options": doctype, "width": 170}
	]
	if filters.by != CUSTOMER_GROUP:
		columns.append({"fieldname": "title", "label": _("Nom"), "fieldtype": "Data", "width": 190})
	for fieldname, label in months:
		columns.append({"fieldname": fieldname, "label": label, "fieldtype": "Currency", "width": 120})
	columns += [
		{"fieldname": "total", "label": _("Total HT"), "fieldtype": "Currency", "width": 140},
		{"fieldname": "evolution", "label": evolution_label(months), "fieldtype": "Percent", "width": 130},
	]
	return columns


def evolution_label(months):
	pair = compared(months)
	return _("Évolution {0}").format(pair[1][1]) if pair else _("Évolution")


def get_rows(filters, months):
	if filters.by == CUSTOMER:
		key = "si.customer"
	elif filters.by == CUSTOMER_GROUP:
		key = "si.customer_group"
	elif filters.show_variants:
		key = "sii.item_code"
	else:
		key = "COALESCE(NULLIF(i.variant_of, ''), sii.item_code)"

	# Plain SQL: the amount HT per month and row, in the company's currency
	lines = frappe.db.sql(
		f"""
		SELECT DATE_FORMAT(si.posting_date, 'm_%%Y_%%m') AS month, {key} AS name,
			SUM(sii.base_net_amount) AS amount
		FROM `tabSales Invoice Item` sii
		JOIN `tabSales Invoice` si ON si.name = sii.parent
		LEFT JOIN `tabItem` i ON i.name = sii.item_code
		WHERE si.docstatus = 1
			AND si.company = %(company)s
			AND si.posting_date BETWEEN %(from_date)s AND %(to_date)s
		GROUP BY month, name
		""",
		{"company": filters.company, "from_date": filters.from_date, "to_date": filters.to_date},
		as_dict=True,
	)

	rows = {}  # name -> row
	for line in lines:
		row = rows.setdefault(line.name, {"name": line.name, "total": 0})
		row[line.month] = flt(line.amount)
		row["total"] += flt(line.amount)

	titles = get_titles(filters.by, list(rows))
	for row in rows.values():
		row["title"] = titles.get(row["name"])
		row["evolution"] = evolution(row, months)
	rows = sorted(rows.values(), key=lambda row: row["total"], reverse=True)

	if rows:
		total = {"name": _("Total"), "total": sum(row["total"] for row in rows), "is_total_row": 1}
		for fieldname, _label in months:
			total[fieldname] = sum(row.get(fieldname, 0) for row in rows)
		total["evolution"] = evolution(total, months)
		rows.append(total)
	return rows


def get_titles(by, names):
	"""The readable name next to the code: item name, customer name."""
	if by == PRODUCT:
		doctype, field = "Item", "item_name"
	elif by == CUSTOMER:
		doctype, field = "Customer", "customer_name"
	else:
		return {}
	return dict(
		frappe.get_all(doctype, filters={"name": ("in", names)}, fields=["name", field], as_list=True)
	)


def compared(months):
	"""The two months "Évolution" compares: the last two full ones. The current
	month is not over yet; set against a whole month it would always look down."""
	full = [m for m in months if m[0] < f"m_{getdate(today()).year}_{getdate(today()).month:02d}"]
	return full[-2:] if len(full) >= 2 else None


def evolution(row, months):
	"""Last full month against the one before, in %; empty when there is nothing to compare."""
	pair = compared(months)
	if not pair:
		return None
	before, last = flt(row.get(pair[0][0])), flt(row.get(pair[1][0]))
	return round(100 * (last - before) / abs(before), 1) if before else None


def get_chart(rows, months):
	"""Stacked bars: one bar per month, one colour for each of the 5 best rows."""
	top = [row for row in rows if not row.get("is_total_row")][:5]
	return {
		"data": {
			"labels": [label for _fieldname, label in months],
			"datasets": [
				{
					"name": row.get("title") or row["name"],
					"values": [flt(row.get(fieldname), 2) for fieldname, _label in months],
				}
				for row in top
			],
		},
		"type": "bar",
		"barOptions": {"stacked": 1},
		"fieldtype": "Currency",
	}


def get_summary(rows, months):
	total = next((row for row in rows if row.get("is_total_row")), {})
	last = months[-1][1] if months else ""
	return [
		{
			"label": _("Ventes HT"),
			"value": total.get("total", 0),
			"datatype": "Currency",
			"indicator": "blue",
		},
		{
			"label": _("Ventes HT {0}").format(last),
			"value": total.get(months[-1][0], 0) if months else 0,
			"datatype": "Currency",
			"indicator": "green",
		},
		{
			"label": evolution_label(months),
			"value": total.get("evolution") or 0,
			"datatype": "Percent",
			"indicator": "green" if flt(total.get("evolution")) >= 0 else "red",
		},
	]
