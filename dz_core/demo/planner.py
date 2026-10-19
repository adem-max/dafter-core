"""Plan a demo's history day by day, in plain Python (no database).

The planner keeps its own stock count so that every event it emits is
possible when the engine posts it in ERPNext: nothing is delivered before it
was made, nothing is made before its ingredients arrived. It plays a small
business, one working day at a time:

1. receive the purchases due today
2. finish the work orders started yesterday
3. deliver the orders due today (or tomorrow, if stock is short)
4. take today's new orders (the profile's `orders()`), refusing what is no
   longer made and sold out
5. start work orders where finished stock would fall below its target
6. order raw materials that fall below their reorder level
7. plan invoices, payments, the odd return or cancelled invoice, and the
   end-of-month stock count

Each event is a dict {"date", "type", "key", ...}. The same profile, seed and
start date always give the same events, and a later end date only adds events
at the end: the randomness of a day depends on that day alone, so the demo can
be loaded again a few days later and "continue the story".

A profile module provides (see food.py):
    BOMS            {product: (batch_qty, [(component, qty), ...])}, as in the workbook
    PLAN_BOMS       optional, the same per item actually made (clothing: per variant)
    PRODUCTION      {product: {"target": units in stock, "max_batches": per day}}
    RAW             {code: {"supplier", "lead_days", "reorder_level", "reorder_qty"}}
    OPENING         [(code, warehouse label, qty, rate, batch, expiry)]
    PAYMENT         {customer group: (mode, days after invoice)}
    COUNTS          [(code, warehouse label, delta)] applied at each month end
    CUSTOMERS       [{"name", "group", ...}]
    orders(rng, day) -> [(customer name, [(item, qty)])]
    buying_rate(code, day), labour_rate(product) (optional)
"""

import datetime
import math
import random

RAW_WAREHOUSE = "Matières premières"
FINISHED_WAREHOUSE = "Produits finis"

# Algeria works Sunday to Thursday (Friday and Saturday are the weekend)
WORKDAYS = {6, 0, 1, 2, 3}

# Order of event types inside one day, as they would happen in a workshop
PRIORITY = {
	"po": 1,
	"receive": 2,
	"pinv": 3,
	"wo_finish": 4,
	"so": 5,
	"dn": 6,
	"si": 7,
	"cancel": 8,
	"reinvoice": 9,
	"return": 10,
	"spay": 11,
	"ppay": 12,
	"wo": 13,
	"count": 14,
}


def workdays(start, end):
	day = start
	while day <= end:
		if day.weekday() in WORKDAYS:
			yield day
		day += datetime.timedelta(days=1)


def add_workdays(day, count):
	while count > 0:
		day += datetime.timedelta(days=1)
		if day.weekday() in WORKDAYS:
			count -= 1
	return day


def day_rng(seed, day):
	"""Randomness that depends on the day only (see module docstring)."""
	return random.Random(f"{seed}-{day.isoformat()}")


class Story:
	def __init__(self, profile, start, today, seed):
		self.p = profile
		self.start, self.today, self.seed = start, today, seed
		self.events = []
		self.counter = {}
		self.stock = {}  # (code, warehouse) -> qty
		for code, warehouse, qty, *_rest in profile.OPENING:
			self.add(code, warehouse, qty)
		self.on_order = {}  # raw code -> qty ordered, not yet received
		self.arrivals = {}  # date -> [(po key, [(code, qty)])]
		self.wip = {}  # date -> [(wo key, product, qty)]
		self.backlog = []  # [{"key", "customer", "lines", "due"}]
		self.groups = {c["name"]: c["group"] for c in profile.CUSTOMERS}
		# What production uses per item made. Clothing: one recipe per model in
		# the workbook, but each size/colour variant is made on its own
		self.boms = getattr(profile, "PLAN_BOMS", profile.BOMS)

	# ------------------------------------------------------------ helpers

	def add(self, code, warehouse, qty):
		self.stock[(code, warehouse)] = self.stock.get((code, warehouse), 0) + qty

	def qty(self, code, warehouse):
		return self.stock.get((code, warehouse), 0)

	def next_key(self, kind):
		self.counter[kind] = self.counter.get(kind, 0) + 1
		return f"{kind}:{self.counter[kind]:04d}"

	def emit(self, day, kind, key, **values):
		self.events.append({"date": day.isoformat(), "type": kind, "key": key, **values})

	# ------------------------------------------------------------ the days

	def run(self):
		for day in workdays(self.start, self.today):
			rng = day_rng(self.seed, day)
			self.receive(day)
			self.finish_production(day)
			self.deliver(day)
			self.take_orders(day, rng)
			self.produce(day)
			self.purchase(day)
			if self.is_month_end(day):
				self.count(day)
		self.events.sort(key=lambda e: (e["date"], PRIORITY[e["type"]], e["key"]))
		return self.events

	def receive(self, day):
		for po_key, lines in self.arrivals.pop(day, []):
			key = po_key.replace("po:", "receive:")
			self.emit(day, "receive", key, ref=po_key)
			self.emit(day, "pinv", key.replace("receive:", "pinv:"), ref=key)
			for code, qty in lines:
				self.add(code, RAW_WAREHOUSE, qty)
				self.on_order[code] -= qty
			supplier = self.p.RAW[lines[0][0]]["supplier"]
			pay_day = add_workdays(day, self.p.SUPPLIER_TERMS.get(supplier, 20))
			if pay_day <= self.today:
				self.emit(
					pay_day, "ppay", key.replace("receive:", "ppay:"), ref=key.replace("receive:", "pinv:")
				)

	def finish_production(self, day):
		for wo_key, product, qty in self.wip.pop(day, []):
			self.emit(day, "wo_finish", wo_key.replace("wo:", "wo_finish:"), ref=wo_key, qty=qty)
			self.add(product, FINISHED_WAREHOUSE, qty)

	def deliver(self, day):
		"""First come, first served: an order due but not complete keeps what it
		needs, so smaller orders taken after it cannot starve it."""
		still_open = []
		held = {}
		for order in self.backlog:
			ready = order["due"] <= day and all(
				self.qty(code, FINISHED_WAREHOUSE) - held.get(code, 0) >= qty for code, qty in order["lines"]
			)
			if not ready:
				if order["due"] <= day:
					for code, qty in order["lines"]:
						held[code] = held.get(code, 0) + qty
				still_open.append(order)
				continue
			for code, qty in order["lines"]:
				self.add(code, FINISHED_WAREHOUSE, -qty)
			self.invoice(day, order)
		self.backlog = still_open

	def invoice(self, day, order):
		number = order["key"].split(":")[1]
		dn, si = f"dn:{number}", f"si:{number}"
		self.emit(day, "dn", dn, ref=order["key"])
		group = self.groups[order["customer"]]
		mode, days = self.p.PAYMENT[group]
		self.emit(day, "si", si, ref=dn, mode=mode, due_days=days)
		self.plan_payment(day, si, mode, days, order["customer"])

	def plan_payment(self, day, si, mode, days, customer):
		"""Most pay on time; some late, some in two parts; the profile's bad
		payers never pay their last invoices (overdue in the demo).

		Each invoice has its own randomness: the bad-payer rule depends on
		today, and must not change the orders drawn after it on the same day."""
		if customer in getattr(self.p, "BAD_PAYERS", ()) and (self.today - day).days < 35:
			return
		roll = random.Random(f"{self.seed}-{si}").random()
		if roll < 0.12:  # late
			days += 15
		if roll > 0.88:  # two payments
			first = add_workdays(day, max(days // 2, 0))
			if first <= self.today:
				self.emit(first, "spay", f"spay:{si[3:]}:1", ref=si, mode=mode, part=0.5)
			second = add_workdays(day, days + 10)
			if second <= self.today:
				self.emit(second, "spay", f"spay:{si[3:]}:2", ref=si, mode=mode, part=None)
			return
		pay_day = add_workdays(day, days) if days else day
		if pay_day <= self.today:
			self.emit(pay_day, "spay", f"spay:{si[3:]}:1", ref=si, mode=mode, part=None)

	def take_orders(self, day, rng):
		for customer, lines in self.p.orders(rng, day):
			lines = [(code, qty) for code, qty in lines if self.can_promise(code, qty, day)]
			if not lines:
				continue
			key = self.next_key("so")
			due = add_workdays(day, rng.choice([1, 2, 2, 3]))
			self.emit(day, "so", key, customer=customer, lines=lines, delivery=due.isoformat())
			self.backlog.append({"key": key, "customer": customer, "lines": lines, "due": due})

	def booked(self):
		booked = {}
		for order in self.backlog:
			for code, qty in order["lines"]:
				booked[code] = booked.get(code, 0) + qty
		return booked

	def can_promise(self, code, qty, day):
		"""A product no longer made (out of season, discontinued) is sold until
		its stock runs out; after that the seller says no, and the line is dropped."""
		rule = self.p.PRODUCTION.get(code)
		if rule and rule.get("active", lambda d: True)(day):
			return True
		return self.qty(code, FINISHED_WAREHOUSE) - self.booked().get(code, 0) >= qty

	def produce(self, day):
		booked = self.booked()
		in_progress = {}
		for jobs in self.wip.values():
			for _key, product, qty in jobs:
				in_progress[product] = in_progress.get(product, 0) + qty

		for product, rule in self.p.PRODUCTION.items():
			if not rule.get("active", lambda d: True)(day):
				continue
			batch_qty, components = self.boms[product]
			projected = (
				self.qty(product, FINISHED_WAREHOUSE) + in_progress.get(product, 0) - booked.get(product, 0)
			)
			if projected >= rule["target"]:
				continue
			batches = min(math.ceil((rule["target"] - projected) / batch_qty), rule.get("max_batches", 2))
			while batches and not self.has_materials(components, batches):
				batches -= 1
			if not batches:
				continue
			qty = batches * batch_qty
			for code, per_batch in components:
				self.add(code, RAW_WAREHOUSE, -per_batch * batches)
			key = self.next_key("wo")
			finish = add_workdays(day, 1)
			self.emit(day, "wo", key, item=product, qty=qty, finish=finish.isoformat())
			if finish <= self.today:
				self.wip.setdefault(finish, []).append((key, product, qty))
			else:
				# still in progress at the end of the story: the engine starts it, nobody finishes it
				pass

	def has_materials(self, components, batches):
		return all(self.qty(code, RAW_WAREHOUSE) >= qty * batches for code, qty in components)

	def purchase(self, day):
		by_supplier = {}
		for code, rule in self.p.RAW.items():
			projected = self.qty(code, RAW_WAREHOUSE) + self.on_order.get(code, 0)
			if projected < rule["reorder_level"]:
				by_supplier.setdefault(rule["supplier"], []).append((code, rule["reorder_qty"]))
		for supplier, lines in sorted(by_supplier.items()):
			key = self.next_key("po")
			lead = max(self.p.RAW[code]["lead_days"] for code, _qty in lines)
			arrival = add_workdays(day, lead)
			rated = [(code, qty, self.p.buying_rate(code, day)) for code, qty in lines]
			self.emit(day, "po", key, supplier=supplier, lines=rated, arrival=arrival.isoformat())
			for code, qty in lines:
				self.on_order[code] = self.on_order.get(code, 0) + qty
			if arrival <= self.today:
				self.arrivals.setdefault(arrival, []).append((key, lines))

	def is_month_end(self, day):
		following = add_workdays(day, 1)
		return following.month != day.month

	def count(self, day):
		lines = []
		for code, warehouse, delta in self.p.COUNTS:
			if self.qty(code, warehouse) + delta >= 0:
				self.add(code, warehouse, delta)
				lines.append((code, warehouse, delta))
		if lines:
			self.emit(day, "count", f"count:{day:%Y-%m}", lines=lines)


def plan(profile, start, today, seed=2026):
	"""All events from start to today (dates as datetime.date)."""
	story = Story(profile, start, today, seed)
	events = story.run()
	add_specials(profile, events, today)
	return events


def add_specials(profile, events, today):
	"""One cancelled-and-reissued invoice and one credit note, on invoices of
	about two and three weeks ago, so a prospect can open both."""
	invoices = [e for e in events if e["type"] == "si"]
	if len(invoices) < 10:
		return
	by_age = sorted(invoices, key=lambda e: abs((today - datetime.date.fromisoformat(e["date"])).days - 14))
	cancelled = by_age[0]
	day = cancelled["date"]
	events.append(
		{"date": day, "type": "cancel", "key": f"cancel:{cancelled['key'][3:]}", "ref": cancelled["key"]}
	)
	events.append(
		{
			"date": day,
			"type": "reinvoice",
			"key": f"reinvoice:{cancelled['key'][3:]}",
			"ref": cancelled["ref"],
		}
	)
	# Payments planned on the cancelled invoice go to the new one
	for event in events:
		if event["type"] == "spay" and event["ref"] == cancelled["key"]:
			event["ref"] = f"reinvoice:{cancelled['key'][3:]}"
	older = [
		e
		for e in invoices
		if e is not cancelled and (today - datetime.date.fromisoformat(e["date"])).days >= 21
	]
	if older:
		target = older[-1]
		events.append(
			{
				"date": (
					datetime.date.fromisoformat(target["date"]) + datetime.timedelta(days=2)
				).isoformat(),
				"type": "return",
				"key": f"return:{target['key'][3:]}",
				"ref": target["key"],
				"part": 0.1,
			}
		)
	events.sort(key=lambda e: (e["date"], PRIORITY[e["type"]], e["key"]))
