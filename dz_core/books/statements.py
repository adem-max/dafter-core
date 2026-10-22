"""The SCF statements: compte de résultat par nature and bilan (SCF advice Q20;
DECISIONS.md, "Compliance").

ERPNext 16's Financial Report Templates (report "Custom Financial
Statement") lay out a statement as rows: an account row sums the accounts its
filter selects, a formula row combines rows by their codes. The two SCF
statements are written here as data and made, or brought up to date, by
setup_statements() (apply_scf_setup), so they follow the code and are never
edited by hand.

Signs: an account row is debit minus credit; reverse_sign turns income,
liabilities and equity positive, so formulas read like the paper model
(valeur ajoutée = production - consommation).

Every account lands in exactly one row: ledgers without a number, or with a
number no row names, show in "non classés" rows (hidden when empty), so the
net result is always classes 7 - 6 and actif always equals passif. The bilan
classifies by account, not by the sign of its balance (the engine cannot split
an account): a supplier with a debit balance stays with the suppliers until
the month-end reclassification to 4097 (closing.py). The titles say "projet"
until an accountant has validated the layout.
"""

import json

import frappe
from frappe.utils import flt

INCOME_STATEMENT = "Compte de résultat SCF (projet)"
BALANCE_SHEET = "Bilan SCF (projet)"
MOVEMENT, CLOSING = "Period Movement (Debits - Credits)", "Closing Balance"


def number_filter(*prefixes, roots=None, exclude=()):
	"""The JSON filter of an account row: numbers starting with a prefix,
	optionally of these root types, none starting with an excluded prefix."""
	conditions = [{"or": [["account_number", "like", f"{prefix}%"] for prefix in prefixes]}]
	if roots:
		conditions.append(["root_type", "in", list(roots)])
	conditions += [["account_number", "not like", f"{prefix}%"] for prefix in exclude]
	return json.dumps({"and": conditions})


def unnumbered(*roots):
	return json.dumps({"and": [["account_number", "is", "not set"], ["root_type", "in", list(roots)]]})


def of_roots(*roots):
	return json.dumps(["root_type", "in", list(roots)])


def accounts(code, label, account_filter, reverse=0, hidden=0, hide_empty=0, indent=1):
	return {
		"reference_code": code,
		"display_name": label,
		"data_source": "Account Data",
		"calculation_formula": account_filter,
		"reverse_sign": reverse,
		"hidden_calculation": hidden,
		"hide_when_empty": hide_empty,
		"indentation_level": indent,
		"advanced_filtering": 1,
	}


def total(code, label, formula, bold=1, indent=0, hide_empty=0, hidden=0):
	return {
		"reference_code": code,
		"display_name": label,
		"data_source": "Calculated Amount",
		"calculation_formula": formula,
		"bold_text": bold,
		"indentation_level": indent,
		"hide_when_empty": hide_empty,
		"hidden_calculation": hidden,
	}


def blank(label=""):
	return {"data_source": "Blank Line", "display_name": label, "bold_text": 1 if label else 0}


# --------------------------------------------- compte de résultat par nature

INCOME_ROWS = {  # code: (label, prefixes)
	"R70": ("Ventes et produits annexes", ("70",)),
	"R72": ("Variation stocks produits finis et en cours", ("72",)),
	"R73": ("Production immobilisée", ("73",)),
	"R74": ("Subventions d'exploitation", ("74",)),
	"R75": ("Autres produits opérationnels", ("75",)),
	"R78": ("Reprises sur pertes de valeur et provisions", ("78",)),
	"R76": ("Produits financiers", ("76",)),
	"R77": ("Éléments extraordinaires (produits)", ("77",)),
}
EXPENSE_ROWS = {
	"C60": ("Achats consommés", ("60",)),
	"C61": ("Services extérieurs et autres consommations", ("61", "62")),
	"C63": ("Charges de personnel", ("63",)),
	"C64": ("Impôts, taxes et versements assimilés", ("64",)),
	"C65": ("Autres charges opérationnelles", ("65",)),
	"C68": ("Dotations aux amortissements, provisions et pertes de valeur", ("68",)),
	"C66": ("Charges financières", ("66",)),
	"C69": ("Impôts exigibles sur résultats ordinaires", ("69",)),  # less 692 / 693, below
	"C692": ("Impôts différés (variations) sur résultats ordinaires", ("692", "693")),
	"C67": ("Éléments extraordinaires (charges)", ("67",)),
}


def income_row(code):
	label, prefixes = INCOME_ROWS[code]
	return accounts(code, label, number_filter(*prefixes, roots=["Income"]), reverse=1)


def expense_row(code, exclude=()):
	label, prefixes = EXPENSE_ROWS[code]
	return accounts(code, label, number_filter(*prefixes, roots=["Expense"], exclude=exclude))


def income_statement_rows():
	listed_income = " + ".join(INCOME_ROWS)
	listed_expense = " + ".join(EXPENSE_ROWS)
	return [
		accounts("ALLINC", "Tous les produits", of_roots("Income"), reverse=1, hidden=1),
		accounts("ALLEXP", "Toutes les charges", of_roots("Expense"), hidden=1),
		income_row("R70"),
		income_row("R72"),
		income_row("R73"),
		income_row("R74"),
		total("PROD", "I - Production de l'exercice", "R70 + R72 + R73 + R74"),
		expense_row("C60"),
		expense_row("C61"),
		total("CONS", "II - Consommation de l'exercice", "C60 + C61"),
		total("VA", "III - Valeur ajoutée d'exploitation (I - II)", "PROD - CONS"),
		expense_row("C63"),
		expense_row("C64"),
		total("EBE", "IV - Excédent brut d'exploitation", "VA - C63 - C64"),
		income_row("R75"),
		expense_row("C65"),
		expense_row("C68"),
		income_row("R78"),
		total("RO", "V - Résultat opérationnel", "EBE + R75 - C65 - C68 + R78"),
		income_row("R76"),
		expense_row("C66"),
		total("RF", "VI - Résultat financier", "R76 - C66"),
		total("RAI", "VII - Résultat ordinaire avant impôts (V + VI)", "RO + RF"),
		expense_row("C69", exclude=("692", "693")),
		expense_row("C692"),
		total("RX", "Produits non classés", f"ALLINC - ({listed_income})", bold=0, indent=1, hide_empty=1),
		total("CX", "Charges non classées", f"ALLEXP - ({listed_expense})", bold=0, indent=1, hide_empty=1),
		total("TPAO", "Total des produits des activités ordinaires", "PROD + R75 + R78 + R76 + RX"),
		total(
			"TCAO",
			"Total des charges des activités ordinaires",
			"CONS + C63 + C64 + C65 + C68 + C66 + C69 + C692 + CX",
		),
		total("RNAO", "VIII - Résultat net des activités ordinaires", "TPAO - TCAO"),
		income_row("R77"),
		expense_row("C67"),
		total("REXT", "IX - Résultat extraordinaire", "R77 - C67"),
		blank(),
		total("RNET", "X - Résultat net de l'exercice", "RNAO + REXT"),
	]


# ----------------------------------------------------------------- bilan

ASSET, LIABILITY, EQUITY = "Asset", "Liability", "Equity"
PL = ("Income", "Expense")


def asset(code, label, *prefixes, exclude=(), roots=None):
	return accounts(code, label, number_filter(*prefixes, roots=roots, exclude=exclude), hide_empty=1)


def liability(code, label, *prefixes, exclude=(), roots=None):
	return accounts(
		code, label, number_filter(*prefixes, roots=roots, exclude=exclude), reverse=1, hide_empty=1
	)


def balance_sheet_rows():
	return [
		blank("ACTIF"),
		asset("A20", "Immobilisations incorporelles", "20", "280", "290"),
		asset("A21", "Immobilisations corporelles", "21", "281", "291"),
		asset("A22", "Immobilisations en concession", "22", "282", "292"),
		asset("A23", "Immobilisations en cours", "23", "293"),
		asset("A26", "Immobilisations financières", "26", "27", "294", "296", "297", "298"),
		asset("A133", "Impôts différés actif", "133"),
		total("ANC", "Total actif non courant", "A20 + A21 + A22 + A23 + A26 + A133"),
		asset("A3", "Stocks et encours", "3", roots=[ASSET]),
		asset("A41", "Clients", "41", "491", roots=[ASSET]),
		asset("A44", "Impôts et assimilés", "44", roots=[ASSET]),
		asset("A4X", "Autres débiteurs", "4", roots=[ASSET], exclude=("41", "44", "491")),
		asset("A5", "Trésorerie", "5", roots=[ASSET], exclude=("519",)),
		accounts("AX", "Autres actifs (non classés)", unnumbered(ASSET), hide_empty=1),
		total("AC", "Total actif courant", "A3 + A41 + A44 + A4X + A5 + AX"),
		total("TA", "TOTAL GÉNÉRAL ACTIF", "ANC + AC"),
		blank(),
		blank("PASSIF"),
		liability("P101", "Capital émis", "101", "108", "109"),
		liability("P104", "Primes et réserves", "103", "104", "106"),
		liability("P105", "Écarts de réévaluation et d'équivalence", "105", "107"),
		liability("P12", "Résultat net (exercices clôturés)", "12"),
		accounts("PRES", "Résultat de l'exercice en cours", of_roots(*PL), reverse=1),
		liability("P11", "Report à nouveau", "11"),
		accounts("PEX", "Autres capitaux propres (non classés)", unnumbered(EQUITY), reverse=1, hide_empty=1),
		total("CP", "Total capitaux propres", "P101 + P104 + P105 + P12 + PRES + P11 + PEX"),
		liability("P16", "Emprunts et dettes financières", "16", "17"),
		liability("P134", "Impôts (différés et provisionnés)", "134"),
		liability("P18", "Autres dettes non courantes", "18", "229"),
		liability(
			"P15", "Provisions et produits constatés d'avance", "13", "14", "15", exclude=("133", "134")
		),
		total("PNC", "Total passifs non courants", "P16 + P134 + P18 + P15"),
		liability("P40", "Fournisseurs et comptes rattachés", "40", roots=[LIABILITY]),
		liability("P44", "Impôts", "44", roots=[LIABILITY]),
		liability("P4X", "Autres dettes", "4", roots=[LIABILITY], exclude=("40", "44")),
		liability("P519", "Trésorerie passif", "519"),
		accounts("PX", "Autres passifs (non classés)", unnumbered(LIABILITY), reverse=1, hide_empty=1),
		total("PC", "Total passifs courants", "P40 + P44 + P4X + P519 + PX"),
		total("TP", "TOTAL GÉNÉRAL PASSIF", "CP + PNC + PC"),
	]


TEMPLATES = {
	INCOME_STATEMENT: ("Profit and Loss Statement", MOVEMENT, income_statement_rows),
	BALANCE_SHEET: ("Balance Sheet", CLOSING, balance_sheet_rows),
}


def setup_statements():
	"""Make the two templates, or rewrite their rows to match this file."""
	for name, (report_type, balance_type, make_rows) in TEMPLATES.items():
		rows = []
		for row in make_rows():
			if row.get("data_source") == "Account Data":
				row["balance_type"] = balance_type
			rows.append(row)
		doc = (
			frappe.get_doc("Financial Report Template", name)
			if frappe.db.exists("Financial Report Template", name)
			else frappe.new_doc("Financial Report Template")
		)
		doc.template_name = name
		doc.report_type = report_type
		doc.set("rows", rows)
		doc.flags.ignore_permissions = True
		doc.save()


def statement(company, template, start, end):
	"""(columns, rows) of a template over a date range, from ERPNext's engine."""
	from erpnext.accounts.doctype.financial_report_template.financial_report_engine import (
		FinancialReportEngine,
	)

	result = FinancialReportEngine().execute(
		frappe._dict(
			company=company,
			report_template=template,
			filter_based_on="Date Range",
			period_start_date=start,
			period_end_date=end,
			periodicity="Yearly",
		)
	)
	return result[0], result[1]


def amounts(company, template, start, end):
	"""{reference code: amount} of a statement over one period."""
	_columns, rows = statement(company, template, start, end)
	codes = {row["display_name"]: row.get("reference_code") for row in TEMPLATES[template][2]()}
	result = {}
	for row in rows:
		code = codes.get(row.get("account"))
		if code and not row.get("is_blank_line"):
			result[code] = flt(row.get(row["_segment_info"]["period_keys"][-1]))
	return result
