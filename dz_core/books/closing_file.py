"""The accountant's closing file, "Dossier de clôture" (SCF advice Q20).

One Excel workbook, one tab per table: the checks, balance générale, grand
livre, journal centralisateur, aged customer and supplier balances, stock
statement, fixed-asset register, TVA per month (régime réel) or the IFU
figures (IFU, auto-entrepreneur), compte de résultat and bilan. With it the
statements and the balance in PDF, and the entry export. All kept on a DZ
Archive with their SHA-256.

Refused while a check of the year end is not OK (books/year_end.py), as the
advice asks; draft=1 makes it anyway, marked "BROUILLON" on every tab and
page, for a first look by the accountant.
"""

import frappe
from frappe import _

from dz_core.books import tables
from dz_core.books.archive import CLOSING_FILE, keep
from dz_core.books.export import entry_files, entry_rows
from dz_core.books.statements import BALANCE_SHEET, INCOME_STATEMENT
from dz_core.books.year_end import NOT_FOR_THE_FILE, failing, refuse_if, year_bounds, year_checks
from dz_core.dz_core.doctype.dz_core_settings.dz_core_settings import REEL

DRAFT = "BROUILLON : des contrôles de clôture ne sont pas au vert"


def regime(company):
	settings = frappe.get_single("DZ Core Settings")
	return settings.tax_regime if settings.company == company else None


def checks_table(rows):
	return tables.table(
		_("Contrôles"),
		[
			(_("Contrôle"), tables.TEXT),
			(_("Montant"), tables.AMOUNT),
			(_("État"), tables.TEXT),
			(_("À faire"), tables.TEXT),
		],
		[[r["check"], r["amount"], r["status"], r["todo"]] for r in rows],
	)


def tax_tables(company, start, end):
	"""TVA per month on the régime réel; the IFU figures otherwise (Aide G12)."""
	from dz_core.books.ifu import ifu_table

	if regime(company) == REEL:
		return [tables.tva_by_month(company, start, end)]
	return [ifu_table(company, start, end)]


@frappe.whitelist()
def make_closing_file(company, fiscal_year, draft=0):
	"""Returns the DZ Archive's name."""
	frappe.has_permission("DZ Archive", "read", throw=True)
	frappe.has_permission("GL Entry", "read", throw=True)
	draft = int(draft or 0)
	start, end = year_bounds(fiscal_year)
	rows = year_checks(company, fiscal_year)
	problems = failing(rows, except_codes=NOT_FOR_THE_FILE)
	if not draft:
		refuse_if(problems, _("Dossier de clôture refusé"))
	banner = _(DRAFT) if problems else None

	entries = entry_rows(company, start, end)
	balance = tables.trial_balance(company, start, end)
	statements = [
		tables.statement_table(company, INCOME_STATEMENT, start, end),
		tables.statement_table(company, BALANCE_SHEET, start, end),
	]
	workbook = [
		checks_table(rows),
		balance,
		tables.general_ledger(company, start, end, entries),
		tables.centralising_journal(company, start, end, entries),
		tables.aged_balances(company, end, "Customer"),
		tables.aged_balances(company, end, "Supplier"),
		tables.stock_statement(company, end),
		tables.asset_register(company, end),
		*tax_tables(company, start, end),
		*statements,
	]
	heading = _("Dossier de clôture - {0} - exercice {1}").format(company, fiscal_year)
	files = [
		(
			f"dossier-cloture-{fiscal_year}.xlsx",
			tables.to_xlsx(workbook, banner),
			_("Dossier de clôture (Excel)"),
		),
		(
			f"etats-{fiscal_year}.pdf",
			tables.to_pdf([*statements, balance], heading, banner),
			_("États financiers SCF et balance"),
		),
		*entry_files(company, start, end, entries),
	]
	archive = keep(
		company, CLOSING_FILE, files, start, end, fiscal_year=fiscal_year, draft=1 if problems else 0
	)
	return archive.name
