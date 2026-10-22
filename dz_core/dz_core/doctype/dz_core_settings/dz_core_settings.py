"""DZ Core Settings: what differs from one client to another in the base.

Rule of the project (same as dz_cod): per-client differences live here or in
custom fields, never in `if client == ...` branches in the code.
"""

import frappe
from frappe import _
from frappe.model.document import Document

SECTORS = ("Alimentaire et cosmétique", "Confection")
IFU = "IFU"
REEL = "Régime réel"
AUTO = "Auto-entrepreneur"  # loi 22-23: no TVA, like the IFU (0.5 % of turnover)
NO_TVA = (IFU, AUTO)
REGIMES = (IFU, REEL, AUTO)


class DZCoreSettings(Document):
	def validate(self):
		for fieldname in ("raw_materials_warehouse", "wip_warehouse", "finished_goods_warehouse"):
			warehouse = self.get(fieldname)
			if warehouse and frappe.db.get_value("Warehouse", warehouse, "company") != self.company:
				frappe.throw(
					_("L'entrepôt {0} n'appartient pas à la société {1}.").format(warehouse, self.company)
				)
		from dz_core.stamp import check_settings

		check_settings(self)


def get_settings():
	"""The DZ Core Settings document (cached, read-only use)."""
	return frappe.get_cached_doc("DZ Core Settings")
