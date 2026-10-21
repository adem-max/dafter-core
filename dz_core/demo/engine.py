"""Post the planned events (planner.py) as real ERPNext documents.

Each event is done once: its key and the document it made are kept in a site
default (dz_demo::<profile>::<key>), so loading again skips what exists and
only adds the days since. Events after today are never posted: the story
stops today, with orders still to deliver and work orders in progress.

Documents are backdated (posting_date + set_posting_time) and posted strictly
in date order, the way ERPNext expects stock to move. On a past day they are
posted at noon, not at the clock time of the load: the opening stock (posted
at the start of its day, or at the time an older demo was built) comes first
whatever the hour of a reload.
"""

import frappe
from frappe.utils import add_days, flt, getdate, nowdate

from dz_core.demo.planner import FINISHED_WAREHOUSE, RAW_WAREHOUSE
from dz_core.dz_core.doctype.dz_core_settings.dz_core_settings import get_settings

PREFIX = "dz_demo"
STORY_TIME = "12:00:00"  # the time of the story's documents on past days (dated)

# dz_core's payment modes (Sales Invoice field dz_payment_mode) -> ERPNext Mode of Payment
MODES = {
	"Espèces": ("Cash", "Cash"),
	"Chèque": ("Cheque", "Bank"),
	"Virement": ("Wire Transfer", "Bank"),
	"CCP / BaridiMob": ("CCP / BaridiMob", "Bank"),
}


class Engine:
	def __init__(self, profile_name, profile):
		self.name = profile_name
		self.p = profile
		self.settings = get_settings()
		self.company = self.settings.company
		self.warehouses = {
			RAW_WAREHOUSE: self.settings.raw_materials_warehouse,
			"Travaux en cours": self.settings.wip_warehouse,
			FINISHED_WAREHOUSE: self.settings.finished_goods_warehouse,
		}
		self.today = getdate(nowdate())
		self.ensure_payment_setup()

	# ------------------------------------------------------------ done log

	def done_key(self, key):
		return f"{PREFIX}::{self.name}::{key}"

	def done(self, key):
		return frappe.db.get_default(self.done_key(key))

	def mark(self, key, docname):
		frappe.db.set_default(self.done_key(key), docname)

	def ref(self, event):
		name = self.done(event["ref"])
		if not name:
			frappe.throw(f"Démo : {event['key']} attend {event['ref']}, qui n'a pas été créé")
		return name

	# ------------------------------------------------------------ run

	def run(self, events):
		posted = 0
		for event in events:
			if getdate(event["date"]) > self.today or self.done(event["key"]):
				continue
			handler = getattr(self, "do_" + event["type"])
			docname = handler(event)
			self.mark(event["key"], docname or "-")
			posted += 1
			if posted % 50 == 0:
				frappe.db.commit()
				print(f"   {posted} événements ({event['date']})")
		frappe.db.commit()
		return posted

	# ------------------------------------------------------------ shared helpers

	def dated(self, doc, date, field="posting_date"):
		doc.set(field, getdate(date))
		if doc.meta.has_field("set_posting_time"):
			doc.set_posting_time = 1
			# Today keeps the clock time: ERPNext refuses stock posted in the future
			if getdate(date) < self.today:
				doc.posting_time = STORY_TIME
		return doc

	def save(self, doc):
		doc.flags.ignore_permissions = True
		doc.insert()
		doc.submit()
		return doc.name

	def default_template(self, doctype):
		return frappe.db.get_value(doctype, {"company": self.company, "is_default": 1, "disabled": 0})

	def apply_taxes(self, doc, template_doctype):
		"""Server-side documents don't fetch the default tax template: do it here.
		IFU sites have no default (no TVA), réel sites get 19 %."""
		from erpnext.controllers.accounts_controller import get_taxes_and_charges

		template = self.default_template(template_doctype)
		if template:
			doc.taxes_and_charges = template
			doc.set("taxes", get_taxes_and_charges(template_doctype, template))

	def ensure_batch(self, item_code, batch_id, date):
		if not frappe.db.exists("Batch", batch_id):
			frappe.get_doc(
				{
					"doctype": "Batch",
					"batch_id": batch_id,
					"item": item_code,
					"manufacturing_date": getdate(date),
				}
			).insert(ignore_permissions=True)
		return batch_id

	def has_batch(self, item_code):
		return frappe.get_cached_value("Item", item_code, "has_batch_no")

	def split_batches(self, doc, warehouse_field):
		"""Outgoing lines of batch-tracked items, split across batches, oldest first
		(expired ones skipped). ERPNext 16 fills one batch per line by itself, which
		fails as soon as a line needs more than one batch holds."""
		rows = []
		for row in doc.items:
			values = {
				k: v
				for k, v in row.as_dict().items()
				if k not in ("name", "idx", "parent", "serial_and_batch_bundle")
			}
			warehouse = row.get(warehouse_field)
			if not warehouse or row.get("is_finished_item") or not self.has_batch(row.item_code):
				rows.append(values)
				continue
			factor = flt(row.get("conversion_factor")) or 1
			need = flt(row.qty)
			for batch_no, available in self.available_batches(row.item_code, warehouse, doc):
				if need <= 1e-9:
					break
				take = min(available / factor, need)
				part = {**values, "qty": take, "batch_no": batch_no, "use_serial_batch_fields": 1}
				for field in ("transfer_qty", "stock_qty"):
					if field in values:
						part[field] = take * factor
				rows.append(part)
				need -= take
			if need > 1e-6:
				frappe.throw(
					f"Démo : {row.item_code} manque de {need} dans {warehouse} le {doc.posting_date}"
				)
		doc.set("items", [])
		for values in rows:
			doc.append("items", values)

	def available_batches(self, item_code, warehouse, doc):
		"""[(batch, qty)] in stock at the document's date, oldest batch first."""
		from erpnext.stock.doctype.batch.batch import get_batch_qty

		date = getdate(doc.posting_date)
		found = []
		for entry in (
			get_batch_qty(
				warehouse=warehouse, item_code=item_code, posting_date=date, posting_time=doc.posting_time
			)
			or []
		):
			if flt(entry.get("qty")) <= 0:
				continue
			made, expiry = frappe.db.get_value(
				"Batch", entry["batch_no"], ["manufacturing_date", "expiry_date"]
			)
			if expiry and getdate(expiry) < date:
				continue
			found.append((made or date, entry["batch_no"], flt(entry["qty"])))
		return [(batch_no, qty) for _made, batch_no, qty in sorted(found)]

	# ------------------------------------------------------------ purchases

	def do_po(self, event):
		doc = frappe.new_doc("Purchase Order")
		self.dated(doc, event["date"], "transaction_date")
		doc.update(
			{
				"company": self.company,
				"supplier": event["supplier"],
				"schedule_date": getdate(event["arrival"]),
				"set_warehouse": self.warehouses[RAW_WAREHOUSE],
			}
		)
		for code, qty, rate in event["lines"]:
			doc.append(
				"items",
				{"item_code": code, "qty": qty, "rate": rate, "schedule_date": getdate(event["arrival"])},
			)
		self.apply_taxes(doc, "Purchase Taxes and Charges Template")
		return self.save(doc)

	def do_receive(self, event):
		from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt

		doc = make_purchase_receipt(self.ref(event))
		self.dated(doc, event["date"])
		for row in doc.items:
			if self.has_batch(row.item_code):
				row.use_serial_batch_fields = 1
				row.batch_no = self.ensure_batch(
					row.item_code, f"{row.item_code}-{getdate(event['date']):%y%m%d}", event["date"]
				)
		return self.save(doc)

	def do_pinv(self, event):
		from erpnext.stock.doctype.purchase_receipt.purchase_receipt import make_purchase_invoice

		doc = make_purchase_invoice(self.ref(event))
		self.dated(doc, event["date"])
		doc.bill_no = f"F-{event['key'].split(':')[1]}"
		doc.bill_date = getdate(event["date"])
		doc.due_date = add_days(event["date"], 30)
		return self.save(doc)

	def do_ppay(self, event):
		return self.pay("Purchase Invoice", self.ref(event), event["date"], "Virement", None, event["key"])

	# ------------------------------------------------------------ production

	def bom_of(self, item_code):
		item = frappe.get_cached_doc("Item", item_code)
		for code in (item_code, item.variant_of):
			if code:
				bom = frappe.db.get_value(
					"BOM", {"item": code, "is_default": 1, "docstatus": 1, "is_active": 1}
				)
				if bom:
					return bom
		frappe.throw(f"Démo : pas de nomenclature pour {item_code}")

	def do_wo(self, event):
		"""Create the work order and move its materials to Travaux en cours."""
		from erpnext.manufacturing.doctype.work_order.work_order import make_stock_entry

		wo = frappe.new_doc("Work Order")
		wo.update(
			{
				"company": self.company,
				"production_item": event["item"],
				"bom_no": self.bom_of(event["item"]),
				"qty": event["qty"],
				"planned_start_date": f"{event['date']} 08:00:00",
				"expected_delivery_date": getdate(event["finish"]),
				"source_warehouse": self.warehouses[RAW_WAREHOUSE],
				"wip_warehouse": self.warehouses["Travaux en cours"],
				"fg_warehouse": self.warehouses[FINISHED_WAREHOUSE],
			}
		)
		self.save(wo)
		entry = frappe.get_doc(make_stock_entry(wo.name, "Material Transfer for Manufacture", event["qty"]))
		self.dated(entry, event["date"])
		self.split_batches(entry, "s_warehouse")
		self.save(entry)
		return wo.name

	def do_wo_finish(self, event):
		from erpnext.manufacturing.doctype.work_order.work_order import make_stock_entry

		wo = self.ref(event)
		entry = frappe.get_doc(make_stock_entry(wo, "Manufacture", event["qty"]))
		self.dated(entry, event["date"])
		self.split_batches(entry, "s_warehouse")
		product = frappe.db.get_value("Work Order", wo, "production_item")
		for row in entry.items:
			if row.is_finished_item and self.has_batch(row.item_code):
				row.use_serial_batch_fields = 1
				row.batch_no = self.ensure_batch(
					row.item_code, f"L{getdate(event['date']):%y%m%d}-{row.item_code}", event["date"]
				)
		labour = getattr(self.p, "labour_rate", None)
		if labour and labour(product):
			entry.append(
				"additional_costs",
				{
					"expense_account": self.labour_account(),
					"description": "Main-d'œuvre",
					"amount": flt(labour(product)) * flt(event["qty"]),
				},
			)
		return self.save(entry)

	def labour_account(self):
		"""An expense account for direct labour, created under the expenses root if missing."""
		name = frappe.db.get_value(
			"Account", {"company": self.company, "account_name": "Main-d'œuvre de production"}
		)
		if name:
			return name
		root = frappe.db.get_value(
			"Account",
			{
				"company": self.company,
				"root_type": "Expense",
				"is_group": 1,
				"parent_account": ["is", "not set"],
			},
		)
		return (
			frappe.get_doc(
				{
					"doctype": "Account",
					"account_name": "Main-d'œuvre de production",
					"company": self.company,
					"parent_account": root,
					"account_type": "Expense Account",
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

	# ------------------------------------------------------------ sales

	def do_so(self, event):
		customer = event["customer"]
		price_list = self.p.price_list_of(customer)
		doc = frappe.new_doc("Sales Order")
		self.dated(doc, event["date"], "transaction_date")
		doc.update(
			{
				"company": self.company,
				"customer": customer,
				"delivery_date": getdate(event["delivery"]),
				"selling_price_list": price_list,
				"set_warehouse": self.warehouses[FINISHED_WAREHOUSE],
				"po_no": f"BC-{event['key'].split(':')[1]}",
			}
		)
		for code, qty in event["lines"]:
			rate = frappe.db.get_value(
				"Item Price", {"item_code": code, "price_list": price_list}, "price_list_rate"
			)
			doc.append(
				"items",
				{
					"item_code": code,
					"qty": qty,
					"rate": rate,
					"price_list_rate": rate,
					"delivery_date": getdate(event["delivery"]),
				},
			)
		self.apply_taxes(doc, "Sales Taxes and Charges Template")
		return self.save(doc)

	def do_dn(self, event):
		from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note

		doc = make_delivery_note(self.ref(event))
		self.dated(doc, event["date"])
		self.split_batches(doc, "warehouse")
		return self.save(doc)

	def do_si(self, event):
		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice

		doc = make_sales_invoice(self.ref(event))
		self.dated(doc, event["date"])
		doc.due_date = add_days(event["date"], max(event.get("due_days") or 0, 0))
		doc.dz_payment_mode = event.get("mode") or "Espèces"
		return self.save(doc)

	def do_spay(self, event):
		name = self.ref(event)
		mode = frappe.db.get_value("Sales Invoice", name, "dz_payment_mode") or "Espèces"
		return self.pay("Sales Invoice", name, event["date"], mode, event.get("part"), event["key"])

	def do_cancel(self, event):
		doc = frappe.get_doc("Sales Invoice", self.ref(event))
		doc.flags.ignore_permissions = True
		doc.cancel()
		return doc.name

	def do_reinvoice(self, event):
		"""The corrected invoice, from the same delivery note."""
		return self.do_si({**event, "mode": None, "due_days": 15})

	def do_return(self, event):
		"""A credit note (avoir) for broken goods: part of each line, no stock movement."""
		from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_sales_return

		doc = make_sales_return(self.ref(event))
		self.dated(doc, event["date"])
		doc.update_stock = 0
		for row in doc.items:
			row.qty = -max(1, round(abs(row.qty) * event.get("part", 0.1)))
		doc.remarks = "Avoir : marchandise abîmée à la livraison"
		return self.save(doc)

	# ------------------------------------------------------------ payments

	def ensure_payment_setup(self):
		for _label, (mode, kind) in MODES.items():
			if not frappe.db.exists("Mode of Payment", mode):
				frappe.get_doc({"doctype": "Mode of Payment", "mode_of_payment": mode, "type": kind}).insert(
					ignore_permissions=True
				)
		self.cash_account = frappe.get_cached_value("Company", self.company, "default_cash_account")
		self.bank_account = frappe.get_cached_value("Company", self.company, "default_bank_account")
		if not self.bank_account:
			self.bank_account = frappe.db.get_value(
				"Account", {"company": self.company, "account_type": "Bank", "is_group": 0}
			)
			if self.bank_account:
				frappe.db.set_value("Company", self.company, "default_bank_account", self.bank_account)

	def pay(self, doctype, name, date, mode_label, part, key):
		from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

		mode, kind = MODES.get(mode_label, MODES["Virement"])
		account = self.cash_account if kind == "Cash" else self.bank_account
		outstanding = flt(frappe.db.get_value(doctype, name, "outstanding_amount"))
		if outstanding <= 0:
			return None
		amount = flt(outstanding * part, 2) if part else outstanding
		pe = get_payment_entry(doctype, name, party_amount=amount, bank_account=account)
		self.dated(pe, date)
		pe.mode_of_payment = mode
		pe.reference_no = f"{mode_label} {key}"
		pe.reference_date = getdate(date)
		return self.save(pe)

	# ------------------------------------------------------------ stock count

	def do_count(self, event):
		from erpnext.stock.utils import get_stock_balance

		doc = frappe.new_doc("Stock Reconciliation")
		self.dated(doc, event["date"])
		doc.company = self.company
		doc.purpose = "Stock Reconciliation"
		for code, warehouse_label, delta in event["lines"]:
			warehouse = self.warehouses[warehouse_label]
			current = flt(get_stock_balance(code, warehouse, event["date"]))
			doc.append("items", {"item_code": code, "warehouse": warehouse, "qty": max(current + delta, 0)})
		return self.save(doc)
