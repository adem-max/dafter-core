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

`full=1` also removes the opening stock and its lots, and deletes the ledger
lines of everything removed (Accounts Settings "delete linked ledger
entries", on during the wipe only). The company then has no entry at all, so
the SCF set-up can switch it to inventory accounts per item and convert the
ledgers it needs into groups (setup/scf.py); `load` imports the opening
stock again from the demo workbook. That is how a demo built before
21 October 2026 moves to the SCF set-up without dropping the site.
"""

import importlib
import time
from contextlib import contextmanager

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


def run(profile="food", full=0):
	if profile not in PROFILES:
		frappe.throw(f"Profil inconnu : {profile}")
	p = importlib.import_module(f"dz_core.demo.{profile}")
	check_site_is_for_demo(p)
	with ledger_lines_deleted(full):
		for doctype, filters in ORDER:
			print(f"{doctype}...")
			remove(doctype, {"company": p.COMPANY, **filters})
		if full:
			print("Stock d'ouverture...")
			remove("Stock Reconciliation", {"company": p.COMPANY, "purpose": "Opening Stock"})
	frappe.db.delete("Repost Item Valuation", {"company": p.COMPANY})
	if not full:
		repost_opening_stock(p.COMPANY)
	# Batches made by the story (receipts and production); opening batches stay
	# unless the opening stock went too
	batch_filters = {} if full else {"name": ["not like", "OUV-%"]}
	for name in frappe.get_all("Batch", filters=batch_filters, pluck="name"):
		if not frappe.db.exists("Serial and Batch Entry", {"batch_no": name}):
			frappe.delete_doc("Batch", name, force=True, ignore_permissions=True)
	frappe.db.sql(
		"delete from `tabDefaultValue` where defkey like %s and defkey not like %s and defkey not like %s",
		(f"{PREFIX}::{profile}::%", f"{PREFIX}::{profile}::step::%", f"{PREFIX}::{profile}::start"),
	)
	if full:
		# the masters import runs again: it re-creates the opening stock (items etc. exist)
		frappe.db.delete("DefaultValue", {"defkey": f"{PREFIX}::{profile}::step::masters"})
		from dz_core.demo.loader import demo_accounting

		for line in demo_accounting(p.COMPANY, p.SECTOR):
			print(f"   {line}")
	frappe.clear_cache()
	frappe.db.commit()
	print(
		f"Histoire effacée. Relancez : bench --site <site> execute dz_core.demo.loader.load --kwargs \"{{'profile': '{profile}'}}\""
	)


@contextmanager
def ledger_lines_deleted(on):
	"""Accounts Settings "delete linked ledger entries" on for the block, so the
	ledger lines of the removed documents go with them."""
	if not on:
		yield
		return
	before = frappe.db.get_single_value("Accounts Settings", "delete_linked_ledger_entries")
	frappe.db.set_single_value("Accounts Settings", "delete_linked_ledger_entries", 1)
	try:
		yield
	finally:
		frappe.db.set_single_value("Accounts Settings", "delete_linked_ledger_entries", before)


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
	for count, name in enumerate(names, 1):
		frappe.delete_doc(doctype, name, force=True, ignore_permissions=True)
		if count % BATCH == 0:
			commit_when_workers_keep_up()
	commit_when_workers_keep_up()


# Frappe queues one clean-up job per deleted document when the deletion is
# committed (delete_dynamic_links), and refuses new jobs past 1,000
BATCH = 100
QUEUE_ROOM = 500
QUEUE_PATIENCE = 600  # seconds without progress before giving up


def commit_when_workers_keep_up():
	"""Commit once the background queue has room for this batch's clean-up
	jobs. The workers of `bench start` empty it; without them the wipe stops
	with a clear message instead of Frappe's "Too many queued background jobs"."""
	from frappe.utils.background_jobs import get_queue

	queue = get_queue("default")
	waited, last = 0, queue.count
	while queue.count > QUEUE_ROOM:
		time.sleep(5)
		waited = 0 if queue.count < last else waited + 5
		last = queue.count
		if waited >= QUEUE_PATIENCE:
			frappe.throw(
				f"La file des tâches ne se vide pas ({queue.count} tâches) : lancez les workers (bench start)."
			)
	frappe.db.commit()
