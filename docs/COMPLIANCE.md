# Compliance: decree 09-110, the 2027 software rules and the accountant's hand-off

What Daftar does so a client's computerised books hold up in an audit, what it
does not do yet, and the routine that keeps them clean. From the SCF advice of
21 October 2026 (section Q6, Q13, Q18 to Q20) and release 0.4.0.

The French texts for clients are next to this file:
[ENGAGEMENT-EDITEUR.md](ENGAGEMENT-EDITEUR.md) (draft publisher's commitment)
and [MANUEL-PROCEDURES.md](MANUEL-PROCEDURES.md) (procedures manual).

## The rules

- **Decree 09-110** (computerised accounting): validated entries never change
  (art. 13), journals and monthly summaries (art. 12), automatic
  carry-forward (art. 14), an entry export (art. 15), users and rights (art.
  17), who did what, from where, when (art. 18), archiving, backups and
  restore (arts. 19 to 21), documentation and the vendor's commitment (arts.
  7 to 9).
- **LF 2026** (from 1 January 2027): the publisher gives each client a signed
  commitment (CPF art. 20 ter) and hands the tax administration codes, data
  and documentation on request (CPF art. 51 sexies). The models are left to
  arrêtés not published as of October 2026.
- **Retention** (CPF art. 64): 10 years for books, accounting and supporting
  documents; 6 years for other documents and the computerised data.

## Decree 09-110, article by article

| Article | ERPNext | Daftar |
| --- | --- | --- |
| 13, no change after validation | Immutable ledger: a cancel keeps the original lines and adds reversals dated the cancel day | Immutable ledger on, ledger deletion off (0.3.0); no Delete right on the documents that post to the ledgers, drafts included (the audited list in hooks.py, and dz_cod's Versements), taken away again after every migrate; no "Delete Transactions" (0.3.0); only the Administrator can still delete, and the deletion is audited; "Clôture du mois" freezes each month, and the freeze date never moves back from Daftar (the Company form can, audited); "Exercice comptable" closes and freezes the year |
| 12, journals and monthly summaries | One general ledger, no journals | Each line's journal (VE, AC, CA, BQ, ST, OD, AN) computed from its voucher (`books/journals.py`); the centralising journal per journal and month (`books/tables.py`) |
| 14, carry-forward | Balance-sheet balances roll on | The entry export starts a fiscal year with "AN" lines: balances of classes 1 to 5, and earlier results not yet closed on 120 / 129 |
| 15, export | Nothing usable as is | Report "Export des écritures": FEC layout plus the user, cancelled originals and their reversals included; text and Excel files kept with their SHA-256 (`books/export.py`) |
| 17, users and rights | Users, roles | One user per person (procedures manual); no shared logins |
| 18, author, workstation, date, operation | Version keeps user and time | DZ Audit Log: user, IP address and browser on every validation, cancellation, change after validation and deletion, and on each change of the freeze date (`books/audit.py`); kept, never pruned |
| 19 to 21, archiving, backups, restore | Site backups | Yearly archive of a frozen year: entry export, books, SCF statements, audit trail, with a `sha256sum` register (DZ Archive, `books/archive.py`); daily off-site backup and a restore test (`scripts/`, DEPLOY.md) |
| 7 to 9, documentation, commitment | | This file, the procedures manual, the draft commitment |

## What is missing, said plainly

- **The official export format and the commitment model**: arrêtés not
  published. The export uses the French FEC layout; the commitment is a draft
  ([ENGAGEMENT-EDITEUR.md](ENGAGEMENT-EDITEUR.md)) to revise when they are.
- **Who signs for open-source software**: Daftar's reading is that it does, as
  the one who configures and distributes the client sites; a written DGI
  answer is asked (advice section 9). Daftar must be a registered legal
  entity or trader before signing.
- **Certification** (CTCA art. 51 bis, TVA-liable clients): no accredited
  body known yet.
- **Workstation**: the browser string and IP address are what a web
  application can know; no device inventory.
- **SCF statements**: drafts until an accountant validates the layout (titles
  say "projet").

## The routine

Monthly (report "Clôture du mois"): 6589, 4781, 476 and 479 at zero; 4081
debit balances reclassified to 4097; class 72 equal to the change in classes 33
and 35; each courier's 4671n against the parcels it owes for (dz_cod);
the regime's returns (G50 by the 20th; G12 by 30 June; G12 bis by 20
January); then "Geler le mois". On the régime réel, "Aide G50": settlement
entry, the stamp duty, the TVA given back on losses and gifts. A month left
unsettled is taken into the next settlement and shown apart ("Clôture du
mois" flags it): the accountant says how to declare it.

Yearly (report "Exercice comptable"): the same checks at the year end, the
stock accounts against the stock ledger, then:

1. "Clôturer l'exercice": ERPNext's Stock Closing Entry (it runs in the
   background: come back a few minutes later), then the Period Closing
   Voucher into 120 (profit) or 129 (loss);
2. "Geler l'exercice";
3. "Dossier de clôture" for the accountant (refused while a check fails;
   "brouillon" makes it anyway, marked);
4. "Archive annuelle" (needs the frozen year), kept 10 years: never prune
   the site's private files.

The entry export, the closing file and the archive are made by an Accounts
Manager (or System Manager) only, since an archive is never deleted; asked
again while nothing moved in the books, they give back the last one.

After the owners' decision, a journal entry allocates 120 / 129 (to 110 /
119, 106x, 457, or 1018 with the balance of 108 for a sole trader).

## Opening a client's books

1. The import workbook (README): parties, items, then the opening stock count
   on the opening date (against 479).
2. `dz_core.imports.opening`: the accountant's closing trial balance and the
   open invoices; a dry run lists every problem; then the open invoices and one
   "Écritures d'à-nouveaux" entry, and 479 must end at zero. Once done it is
   refused: to redo it, cancel the opening documents first.
3. Existing fixed assets by hand: Asset, "Is Existing Asset", with the
   opening accumulated depreciation (their balances are in step 2).
