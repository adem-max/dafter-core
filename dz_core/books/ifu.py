"""IFU and auto-entrepreneur figures, "Aide G12" (SCF advice Q18;
DECISIONS.md, "Tax").

- The year's turnover, from the same invoices as the sales register (credit
  notes deducted, opening invoices left out), per month, split into goods
  (what is made or resold, and the delivery fee billed with them) and
  services (items of the "Services" item group);
- the IFU on it: 5 % on goods and 12 % on services, or 0.5 % of turnover for
  an auto-entrepreneur. The rates are written here, to be confirmed with the
  client's accountant;
- the G12 prévisionnel (by 30 June) starts from the year before's turnover;
  the G12 bis (by 20 January of the next year) declares this one;
- a button books the year's IFU not yet booked: Dr 6428 IFU / Cr 4477 IFU à
  payer, dated the year end (or today, during the year).

A help for the declaration, not the declaration.
"""

import frappe
from erpnext.accounts.utils import get_fiscal_year
from frappe import _
from frappe.utils import add_days, add_years, flt, getdate, today
from frappe.utils.nestedset import get_descendants_of

from dz_core.books.tables import AMOUNT, TEXT, table
from dz_core.dz_core.doctype.dz_core_settings.dz_core_settings import AUTO

SERVICES_ROOT = "Services"  # ERPNext's group, kept by the set-up (DECISIONS "Setup")
IFU_RATES = {"goods": 5, "services": 12}  # % of turnover (to confirm with the accountant)
AUTO_RATE = 0.5
CHARGE, PAYABLE = "6428", "4477"


def service_groups():
	if not frappe.db.exists("Item Group", SERVICES_ROOT):
		return set()
	return {SERVICES_ROOT, *get_descendants_of("Item Group", SERVICES_ROOT)}


def turnover_by_month(company, start, end):
	"""{"MM/YYYY": {"goods": x, "services": y}} of the period."""
	services = service_groups()
	result = {}
	for posting_date, item_group, amount in frappe.db.sql(
		"""SELECT inv.posting_date, item.item_group, item.base_net_amount
		FROM `tabSales Invoice Item` item JOIN `tabSales Invoice` inv ON inv.name = item.parent
		WHERE inv.company = %s AND inv.docstatus = 1 AND inv.is_opening != 'Yes'
			AND inv.posting_date BETWEEN %s AND %s
		ORDER BY inv.posting_date""",
		(company, start, end),
	):
		month = getdate(posting_date).strftime("%m/%Y")
		kind = "services" if item_group in services else "goods"
		result.setdefault(month, {"goods": 0.0, "services": 0.0})[kind] += flt(amount)
	return result


def year_figures(company, fiscal_year=None, regime=None):
	if not fiscal_year:
		fiscal_year = get_fiscal_year(today(), company=company)[0]
	start, end = (
		getdate(d)
		for d in frappe.db.get_value("Fiscal Year", fiscal_year, ["year_start_date", "year_end_date"])
	)
	months = turnover_by_month(company, start, end)
	goods = sum(m["goods"] for m in months.values())
	services = sum(m["services"] for m in months.values())
	if regime == AUTO:
		due = flt((goods + services) * AUTO_RATE / 100, 2)
	else:
		due = flt(goods * IFU_RATES["goods"] / 100 + services * IFU_RATES["services"] / 100, 2)
	before = turnover_by_month(company, add_years(start, -1), add_days(start, -1))
	charge = frappe.db.get_value("Account", {"company": company, "account_number": CHARGE, "is_group": 0})
	booked = (
		flt(
			# not the closing voucher, which empties 6428 at the year end: once the
			# year was closed, the IFU booked read 0 (review of 27 October 2026, 1.1)
			frappe.db.sql(
				"""SELECT SUM(debit - credit) FROM `tabGL Entry` WHERE company = %s AND account = %s
				AND is_cancelled = 0 AND posting_date BETWEEN %s AND %s
				AND voucher_type != 'Period Closing Voucher'""",
				(company, charge, start, end),
			)[0][0]
		)
		if charge
		else 0
	)
	return frappe._dict(
		fiscal_year=fiscal_year,
		start=start,
		end=end,
		months=months,
		goods=flt(goods, 2),
		services=flt(services, 2),
		turnover=flt(goods + services, 2),
		due=due,
		booked=flt(booked, 2),
		previous_turnover=flt(sum(m["goods"] + m["services"] for m in before.values()), 2),
		regime=regime,
	)


def figures_table(f):
	lines = [
		[month, flt(m["goods"], 2), flt(m["services"], 2), flt(m["goods"] + m["services"], 2)]
		for month, m in f.months.items()
	]
	lines.append([_("Total {0}").format(f.fiscal_year), f.goods, f.services, f.turnover])
	if f.regime == AUTO:
		lines.append(
			[_("Impôt forfaitaire de l'auto-entrepreneur ({0} %)").format(AUTO_RATE), None, None, f.due]
		)
	else:
		lines.append(
			[
				_("IFU ({0} % biens, {1} % services, à confirmer)").format(
					IFU_RATES["goods"], IFU_RATES["services"]
				),
				None,
				None,
				f.due,
			]
		)
	lines.append([_("IFU déjà comptabilisé (6428)"), None, None, f.booked])
	lines.append(
		[
			_("Chiffre d'affaires de l'exercice précédent (base du G12 prévisionnel)"),
			None,
			None,
			f.previous_turnover,
		]
	)
	return table(
		_("IFU, chiffre d'affaires (G12)"),
		[(_("Mois"), TEXT), (_("Ventes de biens"), AMOUNT), (_("Services"), AMOUNT), (_("Total"), AMOUNT)],
		lines,
	)


def ifu_table(company, start, end):
	"""For the closing file (books/closing_file.py)."""
	settings = frappe.get_single("DZ Core Settings")
	fiscal_year = get_fiscal_year(start, company=company)[0]
	return figures_table(
		year_figures(company, fiscal_year, settings.tax_regime if settings.company == company else None)
	)


def ifu_remark(fiscal_year):
	return _("IFU de l'exercice {0}").format(fiscal_year)


@frappe.whitelist()
def book_ifu(company, fiscal_year):
	"""Dr 6428 / Cr 4477 for the year's IFU not booked yet. Returns the entry."""
	from dz_core.closing import check_company, closing_key, lock_company

	frappe.has_permission("Journal Entry", "create", throw=True)
	check_company(company)
	lock_company(company)  # two clicks would both see nothing booked yet
	settings = frappe.get_single("DZ Core Settings")
	f = year_figures(company, fiscal_year, settings.tax_regime if settings.company == company else None)
	amount = flt(f.due - f.booked, 2)
	if amount <= 0:
		frappe.throw(_("L'IFU de l'exercice est déjà comptabilisé."))
	accounts = {
		number: frappe.db.get_value("Account", {"company": company, "account_number": number, "is_group": 0})
		for number in (CHARGE, PAYABLE)
	}
	cost_center = frappe.get_cached_value("Company", company, "cost_center")
	entry = frappe.get_doc(
		{
			"doctype": "Journal Entry",
			"company": company,
			"posting_date": min(f.end, getdate(today())),
			"user_remark": ifu_remark(fiscal_year),
			"dz_closing_key": closing_key("ifu", fiscal_year=fiscal_year),
			"accounts": [
				{
					"account": accounts[CHARGE],
					"debit_in_account_currency": amount,
					"cost_center": cost_center,
				},
				{"account": accounts[PAYABLE], "credit_in_account_currency": amount},
			],
		}
	).insert()
	entry.submit()
	return entry.name
