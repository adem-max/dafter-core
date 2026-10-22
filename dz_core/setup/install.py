"""Run after `bench install-app dz_core` and after every `bench migrate`.

Safe to run many times: it creates what is missing and never overwrites
what the user changed. The client-specific part (company, sector, tax
regime) is not here: it is dz_core.setup.new_client.prepare, run once.
"""

import frappe

from dz_core.features import apply_features, move_legacy_key
from dz_core.setup.custom_fields import setup_custom_fields
from dz_core.setup.wilayas import setup_wilayas


def after_install():
	setup_all()


def after_migrate():
	setup_all()


def setup_all():
	from dz_core.books.statements import setup_statements
	from dz_core.stamp import setup_defaults as setup_stamp_defaults
	from dz_core.tax_checks import setup_informal_supplier

	setup_custom_fields()
	setup_wilayas()
	setup_statements()  # the SCF bilan and compte de résultat (books/statements.py)
	setup_stamp_defaults()  # the payment modes' rows; the stamp duty stays off (stamp.py)
	setup_informal_supplier()  # for purchases without an invoice (tax_checks.py)
	# Optional features: old key name, then records to match the list. Apps on
	# top call apply_features() again after their own setup.
	move_legacy_key()
	apply_features()
	frappe.db.commit()
