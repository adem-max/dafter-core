"""Helpers available in print formats (registered under `jinja` in hooks.py)."""

from frappe.utils import flt, fmt_money
from num2words import num2words


def montant_en_lettres(amount):
	"""32400.5 -> "trente-deux mille quatre cents dinars algériens et cinquante centimes".

	Always in French, whatever the user's language: ERPNext's own "In Words"
	follows the language of whoever saved the document (often English)."""

	def in_words(number):
		# Frappe's own in_words() follows the user's language; num2words is what it uses underneath
		return num2words(number, lang="fr")

	amount = round(flt(amount), 2)
	dinars = int(amount)
	centimes = round((amount - dinars) * 100)
	number_words = in_words(dinars)
	# "deux millions de dinars": French puts "de" after million and milliard
	link = " de" if number_words.endswith(("million", "millions", "milliard", "milliards")) else ""
	words = f"{number_words}{link} dinar{'s' if dinars > 1 else ''} algérien{'s' if dinars > 1 else ''}"
	if centimes:
		words += f" et {in_words(centimes)} centime{'s' if centimes > 1 else ''}"
	return words


def montant(amount):
	"""32400 -> "32 400,00": the amount without currency symbol, French separators."""
	return fmt_money(flt(amount), precision=2, format="# ###,##")
