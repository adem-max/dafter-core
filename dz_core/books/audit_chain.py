"""The audit trail as a hash chain (review of 27 October 2026, 4.3; decision
D3 taken as proposed on 29 October 2026).

Each DZ Audit Log row carries its number in its company's chain (`seq`), the
hash of the row before it (`previous_hash`) and its own hash (`row_hash` =
SHA-256 of the previous hash and the row's content, its time included). A
row changed, removed or slipped in later breaks every hash after it, and
`verify_chain` says where.

Like a numbered, bound register whose pages also carry the stamp of the page
before: tearing out or rewriting one page shows.

Limit: someone with direct database access (the host) can recompute a whole
chain. So the chain's last hash at each year end is written into the yearly
archive (books/archive.py), whose register is kept off-site: the chain as it
stood then can be proved against that copy.

One chain per company: the demo wipe deletes one company's rows, which must
not break another company's chain. The order is kept by locking the company's
row first, then reading the chain's tail with a locking read (which sees the
latest committed rows), so two documents validated at the same moment cannot
both chain onto the same tail.
"""

import hashlib
import json

import frappe
from frappe.utils import get_datetime

GENESIS = ""
FIELDS = (
	"name",
	"creation",
	"operation",
	"reference_doctype",
	"reference_name",
	"company",
	"user",
	"ip_address",
	"device",
	"details",
	"seq",
	"previous_hash",
)


def canonical(row):
	"""The row's content as one fixed text: same row, same text, whichever way it was read."""
	values = {field: "" if row.get(field) is None else str(row.get(field)) for field in FIELDS}
	values["creation"] = get_datetime(row.get("creation")).strftime("%Y-%m-%d %H:%M:%S.%f")
	return json.dumps(values, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def row_hash(row):
	return hashlib.sha256((row.get("previous_hash") or GENESIS).encode() + canonical(row).encode()).hexdigest()


def company_condition(company):
	return ("company = %(company)s", {"company": company}) if company else ("company IS NULL", {})


def tail(company):
	"""The chain's last row, read with a lock (see the module docstring)."""
	if company:
		frappe.db.sql("SELECT name FROM `tabCompany` WHERE name = %s FOR UPDATE", company)
	condition, values = company_condition(company)
	rows = frappe.db.sql(
		f"""SELECT seq, row_hash FROM `tabDZ Audit Log`
		WHERE {condition} AND seq > 0 ORDER BY seq DESC LIMIT 1 FOR UPDATE""",
		values,
		as_dict=True,
	)
	return rows[0] if rows else None


def link(doc):
	"""Called by DZ Audit Log just before its row is written: name and time are final."""
	last = tail(doc.company)
	doc.seq = (last.seq if last else 0) + 1
	doc.previous_hash = last.row_hash if last else GENESIS
	doc.row_hash = row_hash(doc)


def rows_of(company, until=None):
	condition, values = company_condition(company)
	if until:
		condition += " AND creation <= %(until)s"
		values["until"] = until
	return frappe.db.sql(
		f"SELECT {', '.join(FIELDS)}, row_hash FROM `tabDZ Audit Log` WHERE {condition} ORDER BY seq, creation",
		values,
		as_dict=True,
	)


def verify_chain(company, until=None):
	"""{"ok", "rows", "head" (the last hash), "broken_at" (the first row that
	does not match, with why)}."""
	previous = GENESIS
	rows = rows_of(company, until)
	for number, row in enumerate(rows, start=1):
		why = None
		if row.seq != number:
			why = f"numéro {row.seq} au lieu de {number}"
		elif (row.previous_hash or GENESIS) != previous:
			why = "empreinte précédente différente"
		elif row_hash(row) != row.row_hash:
			why = "contenu modifié"
		if why:
			return {"ok": False, "rows": len(rows), "head": None, "broken_at": f"{row.name} ({why})"}
		previous = row.row_hash
	return {"ok": True, "rows": len(rows), "head": previous, "broken_at": None}


def chain_existing():
	"""Give the rows written before the chain their place in it, in the order
	they were made (patch chain_audit_log). Rows already chained are kept."""
	for (company,) in frappe.db.sql("SELECT DISTINCT company FROM `tabDZ Audit Log`"):
		condition, values = company_condition(company)
		chained = frappe.db.sql(
			f"SELECT COUNT(*) FROM `tabDZ Audit Log` WHERE {condition} AND seq > 0", values
		)[0][0]
		if chained:
			continue
		previous = GENESIS
		for number, row in enumerate(
			frappe.db.sql(
				f"SELECT {', '.join(FIELDS)} FROM `tabDZ Audit Log` WHERE {condition} ORDER BY creation, name",
				values,
				as_dict=True,
			),
			start=1,
		):
			row.seq, row.previous_hash = number, previous
			row.row_hash = row_hash(row)
			frappe.db.set_value(
				"DZ Audit Log",
				row.name,
				{"seq": number, "previous_hash": previous, "row_hash": row.row_hash},
				update_modified=False,
			)
			previous = row.row_hash
