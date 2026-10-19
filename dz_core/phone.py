"""Algerian phone numbers: clean them up and check them.

Pure Python (no database), so it is easy to test. Moved from dz_cod (October
2026): the import workbook and the Customer form use it too.
"""

import re

# Mobile: 05, 06 or 07 followed by 8 digits (Ooredoo, Mobilis, Djezzy)
MOBILE = re.compile(r"^0[567]\d{8}$")
# Landline: 0 + area code + 7 digits = 9 digits in total (for example 021 23 45 67)
LANDLINE = re.compile(r"^0[1-4]\d{7}$")


def normalize_phone(phone):
	"""Turn "+213 555 12-34-56" or "00213555123456" into "0555123456".

	Returns the input unchanged (just stripped) if it does not look Algerian,
	so we never destroy what the operator typed.
	"""
	if not phone:
		return phone

	digits = re.sub(r"\D", "", phone)  # keep digits only
	if digits.startswith("00213"):
		digits = "0" + digits[5:]
	elif digits.startswith("213"):
		digits = "0" + digits[3:]

	if is_valid_phone(digits):
		return digits
	return phone.strip()


def is_valid_phone(phone):
	"""True for a 10-digit mobile or a 9-digit landline number."""
	return bool(phone and (MOBILE.match(phone) or LANDLINE.match(phone)))


def normalize_customer_phone(customer, method=None):
	"""Customer "validate" hook (hooks.py): store the phone in one format, so
	the same number typed two ways is found as one (dz_cod's duplicate check)."""
	customer.dz_phone = normalize_phone(customer.get("dz_phone"))
