"""Helpers shared by dz_core's reports (dz_core/dz_core/report/) and the
counters of the Atelier home page."""

import frappe
from frappe.utils import flt

TO_BUY_REPORT = "A acheter"

LAST_PURCHASE = "Dernier prix d'achat"
STOCK_VALUE = "Coût moyen en stock"


def get_company(filters):
	"""The company asked for, else the one dz_core was set up for."""
	return (
		filters.get("company")
		or frappe.db.get_single_value("DZ Core Settings", "company")
		or frappe.defaults.get_user_default("Company")
	)


@frappe.whitelist()
def get_to_buy_card(filters=None):
	"""Number card "À acheter" on the Atelier home page: how many materials are
	under their reorder level. `filters` is sent by every Custom number card;
	not used here. A click on the card opens the report."""
	from dz_core.dz_core.report.a_acheter.a_acheter import count_under_level

	if not frappe.get_cached_doc("Report", TO_BUY_REPORT).is_permitted():
		raise frappe.PermissionError
	return {"value": count_under_level(), "fieldtype": "Int", "route": ["query-report", TO_BUY_REPORT]}


class Rates:
	"""What one unit of a raw material costs, cached for one report run.

	LAST_PURCHASE: the rate of the last receipt (so a dearer sugar delivery
	moves every jam's cost at once), else the item's last purchase rate, else
	what it is worth in stock. STOCK_VALUE: what it is worth in stock (the
	average of the batches still there)."""

	def __init__(self, basis=LAST_PURCHASE):
		self.basis = basis
		self.cache = {}

	def get(self, item_code):
		if item_code not in self.cache:
			rate = self.last_receipt(item_code) if self.basis == LAST_PURCHASE else 0
			self.cache[item_code] = rate or self.in_stock(item_code)
		return self.cache[item_code]

	@staticmethod
	def last_receipt(item_code):
		row = frappe.db.sql(
			"""
			SELECT pri.base_net_rate / IF(pri.conversion_factor, pri.conversion_factor, 1)
			FROM `tabPurchase Receipt Item` pri
			JOIN `tabPurchase Receipt` pr ON pr.name = pri.parent
			WHERE pri.item_code = %s AND pr.docstatus = 1 AND pr.is_return = 0
			ORDER BY pr.posting_date DESC, pr.posting_time DESC, pr.creation DESC
			LIMIT 1
			""",
			item_code,
		)
		return flt(row[0][0]) if row else flt(frappe.db.get_value("Item", item_code, "last_purchase_rate"))

	@staticmethod
	def in_stock(item_code):
		value, qty = frappe.db.sql(
			"SELECT SUM(stock_value), SUM(actual_qty) FROM tabBin WHERE item_code = %s", item_code
		)[0]
		if flt(qty) > 0:
			return flt(value) / flt(qty)
		return flt(frappe.db.get_value("Item", item_code, "valuation_rate"))
