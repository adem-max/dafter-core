"""Stamp duty on receipts paid in cash, "droit de timbre de quittance"
(code du timbre arts. 4, 19, 100, 258, 258 quinquies; circular
14/MF/DGI/LF.2025; SCF advice Q17; DECISIONS.md, "Tax").

Off by default (DZ Core Settings "Calculer le droit de timbre"): its
application to cash-on-delivery sales is open with the tax office, so a
client switches it on once their accountant agrees. Then, for each payment
mode of the settings' table:

- "Ajouté à la facture": a "Droit de timbre" row on 445751, after the TVA
  and outside its base, paid by the buyer;
- "À la charge du vendeur": the same row plus a negative one on 6457 Droits
  de timbre, so the total does not change (the only choice for
  cash-on-delivery: the courier collects a fixed amount).

Cheques and transfers are exempt when the invoice carries their references
(cheque number, date and drawee bank; transfer dates and banks), art. 258.
Card and BaridiMob payments are exempt (art. 258 quinquies) and are not in
the table. The duty is computed on the draft invoice; a credit note gets
none. A cash payment entered later, on an invoice without the duty, warns.

Scale: nothing up to 300 DA; above, per band of 100 DA or part of it, 1 DA up
to 30,000 DA, 1.5 DA up to 100,000 DA, 2 DA above (the rate of the band the
whole amount falls in), at least 5 DA, no cap. 35,000 DA -> 525 DA. Réel
sellers pay it on the G50 (line E2E12, shown by "Aide G50").
"""

import math

import frappe
from frappe import _
from frappe.utils import flt

from dz_core.setup.accounts import account_by_number

STAMP_ACCOUNT, SELLER_ACCOUNT = "445751", "6457"
ADDED, SELLER_PAYS = "Ajouté à la facture", "À la charge du vendeur"
# French on the legal invoice whatever the user's language; Facture DZ leaves
# out the seller's two rows (they add up to nothing for the buyer)
LABEL = "Droit de timbre"
SELLER_LABEL = "Droit de timbre (à la charge du vendeur)"
CASH, CHEQUE, TRANSFER, COD = "Espèces", "Chèque", "Virement", "Contre-remboursement"
WITH_REFERENCES = (CHEQUE, TRANSFER)
DEFAULT_MODES = [(CASH, ADDED), (CHEQUE, ADDED), (TRANSFER, ADDED)]
RATES = ((30_000, 1), (100_000, 1.5))  # (up to, DA per band), else 2 DA


def stamp_amount(amount):
	"""The duty on a cash receipt of `amount` DA."""
	amount = flt(amount, 2)
	if amount <= 300:
		return 0
	rate = next((rate for limit, rate in RATES if amount <= limit), 2)
	return max(5, flt(math.ceil(amount / 100) * rate, 2))


def mode_charge(mode):
	"""ADDED, SELLER_PAYS or None for this payment mode, as the settings say."""
	settings = frappe.get_cached_doc("DZ Core Settings")
	if not settings.get("stamp_duty"):
		return None
	return next((row.charge for row in settings.get("stamp_modes") or [] if row.mode == mode), None)


def has_references(doc):
	return bool(
		doc.get("dz_payment_reference")
		and doc.get("dz_payment_reference_date")
		and doc.get("dz_payment_bank")
	)


def is_stamp_row(row, accounts):
	return row.charge_type == "Actual" and row.account_head in accounts


def apply_stamp(doc, method=None):
	"""Sales Invoice validate (hooks.py): one up-to-date duty row, or none."""
	if doc.docstatus != 0:
		return
	accounts = {account_by_number(doc.company, STAMP_ACCOUNT), account_by_number(doc.company, SELLER_ACCOUNT)}
	accounts.discard(None)
	stamp_rows = [row for row in doc.get("taxes") or [] if is_stamp_row(row, accounts)]
	charge = None if doc.is_return else mode_charge(doc.get("dz_payment_mode"))
	if charge and doc.dz_payment_mode in WITH_REFERENCES and has_references(doc):
		charge = None
	if not stamp_rows and not charge:
		return
	for row in stamp_rows:
		doc.remove(row)
	doc.calculate_taxes_and_totals()
	amount = stamp_amount(doc.grand_total) if charge else 0
	stamp_account = account_by_number(doc.company, STAMP_ACCOUNT)
	if amount and stamp_account:
		cost_center = doc.get("cost_center") or frappe.get_cached_value("Company", doc.company, "cost_center")
		row = {"charge_type": "Actual", "cost_center": cost_center}
		doc.append(
			"taxes",
			{
				**row,
				"account_head": stamp_account,
				"description": SELLER_LABEL if charge == SELLER_PAYS else LABEL,
				"tax_amount": amount,
			},
		)
		if charge == SELLER_PAYS:
			doc.append(
				"taxes",
				{
					**row,
					"account_head": account_by_number(doc.company, SELLER_ACCOUNT),
					"description": SELLER_LABEL,
					"tax_amount": -amount,
				},
			)
	doc.calculate_taxes_and_totals()


def warn_cash_payment(doc, method=None):
	"""Payment Entry validate (hooks.py): cash received for an invoice that
	carries no duty, while the duty is on for cash."""
	if doc.payment_type != "Receive" or doc.party_type != "Customer" or mode_charge(CASH) != ADDED:
		return
	if not (frappe.db.get_value("Account", doc.paid_to, "account_number") or "").startswith("53"):
		return
	stamp_account = account_by_number(doc.company, STAMP_ACCOUNT)
	for ref in doc.get("references") or []:
		if ref.reference_doctype != "Sales Invoice" or not ref.allocated_amount:
			continue
		if not frappe.db.exists(
			"Sales Taxes and Charges", {"parent": ref.reference_name, "account_head": stamp_account}
		):
			frappe.msgprint(
				_(
					"Paiement en espèces de la facture {0} : droit de timbre de {1} DA à percevoir "
					"(ajoutez-le en déduction, compte 445751)."
				).format(ref.reference_name, stamp_amount(ref.allocated_amount)),
				indicator="orange",
				alert=True,
			)


def setup_defaults():
	"""The table's usual rows on a site that has none (the switch stays off)."""
	settings = frappe.get_single("DZ Core Settings")
	if settings.get("stamp_modes"):
		return
	for mode, charge in DEFAULT_MODES:
		settings.append("stamp_modes", {"mode": mode, "charge": charge})
	settings.flags.ignore_mandatory = True
	settings.save(ignore_permissions=True)


def check_settings(settings):
	"""DZ Core Settings validate: each mode once; cash-on-delivery only at the seller's charge."""
	seen = set()
	for row in settings.get("stamp_modes") or []:
		if row.mode in seen:
			frappe.throw(_("Droit de timbre : le mode {0} figure deux fois.").format(row.mode))
		seen.add(row.mode)
		if row.mode == COD and row.charge != SELLER_PAYS:
			frappe.throw(
				_(
					"Contre-remboursement : le timbre ne peut être qu'à la charge du vendeur (le transporteur encaisse un montant fixe)."
				)
			)
