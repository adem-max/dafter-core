"""DZ Wilaya: one record per wilaya (the 69 of 2026, dz_core/setup/wilayas.py).

Used for customer addresses and imports here; dz_cod adds the delivery rates
of each wilaya as custom fields (dz_cod/setup/custom_fields.py).
"""

from frappe.model.document import Document


class DZWilaya(Document):
	def validate(self):
		# Always store the code with two digits: "1" becomes "01"
		self.code = str(self.code).strip().zfill(2)
