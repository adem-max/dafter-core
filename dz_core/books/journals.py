"""The journal of each ledger line (decree 09-110 art. 12; SCF advice Q6).

ERPNext has no journals: every voucher posts to one General Ledger. The
accountant and the export expect the usual French-style journals, so each
line gets one from its voucher, computed when needed (nothing stored, so the
history needs no migration):

- an opening entry (is_opening) is in the à-nouveaux journal AN;
- invoices: VE (sales), AC (purchases);
- stock documents: ST;
- payments and journal entries: CA when they move cash (53x), BQ when they
  move a bank, the post office or cards (51x, 52x, 54x), else OD (couriers'
  collections into 4671n, reclassifications, the TVA settlement...).
"""

from frappe import _

AN = "AN"
JOURNALS = {
	"VE": "Ventes",
	"AC": "Achats",
	"CA": "Caisse",
	"BQ": "Banque",
	"ST": "Stocks",
	"OD": "Opérations diverses",
	AN: "À-nouveaux",
}

BY_VOUCHER = {
	"Sales Invoice": "VE",
	"Purchase Invoice": "AC",
	"Stock Entry": "ST",
	"Stock Reconciliation": "ST",
	"Delivery Note": "ST",
	"Purchase Receipt": "ST",
	"Landed Cost Voucher": "ST",
}

# account number prefix -> journal, the first that matches wins (cash before bank)
TREASURY = (("53", "CA"), ("51", "BQ"), ("52", "BQ"), ("54", "BQ"))


def treasury_journal(account_number):
	for prefix, code in TREASURY:
		if (account_number or "").startswith(prefix):
			return code


def treasury_journals(lines):
	"""{voucher_no: CA or BQ} for the vouchers among `lines` (dicts with
	voucher_no and account_number) that move cash or a bank."""
	found = {}
	for line in lines:
		code = treasury_journal(line.account_number)
		if code and found.get(line.voucher_no) != "CA":
			found[line.voucher_no] = code
	return found


def journal_of(line, treasury):
	"""The journal code of one ledger line. `treasury` comes from
	treasury_journals() over all the lines of the same vouchers."""
	if line.get("is_opening") == "Yes":
		return AN
	return BY_VOUCHER.get(line.voucher_type) or treasury.get(line.voucher_no) or "OD"


def journal_label(code):
	return _(JOURNALS[code])
