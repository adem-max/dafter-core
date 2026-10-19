"""The 69 wilayas of Algeria: the list every client gets (doctype DZ Wilaya).

Source of the list:
- Wilayas 01 to 58: law 84-09 as amended in 2019 (58 wilayas).
- Wilayas 59 to 69: law 26-06 of 4 April 2026 (JO n° 25 of 5 April 2026)
  and presidential decree 26-206 of 25 May 2026 (JO n° 40), which set their
  names and numbers. The new wilayas take over from their "parent" wilaya
  progressively until 31 December 2026.

Couriers and old documents may keep using the 58-wilaya codes for a while, so
each new wilaya remembers its parent wilaya (field `parent_wilaya`).

Moved from dz_cod (October 2026). dz_cod adds the delivery rates to each
wilaya as custom fields (dz_cod/setup/wilayas.py).
"""

import unicodedata

import frappe

# (code, name, parent wilaya code for the 2026 wilayas)
WILAYAS = [
	("01", "Adrar", None),
	("02", "Chlef", None),
	("03", "Laghouat", None),
	("04", "Oum El Bouaghi", None),
	("05", "Batna", None),
	("06", "Béjaïa", None),
	("07", "Biskra", None),
	("08", "Béchar", None),
	("09", "Blida", None),
	("10", "Bouira", None),
	("11", "Tamanrasset", None),
	("12", "Tébessa", None),
	("13", "Tlemcen", None),
	("14", "Tiaret", None),
	("15", "Tizi Ouzou", None),
	("16", "Alger", None),
	("17", "Djelfa", None),
	("18", "Jijel", None),
	("19", "Sétif", None),
	("20", "Saïda", None),
	("21", "Skikda", None),
	("22", "Sidi Bel Abbès", None),
	("23", "Annaba", None),
	("24", "Guelma", None),
	("25", "Constantine", None),
	("26", "Médéa", None),
	("27", "Mostaganem", None),
	("28", "M'Sila", None),
	("29", "Mascara", None),
	("30", "Ouargla", None),
	("31", "Oran", None),
	("32", "El Bayadh", None),
	("33", "Illizi", None),
	("34", "Bordj Bou Arréridj", None),
	("35", "Boumerdès", None),
	("36", "El Tarf", None),
	("37", "Tindouf", None),
	("38", "Tissemsilt", None),
	("39", "El Oued", None),
	("40", "Khenchela", None),
	("41", "Souk Ahras", None),
	("42", "Tipaza", None),
	("43", "Mila", None),
	("44", "Aïn Defla", None),
	("45", "Naâma", None),
	("46", "Aïn Témouchent", None),
	("47", "Ghardaïa", None),
	("48", "Relizane", None),
	("49", "Timimoun", None),
	("50", "Bordj Badji Mokhtar", None),
	("51", "Ouled Djellal", None),
	("52", "Béni Abbès", None),
	("53", "In Salah", None),
	("54", "In Guezzam", None),
	("55", "Touggourt", None),
	("56", "Djanet", None),
	("57", "El M'Ghair", None),
	("58", "El Meniaa", None),
	# Created by law 26-06 (2026). Parent wilayas: please double-check against
	# the Journal officiel, they come from press reports of the law.
	("59", "Aflou", "03"),
	("60", "Barika", "05"),
	("61", "El Kantara", "07"),
	("62", "Bir El Ater", "12"),
	("63", "El Aricha", "13"),
	("64", "Ksar Chellala", "14"),
	("65", "Aïn Ouessara", "17"),
	("66", "Messaad", "17"),
	("67", "Ksar El Boukhari", "26"),
	("68", "Bou Saâda", "28"),
	("69", "El Abiodh Sidi Cheikh", "32"),
]


def wilaya_docname(code, name):
	"""Record name used for a wilaya, for example "16 - Alger"."""
	return f"{code} - {name}"


def setup_wilayas():
	"""Create the 69 wilayas. Existing ones are left alone."""
	codes_to_names = {code: wilaya_docname(code, name) for code, name, _parent in WILAYAS}
	for code, name, _parent in WILAYAS:
		if not frappe.db.exists("DZ Wilaya", {"code": code}):
			frappe.get_doc({"doctype": "DZ Wilaya", "code": code, "wilaya_name": name}).insert(
				ignore_permissions=True
			)
	# Second pass: the parents exist now
	for code, _name, parent in WILAYAS:
		if parent and not frappe.db.get_value("DZ Wilaya", codes_to_names[code], "parent_wilaya"):
			frappe.db.set_value("DZ Wilaya", codes_to_names[code], "parent_wilaya", codes_to_names[parent])


def find_wilaya(text):
	"""The DZ Wilaya record for what a person typed: "16", "16 - Alger" or "Alger"
	(accents and case ignored). None when nothing matches."""
	text = str(text or "").strip()
	if not text:
		return None
	if frappe.db.exists("DZ Wilaya", text):
		return text
	if text.isdigit():
		return frappe.db.get_value("DZ Wilaya", {"code": text.zfill(2)})
	wanted = simplify(text)
	for name, wilaya_name in frappe.get_all("DZ Wilaya", fields=["name", "wilaya_name"], as_list=True):
		if simplify(wilaya_name) == wanted:
			return name
	return None


def simplify(text):
	"""Turn "Béjaïa" into "bejaia": accents, case, dashes and apostrophes ignored."""
	text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
	return "".join(char for char in text.lower() if char.isalnum())
