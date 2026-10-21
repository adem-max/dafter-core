"""Wipe a demo's story so the loader can replay it from the first day.

    bench --site food-demo.localhost execute dz_core.demo.wipe.run --kwargs "{'profile': 'food'}"
    bench --site food-demo.localhost execute dz_core.demo.loader.load --kwargs "{'profile': 'food'}"

Cancels and deletes every transaction of the story (payments, invoices,
deliveries, orders, production, purchases, month-end counts), newest first,
and forgets which events were done. Kept: the company, the imported masters
(suppliers, customers, items, recipes), the opening stock, prices and users.
The opening stock is posted again to the warehouses' current accounts (they
changed on 21 October 2026, setup/accounts.py).
The story keeps its first day; to start it from a new day, drop the site.

It takes several minutes (hundreds of documents). For a total reset, dropping
and re-creating the site is faster (docs/DEMO.md).
"""

import importlib

import frappe

from dz_core.demo.engine import PREFIX
from dz_core.demo.loader import PROFILES, check_site_is_for_demo

# Newest kind first: what depends on a document goes before it
ORDER = [
	("Payment Entry", {}),
	("Sales Invoice", {"is_return": 1}),
	("Sales Invoice", {}),
	("Delivery Note", {}),
	("Sales Order", {}),
	("Stock Entry", {}),
	("Work Order", {}),
	("Purchase Invoice", {}),
	("Purchase Receipt", {}),
	("Purchase Order", {}),
	("Stock Reconciliation", {"purpose": "Stock Reconciliation"}),
]


def run(profile="food"):
	if profile not in PROFILES:
		frappe.throw(f"Profil inconnu : {profile}")
	p = importlib.import_module(f"dz_core.demo.{profile}")
	check_site_is_for_demo(p)
	for doctype, filters in ORDER:
		print(f"{doctype}...")
		remove(doctype, {"company": p.COMPANY, **filters})
	frappe.db.delete("Repost Item Valuation", {"company": p.COMPANY})
	repost_opening_stock(p.COMPANY)
	# Batches made by the story (receipts and production); opening batches stay
	for name in frappe.get_all("Batch", filters={"name": ["not like", "OUV-%"]}, pluck="name"):
		if not frappe.db.exists("Serial and Batch Entry", {"batch_no": name}):
			frappe.delete_doc("Batch", name, force=True, ignore_permissions=True)
	frappe.db.sql(
		"delete from `tabDefaultValue` where defkey like %s and defkey not like %s and defkey not like %s",
		(f"{PREFIX}::{profile}::%", f"{PREFIX}::{profile}::step::%", f"{PREFIX}::{profile}::start"),
	)
	frappe.clear_cache()
	frappe.db.commit()
	print(
		f"Histoire effacée. Relancez : bench --site <site> execute dz_core.demo.loader.load --kwargs \"{{'profile': '{profile}'}}\""
	)


def repost_opening_stock(company):
	"""Post the kept opening stock again, with today's warehouse accounts."""
	from erpnext.accounts.utils import repost_gle_for_stock_vouchers

	rows = frappe.get_all(
		"Stock Reconciliation",
		filters={"company": company, "docstatus": 1, "purpose": "Opening Stock"},
		fields=["name", "posting_date"],
		order_by="posting_date",
	)
	if rows:
		vouchers = [("Stock Reconciliation", row.name) for row in rows]
		repost_gle_for_stock_vouchers(vouchers, rows[0].posting_date, company)


def remove(doctype, filters):
	"""Cancel (if submitted) then delete, newest first, so stock is given back
	in the reverse order it moved."""
	names = frappe.get_all(doctype, filters=filters, pluck="name", order_by="creation desc")
	for name in names:
		doc = frappe.get_doc(doctype, name)
		if doc.docstatus == 1:
			doc.flags.ignore_links = True
			doc.flags.ignore_permissions = True
			doc.cancel()
	for name in names:
		frappe.delete_doc(doctype, name, force=True, ignore_permissions=True)
	frappe.db.commit()
