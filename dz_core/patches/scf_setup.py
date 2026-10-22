"""Sites set up before the SCF advice of 21 October 2026 get its set-up
(setup/scf.py): chart changes, default accounts, accounting settings,
accounts per item group, supplier groups, payment modes, no deletion of
accounting documents.

What ERPNext refuses on a company with entries is skipped and printed:
inventory accounts per item need a company without stock entries, a ledger
becomes a group only while it has no entry. No client site was live; the
demos are moved over by a full wipe (demo/wipe.py, full=1)."""

import frappe

from dz_core.setup.scf import apply_scf_setup


def execute():
	for company in frappe.get_all("Company", pluck="name"):
		for line in apply_scf_setup(company):
			print(f"{company}: {line}")
