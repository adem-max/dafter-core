"""The monthly close (report "Clôture du mois") and the TVA settlement
(report "Aide G50"), from the SCF advice of 21 October 2026 (DECISIONS.md,
"Monthly close").

Ledger balances are read by SCF account number, so the same code works on
every client's chart. Other apps add their own checks through the hook
`dz_closing_checks` (dz_cod: the couriers' accounts): a function
(company, start, end) returning rows like the ones below.
"""

import frappe
from frappe import _
from frappe.utils import add_days, flt, get_first_day, get_last_day, getdate

OK, TO_CHECK = "OK", "À voir"

# Accounts that must be empty at every month end: (number, what to do)
EMPTY_AT_MONTH_END = [
	("6589", "Reclassez ces charges vers leur compte (60, 61, 62...) : l'article ou son groupe n'en a pas."),
	("4781", "Identifiez ces versements avec le transporteur, puis passez-les au bon compte."),
	("476", "Imputez ces dépenses en attente."),
	("479", "Soldez le compte d'ouverture : l'import d'ouverture n'est pas équilibré."),
]

SRBNB, SUPPLIER_DEBITS = "4081", "4097"  # received not billed; suppliers with a debit balance
PRODUCTION = "72"  # production stockée ou déstockée
STOCKS_OF_PRODUCTS = ("33", "35")  # en-cours and finished goods


def month_bounds(month):
	month = getdate(month)
	return get_first_day(month), get_last_day(month)


def accounts_of(company, number):
	"""The account with this number and every account under it (a group)."""
	row = frappe.db.get_value(
		"Account", {"company": company, "account_number": number}, ["lft", "rgt"], as_dict=True
	)
	if not row:
		return []
	return frappe.get_all(
		"Account", filters={"company": company, "lft": [">=", row.lft], "rgt": ["<=", row.rgt]}, pluck="name"
	)


def accounts_by_prefix(company, prefix):
	return frappe.get_all(
		"Account",
		filters={"company": company, "account_number": ["like", f"{prefix}%"], "is_group": 0},
		pluck="name",
	)


def balance(company, accounts, until, since=None, exclude_vouchers=()):
	"""Debit minus credit on the accounts, up to `until` (from `since` when given)."""
	if not accounts:
		return 0
	conditions = [
		"company = %(company)s",
		"account IN %(accounts)s",
		"is_cancelled = 0",
		"posting_date <= %(until)s",
	]
	if since:
		conditions.append("posting_date >= %(since)s")
	if exclude_vouchers:
		conditions.append("voucher_no NOT IN %(exclude)s")
	return flt(
		frappe.db.sql(
			f"SELECT SUM(debit - credit) FROM `tabGL Entry` WHERE {' AND '.join(conditions)}",
			{
				"company": company,
				"accounts": tuple(accounts),
				"until": until,
				"since": since,
				"exclude": tuple(exclude_vouchers),
			},
		)[0][0]
	)


def opening_vouchers(company):
	"""What brought the opening balances in: every voucher with a line on the
	opening account 479 (the opening count, a receipt of opening stock...).
	Its stock enters against 479, not 72."""
	accounts = frappe.get_all(
		"Account", filters={"company": company, "account_type": "Temporary"}, pluck="name"
	)
	if not accounts:
		return []
	return frappe.get_all(
		"GL Entry",
		filters={"company": company, "account": ["in", accounts], "is_cancelled": 0},
		pluck="voucher_no",
		distinct=True,
	)


def row(check, amount, ok, todo="", action=None, code=None):
	"""One check. `code` names the checks the year end relies on (books/year_end.py)."""
	return {
		"check": check,
		"amount": flt(amount, 2),
		"status": OK if ok else TO_CHECK,
		"todo": "" if ok else todo,
		"action": action,
		"code": code,
	}


# ------------------------------------------------------------ monthly close


def closing_rows(company, month):
	start, end = month_bounds(month)
	rows = []
	for number, todo in EMPTY_AT_MONTH_END:
		accounts = accounts_of(company, number)
		if not accounts and number == "479":
			accounts = frappe.get_all(
				"Account", filters={"company": company, "account_type": "Temporary"}, pluck="name"
			)
		if accounts:
			amount = balance(company, accounts, end)
			label = frappe.db.get_value("Account", accounts[0], "account_name")
			rows.append(
				row(
					_("{0} {1} : solde nul").format(number, label),
					amount,
					abs(amount) < 0.01,
					_(todo),
					code=number,
				)
			)

	debits = srbnb_debits(company, end)
	rows.append(
		row(
			_("4081 : fournisseurs facturés avant la réception ({0})").format(len(debits)),
			sum(debits.values()),
			not debits or bool(srbnb_reclassification(company, end)),
			_("Reclassez ces soldes débiteurs au 4097 (écriture extournée le 1er du mois suivant)."),
			action="reclassify_srbnb",
			code=SRBNB,
		)
	)

	year_start = frappe.db.get_value(
		"Fiscal Year", {"year_start_date": ["<=", end], "year_end_date": [">=", end]}, "year_start_date"
	) or get_first_day(end).replace(month=1)
	production = -balance(company, accounts_by_prefix(company, PRODUCTION), end, since=year_start)
	openings = opening_vouchers(company)
	stock_change = sum(
		balance(
			company, accounts_by_prefix(company, prefix), end, since=year_start, exclude_vouchers=openings
		)
		for prefix in STOCKS_OF_PRODUCTS
	)
	rows.append(
		row(
			_("Classe 72 égale à la variation des classes 33 et 35 depuis le début de l'exercice"),
			production - stock_change,
			abs(production - stock_change) < 1,
			_(
				"Un mouvement de produits finis ou d'en-cours n'est pas passé par le 72 : voyez avec le comptable."
			),
			code=PRODUCTION,
		)
	)

	for method in frappe.get_hooks("dz_closing_checks"):
		rows += frappe.get_attr(method)(company, start, end)

	frozen = frappe.db.get_value("Company", company, "accounts_frozen_till_date")
	rows.append(
		row(
			_("Mois gelé (plus aucune écriture avant le {0})").format(frappe.format(end, "Date")),
			0,
			bool(frozen) and getdate(frozen) >= end,
			_("Une fois les contrôles faits, gelez le mois."),
			action="freeze_month",
			code="frozen",
		)
	)
	return rows


def srbnb_debits(company, until):
	"""{supplier: debit balance} on 4081: invoices booked before their goods arrived."""
	accounts = accounts_of(company, SRBNB)
	if not accounts:
		return {}
	balances = {}
	for doctype in ("Purchase Receipt", "Purchase Invoice"):
		for supplier, amount in frappe.db.sql(
			f"""SELECT doc.supplier, SUM(gle.debit - gle.credit)
			FROM `tabGL Entry` gle JOIN `tab{doctype}` doc ON doc.name = gle.voucher_no
			WHERE gle.voucher_type = %s AND gle.account IN %s AND gle.is_cancelled = 0
				AND gle.company = %s AND gle.posting_date <= %s
			GROUP BY doc.supplier""",
			(doctype, tuple(accounts), company, until),
		):
			balances[supplier] = balances.get(supplier, 0) + flt(amount)
	return {supplier: amount for supplier, amount in balances.items() if amount > 0.01}


def srbnb_remark(end):
	return _("Reclassement 4081 vers 4097 au {0}").format(getdate(end).strftime("%d/%m/%Y"))


def srbnb_reclassification(company, end):
	"""The month's reclassification entry, if it was posted."""
	return frappe.db.get_value(
		"Journal Entry",
		{"company": company, "docstatus": 1, "posting_date": end, "user_remark": srbnb_remark(end)},
	)


@frappe.whitelist()
def reclassify_srbnb(company, month):
	"""Dr 4097 / Cr 4081 at the month end for the suppliers' debit balances,
	reversed on the 1st of the next month. Returns the two entries."""
	frappe.has_permission("Journal Entry", "create", throw=True)
	_start, end = month_bounds(month)
	if srbnb_reclassification(company, end):
		frappe.throw(_("Le 4081 de ce mois est déjà reclassé."))
	debits = srbnb_debits(company, end)
	if not debits:
		return []
	srbnb, target = accounts_of(company, SRBNB)[0], accounts_of(company, SUPPLIER_DEBITS)[0]
	remark = srbnb_remark(end)
	names = []
	for posting_date, debit_account, credit_account in (
		(end, target, srbnb),
		(add_days(end, 1), srbnb, target),
	):
		entry = frappe.new_doc("Journal Entry")
		entry.update({"company": company, "posting_date": posting_date, "user_remark": remark})
		for supplier, amount in debits.items():
			entry.append(
				"accounts",
				{"account": debit_account, "debit_in_account_currency": amount, "user_remark": supplier},
			)
			entry.append(
				"accounts",
				{"account": credit_account, "credit_in_account_currency": amount, "user_remark": supplier},
			)
		entry.insert()
		entry.submit()
		names.append(entry.name)
	return names


@frappe.whitelist()
def freeze_month(company, month):
	"""No entry may be posted on or before the month end any more (Company
	"Accounts Frozen Till Date"), except by the roles allowed there."""
	from dz_core.books.audit import frozen

	frappe.has_permission("Company", "write", doc=company, throw=True)
	_start, end = month_bounds(month)
	before = frappe.db.get_value("Company", company, "accounts_frozen_till_date")
	frappe.db.set_value("Company", company, "accounts_frozen_till_date", end)
	frozen(company, before, end)
	return end


# ------------------------------------------------------------ TVA (Aide G50)

COLLECTED_19, COLLECTED_9 = "445711", "445712"
DEDUCTIBLE, DEDUCTIBLE_ASSETS = "44566", "44562"
CREDIT, PAYABLE = "44568", "44551"
STAMP_DUTY = "445751"  # droits de timbre de quittance à reverser (stamp.py)


def settlement_remark(end):
	return _("Liquidation TVA {0}").format(getdate(end).strftime("%m/%Y"))


def tva_figures(company, month):
	"""The month's TVA: bases per rate, collected, deductible, credit, result."""
	start, end = month_bounds(month)
	settlement = frappe.get_all(
		"Journal Entry",
		filters={"company": company, "docstatus": 1, "user_remark": settlement_remark(end)},
		pluck="name",
	)

	def movement(number):
		return balance(company, accounts_of(company, number), end, since=start, exclude_vouchers=settlement)

	bases = {"19": 0.0, "9": 0.0, "0": 0.0}
	accounts = {accounts_of(company, n)[0]: n for n in (COLLECTED_19, COLLECTED_9) if accounts_of(company, n)}
	for net, rates in frappe.db.sql(
		"""SELECT item.base_net_amount, item.item_tax_rate
		FROM `tabSales Invoice Item` item JOIN `tabSales Invoice` inv ON inv.name = item.parent
		WHERE inv.docstatus = 1 AND inv.company = %s AND inv.posting_date BETWEEN %s AND %s""",
		(company, start, end),
	):
		rates = frappe.parse_json(rates or "{}") or {}
		applied = {accounts[a]: flt(r) for a, r in rates.items() if a in accounts and flt(r)}
		key = "19" if applied.get(COLLECTED_19) else "9" if applied.get(COLLECTED_9) else "0"
		bases[key] += flt(net)

	collected_19, collected_9 = -movement(COLLECTED_19), -movement(COLLECTED_9)
	deductible, deductible_assets = movement(DEDUCTIBLE), movement(DEDUCTIBLE_ASSETS)
	credit_before = balance(company, accounts_of(company, CREDIT), add_days(start, -1))
	result = collected_19 + collected_9 - deductible - deductible_assets - max(credit_before, 0)
	return frappe._dict(
		start=start,
		end=end,
		bases=bases,
		collected_19=collected_19,
		collected_9=collected_9,
		deductible=deductible,
		deductible_assets=deductible_assets,
		credit_before=max(credit_before, 0),
		to_pay=max(result, 0),
		new_credit=max(-result, 0),
		settlement=settlement[0] if settlement else None,
		stamp=-movement(STAMP_DUTY),  # paid on the same G50, line E2E12
	)


@frappe.whitelist()
def make_tva_settlement(company, month):
	"""The month's TVA settlement entry, dated the month end: the collected
	TVA against the deductible, the credit carried, and what is to pay on the
	G50 (44551) or the new credit (44568). Once per month."""
	frappe.has_permission("Journal Entry", "create", throw=True)
	f = tva_figures(company, month)
	if f.settlement:
		frappe.throw(_("La TVA de ce mois est déjà liquidée : {0}.").format(f.settlement))

	def account(number):
		return accounts_of(company, number)[0]

	lines = [
		(COLLECTED_19, f.collected_19),
		(COLLECTED_9, f.collected_9),
		(DEDUCTIBLE, -f.deductible),
		(DEDUCTIBLE_ASSETS, -f.deductible_assets),
		(CREDIT, -f.credit_before + f.new_credit),
		(PAYABLE, -f.to_pay),
	]
	entry = frappe.new_doc("Journal Entry")
	entry.update({"company": company, "posting_date": f.end, "user_remark": settlement_remark(f.end)})
	for number, amount in lines:
		amount = flt(amount, 2)
		if amount:
			entry.append(
				"accounts",
				{
					"account": account(number),
					"debit_in_account_currency": max(amount, 0),
					"credit_in_account_currency": max(-amount, 0),
				},
			)
	if not entry.accounts:
		frappe.throw(_("Pas de TVA ce mois-ci."))
	entry.insert()
	entry.submit()
	return entry.name
