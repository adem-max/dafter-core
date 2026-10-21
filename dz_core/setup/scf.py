"""Everything a company needs on the Algerian chart before its first entry,
from the SCF advice of 21 October 2026 (DECISIONS.md, "Chart of accounts and
default accounts"): chart changes, default accounts, accounting settings,
accounts per item group, supplier groups, payment modes, asset categories,
TVA templates per rate, and no deletion of accounting documents.

Run by prepare() on a new client, by the patch scf_setup on existing sites
and by the demo loaders. Safe to run again: nothing someone chose is
overwritten, and what ERPNext refuses on a company with entries (item-wise
inventory, converting a used ledger to a group) is skipped and reported.
"""

import frappe

from dz_core.setup.accounts import set_accounting_settings, set_default_accounts
from dz_core.setup.chart import apply_chart_changes
from dz_core.setup.item_groups import setup_item_groups
from dz_core.setup.parties import setup_parties
from dz_core.setup.permissions import lock_deletions
from dz_core.setup.sectors import SECTORS
from dz_core.setup.tax import REEL, set_default_templates, setup_tva


def apply_scf_setup(company, sector=None):
	"""Returns a list of lines saying what changed or was skipped."""
	log = apply_chart_changes(company)
	log += set_accounting_settings(company)  # before the defaults: warehouse accounts depend on it
	log += [f"{field}: {old or '-'} -> {new}" for field, (old, new) in set_default_accounts(company).items()]
	settings = frappe.get_single("DZ Core Settings")
	ours = settings.company == company
	if not sector and ours:
		sector = settings.sector
	setup_item_groups(company, SECTORS[sector]["group_kinds"] if sector in SECTORS else {})
	setup_parties(company)
	# TVA per rate (setup/tax.py); on the régime réel its templates are the defaults
	setup_tva(company)
	if ours and settings.tax_regime == REEL:
		set_default_templates(company)
	log += [f"no {right} on {doctype} for {role}" for doctype, role, right in lock_deletions()]
	return log
