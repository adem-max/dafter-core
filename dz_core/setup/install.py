"""Run after `bench install-app dz_core` and after every `bench migrate`.

Safe to run many times: it creates what is missing and never overwrites
what the user changed. The client-specific part (company, sector, tax
regime) is not here: it is dz_core.setup.new_client.prepare, run once.
"""

import frappe

from dz_core.setup.custom_fields import setup_custom_fields
from dz_core.setup.wilayas import setup_wilayas


def after_install():
	setup_all()


def after_migrate():
	setup_all()


def setup_all():
	setup_custom_fields()
	setup_wilayas()
	frappe.db.commit()
