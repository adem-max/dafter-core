"""Give the entries made before 0.4.1 their closing key (Journal Entry
dz_closing_key, closing.closing_key), read from their French remark: until
then they were found by that remark (review of 27 October 2026, 2.5)."""

import re

import frappe
from frappe.utils import getdate

from dz_core.closing import closing_key
from dz_core.setup.custom_fields import setup_custom_fields

# remark written by Daftar -> (kind, how to read the period)
MONTH = r"(\d{2})/(\d{4})"
PATTERNS = [
	(re.compile(rf"^Liquidation TVA {MONTH}$"), "tva"),
	(re.compile(rf"^Reversement TVA pertes et dons {MONTH}$"), "tva-losses"),
	(re.compile(r"^Reclassement 4081 vers 4097 au \d{2}/(\d{2})/(\d{4})$"), "srbnb"),
	(re.compile(r"^IFU de l'exercice (.+)$"), "ifu"),
]


def key_of(remark, posting_date):
	for pattern, kind in PATTERNS:
		found = pattern.match(remark or "")
		if not found:
			continue
		if kind == "ifu":
			return closing_key(kind, fiscal_year=found.group(1))
		month, year = found.groups()
		day = getdate(f"{year}-{month}-01")
		# the 4081 reclassification is two entries: the month end, then its reversal on the 1st
		if kind == "srbnb" and getdate(posting_date).strftime("%Y-%m") != day.strftime("%Y-%m"):
			kind = "srbnb-reversal"
		return closing_key(kind, day)
	return None


def execute():
	setup_custom_fields()  # the field comes with after_migrate, which runs after the patches
	for name, remark, posting_date in frappe.get_all(
		"Journal Entry",
		filters={"dz_closing_key": ["is", "not set"], "user_remark": ["is", "set"]},
		fields=["name", "user_remark", "posting_date"],
		as_list=True,
	):
		key = key_of(remark, posting_date)
		if key:
			frappe.db.set_value("Journal Entry", name, "dz_closing_key", key, update_modified=False)
