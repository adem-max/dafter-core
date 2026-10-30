# Decisions

Why dz_core is built the way it is. Same rules as dz_cod's DECISIONS.md.

## Platform

- **An app, not a fork.** ERPNext is never edited. Everything is custom
  fields, settings, setup code and print formats in this app, so ERPNext
  updates stay a normal `bench update`.
- **Two apps, two repos.** dz_cod changes how every Sales Order behaves
  (confirmation workflow, courier fields, validation hooks). A producer who
  sells wholesale by phone must not get that, so it stays a separate app
  installed only for online sellers. dz_cod declares
  `required_apps = ["erpnext", "dz_core"]`.
- **Technical names stay neutral.** The apps are `dz_core` and `dz_cod`
  whatever the brand becomes. Renaming a Frappe app later means renaming a
  Python package and its module on every live site; the brand lives in the
  repo names, `app_title`, logos and the website.
- **Brand: Sijil (company), Daftar (the ERP)** (22 October 2026). Sijil (سجل,
  "register") is the company and umbrella brand, free of any one country, for
  every SaaS it builds; Daftar is this ERP's product name ("Daftar by Sijil").
  "Daftar" alone is used by a real estate agency, "Daftar DZ" ties the brand
  to Algeria, "Daftar ERP" ties it to one product. Note only: nothing renamed
  yet (app names stay, see above).
- **Logos** (23 October 2026, chosen from three options each). Sijil: lowercase
  `sijil` in Inter Bold whose three dots are green squares (#006233), the icon
  is the ı ȷ pair on an ink tile. Daftar: a spiral school notebook, white line
  art on a teal tile (#0f5c63), the same tile family as the Atelier and COD
  marks; "Daftar by Sijil" is its own lockup. The SVGs are in
  `dz_core/public/images/brand/` (text as outlines, no font needed); rules and
  sizes in the Daftar design system. Not wired in yet: Atelier stays the app's
  icon.

- **The split with dz_cod is finished** (19 October 2026, `docs/SPLIT.md`).
  Rule: what every client needs goes here, what only an online seller needs
  goes in dz_cod. dz_core never imports dz_cod; when it needs something from
  an app on top, it offers a hook. Done ahead of ROADMAP Phase 4 on purpose:
  moving a doctype between apps costs nothing before a client site is live
  and a migration patch per site after.

## Setup

- **Setup is code, not fixtures.** `sectors.py` and `tax.py` create what is
  missing and never overwrite what exists, like dz_cod's setup. Fixtures
  would export whole records and overwrite a client's changes on every
  migrate.
- **Per-client differences live in DZ Core Settings** (sector, tax regime,
  warehouses, invoice note), never in `if client == ...` code.
- **Three warehouses for every producer**: Matières premières (added),
  Travaux en cours and Produits finis (made by ERPNext's French setup wizard,
  reused). Work orders default to Travaux en cours and Produits finis.
- **Items get their warehouse from their group** (Item Group defaults), not
  from the company default: raw materials, fabric and packaging land in
  Matières premières, finished products in Produits finis. The wizard's
  "Magasins" stays the company default for anything else.
- **ERPNext v16 moved the default warehouses to the Company** (section
  "Warehouse Defaults"). Stock Settings and Manufacturing Settings no longer
  have the WIP and finished-goods ones. The general `default_warehouse`
  followed in ERPNext 16.51; up to 16.50 it is still in Stock Settings, so
  dz_cod's demo loader writes whichever exists (19 October 2026).
- **An opening-balance account is added** (479 "Ouverture temporaire", type
  Temporary, under class 47 since 0.3.0): the Algerian chart has none and the
  opening stock import needs one.
- **Algerian chart of accounts**: "Algerie - Plan Comptable General 2 avec
  code", shipped with ERPNext, same as dz_cod.
- **Facture DZ and Bon de livraison DZ are the default print formats**, set
  by `prepare()` (19 October 2026). The test is "did the client choose one in
  Customize Form" (a Property Setter not made by the system), not "is there a
  default": ERPNext 16 ships its own ("Sales Invoice Modern with Images").
- **The wizard's English item groups are deleted** (Products, Raw Material,
  Sub Assemblies, Consumable; 19 October 2026, Phase 1 option A): they sat
  next to the sector's French groups and confused clients. A group still used
  by an item or a setting is kept. "Services" stays: producers bill services,
  and the word is the same in French.
- **Cancelled invoices stay printable** (Print Settings "allow print for
  cancelled", set by `prepare()`, 19 October 2026): ERPNext refuses by
  default, which made Facture DZ's FACTURE ANNULÉE mark unreachable. Found
  walking the demo script.
- **Algerian addresses print in French, without the country**: ERPNext's
  wizard makes an "Algeria" Address Template with Frappe's stock text, which
  ends with "Algeria" in English on every invoice. `prepare()` replaces it
  (postcode and city, then the wilaya), unless the client edited it.
- **Food sector counts trays** ("Barquette"): date paste is sold by the tray,
  and "Nos" on an invoice means nothing to a buyer.
- **Clothing counts thread by the cone, in fractions** ("Cône", 19 October
  2026): a T-shirt uses about 0.02 of a cone, and ERPNext refuses a fraction
  of a whole-number unit such as Nos in a BOM or a stock entry. Shipping
  cartons stay whole and out of the garment recipes: they are used when
  shipping, not per piece.

## Places and phones (moved from dz_cod, 19 October 2026)

- **The 69 wilayas are a dz_core doctype (DZ Wilaya)**: every client's
  customers live somewhere in Algeria, and imports need a list to check
  against. dz_cod's reasons for a doctype still hold (ERPNext has no list of
  Algerian provinces; Territory is the sales tree). The record name stays
  "16 - Alger" and the 2026 wilayas keep their parent; see dz_cod's
  DECISIONS.md for the sources, which still need checking against the
  Journal officiel.
- **Delivery rates are dz_cod custom fields on DZ Wilaya**, with the field
  names they had as standard fields, so migrating an existing site moves no
  data. A producer without dz_cod sees only code, name and parent.
- **Customer phone and wilaya are dz_core fields** (`dz_phone`, `dz_wilaya`,
  section "Coordonnées"); commune and address stay dz_cod's delivery
  snapshot. The import workbook fills them, so imported customers are ready
  for COD orders, and it refuses a wilaya it cannot find ("16", "Alger",
  "16 - Alger", accents and case ignored). ERPNext's own `mobile_no` and the
  Address are still filled as before.
- **Phones are normalized on every Customer save** (`dz_core/phone.py`, rule
  in dz_cod's DECISIONS.md): `+213` and `00213` become `0`, unknown formats
  are kept as typed.
- **The restore check is extended by hooks**, not copied: an app adds
  `dz_restore_check_counted` and `dz_restore_check_last` lists to its
  hooks.py, and `restore_test.sh` compares those too.
- **Feature switches live in dz_core** (moved 19 October 2026, the same
  day the split closed): the hub manages every client, most of whom never
  get dz_cod, so it needs one place to ask "what can this client switch
  on". dz_core owns the mechanism (`dz_core/features.py`: the site's list in
  site_config key `dz_features`, `is_enabled`, `@requires_feature`, hiding
  reports and print formats, the `dz-features` command, `frappe.boot.dz_features`).
  Each app declares its own features with a `dz_features` hook pointing at
  a dict; dz_core has none of its own yet. The old key `dz_cod_features` is
  still read and moved on migrate; `dz-cod-features` stays as an alias.
- **No feature list means the base only** (20 October 2026): it meant
  "everything", so a client site made by hand, or restored on a new server
  without its site_config, had every paid option. Demo and test sites say
  `"all"`; a patch wrote it on the sites made before, and new sites skip it
  (Frappe marks an app's patches done on install). A restore copies the list
  from the backup's site_config (docs/DEPLOY.md, section 10).
- **The catalogue is read with plain imports for the hub**
  (`bench_catalog`): the hub site does not install the client apps, and
  `frappe.get_hooks(app_name=...)` and `frappe.get_attr` both refuse an app
  that is not installed on the current site.

## Tax

- **IFU is the default.** Most very small producers pay the IFU (individuals
  up to 8 million DA turnover) and charge no TVA, so the 19 % template made
  by the setup wizard is not applied by default for them. This replaced
  dz_cod's own "remove the default 19 % VAT" step.
- **TVA per rate, on its own ledgers** (21 October 2026, SCF advice Q5).
  The setup wizard's templates booked collected and deductible TVA in one
  account ("TVA 19%"), which the SCF does not allow. `setup/tax.py` makes a
  sales template "TVA ventes" (rows 445711 for 19 %, 445712 for 9 %) and a
  purchase template "TVA achats" (44566 stocks and services, 44562 fixed
  assets), all at rate 0: the rate comes from the item's Item Tax Template
  ("TVA 19 %", "TVA 9 %", "Exonéré", "TVA 19 % immobilisations"), and every
  item group carries "TVA 19 %". The 2026 codes put all our products at 19 %
  (honey, jams, date paste, cosmetics, t-shirts, fabric); fresh dates are at
  9 %, locally grown fresh fruit exempt until 31 Dec 2026 (LF 2024 art. 65,
  LF 2026 art. 112). Facture DZ prints only the rates the invoice uses.
  Accounts Settings "Add Taxes from Item Tax Template" is switched off: on,
  ERPNext adds the item's template accounts as tax rows even on a document
  with no template, so an IFU invoice got TVA (found by the tests).
- **Régime réel**: "TVA ventes" and "TVA achats" are the defaults. **IFU**:
  no default template; an IFU invoice may not show TVA (CTCA art. 64).
- **Aide G50** (report, `closing.py` `tva_figures`): taxable turnover per
  rate, TVA collected, TVA deductible, the credit carried from the month
  before, and the amount to pay on the G50 (44551) or the new credit (44568);
  a button posts the settlement entry, once per month. A help, not the
  declaration.
- **Auto-entrepreneur** (22 October 2026, 0.4.0): a third regime, no TVA
  like the IFU (CTCA art. 64), note "Auto-entrepreneur : TVA non facturée.";
  turnover counts at delivery ("réalisé", CIDTA art. 282 quater), the
  payment date shows in the receipts register for the reconciliation.
- **Stamp duty on cash receipts, built and off** (22 October 2026,
  `stamp.py`): the circular 14/MF/DGI/LF.2025 scale (nothing up to 300 DA,
  then per 100 DA band 1 / 1.5 / 2 DA by the bracket of the whole amount, at
  least 5 DA), on draft sales invoices, per payment mode of DZ Core Settings:
  added to the invoice (445751, outside the TVA base) or at the seller's
  charge (445751 and 6457, total unchanged). Cheques and transfers whose
  references are on the invoice are exempt (art. 258); card and BaridiMob
  too (art. 258 quinquies). Cash-on-delivery can only be at the seller's
  charge (the courier collects a fixed amount) and is not in the default
  table: whether it is due there is the open question for the tax office.
  The whole switch stays off until the client's accountant agrees; the food
  demo has it on. A later cash payment of an invoice without it only warns.
  Aide G50 shows the month's duty (line E2E12).
- **Registers and Aide G12** (`books/registers.py`, `books/ifu.py`): the
  sales and purchases registers, printed to copy into the numbered paper
  books (CPF art. 1: nothing allows keeping them only in software);
  turnover per month, goods and services (items of ERPNext's "Services"
  group), the IFU at 5 % / 12 % or 0.5 % for an auto-entrepreneur, written
  as constants to confirm with the accountant; a button books the IFU
  (6428 / 4477). "Clôture du mois" reminds the regime's next returns.
- **Warnings** (`tax_checks.py`): non-stock purchase lines above 60,000 DA
  HT a unit (CIDTA 141-3, equipment); purchases "Sans facture" (no TVA,
  totalled at the year end as likely non-deductible; supplier "Fournisseur
  divers sans facture"); supplier invoices above 1,000,000 DA TTC paid in
  cash (CTCA art. 30). On the régime réel, Material Issues for loss, theft,
  destruction or gifts give back their TVA (CTCA arts. 37-a, 41-5): Aide
  G50 posts the reversal once a month at each item's rate, an approximation
  (the item's cost times its rate) for the accountant to confirm; own
  products' reversal goes to 65888, not 7245, so class 72 stays equal to the
  stock change.
- **Still waiting for the tax office:** the stamp duty on cash-on-delivery,
  the exact IFU mention (`IFU_NOTE`, editable in DZ Core Settings), the IFU
  rates, the craft products at 9 %. The default accounts are below.

## Chart of accounts and default accounts (21 October 2026)

Source: the advice doc "Daftar: SCF default accounts and compliance advice
(ERPNext v16)" (claude.ai artifact FKLsv1yiQhp6H3F7MYirFm), written from
the SCF texts, the 2026 tax codes and a practitioner review. Applied by
`setup/scf.py` (prepare() on a new client, patch `scf_setup` on older sites,
the demo loaders). Its open questions stay for the expert-comptable and the
tax office (doc section 9).

- **ERPNext's setup wizard picks the wrong default accounts for the Algerian
  chart.** It takes the last account of each type: receivables in 4172,
  suppliers in 4213 (a salary account), the bank in 5176 "Société de bourse",
  stock in 3451 "Prestations de services". Daftar 0.2.0 replaced them;
  0.3.0 applies the advice in full.
- **Inventory accounts per item group, not per warehouse** (Company "Enable
  Item-wise Inventory Account"). A small workshop keeps fabric, trims and
  packaging in one room, and finished goods and resold goods at the same
  courier: per warehouse, one room means one account. ERPNext allows the
  switch only before the company's first stock entry, and then refuses an
  item whose group has no stock account (no company fallback, no
  inheritance from the parent group). So every group carries its accounts
  (`setup/item_groups.py`), a new group copies its parent's, and the import
  workbook refuses a group without accounts.

  | Kind of group | Stock | Cost of sales | Consumption / issue | Income |
  | --- | --- | --- | --- | --- |
  | Raw materials (Matières premières, Tissus) | 311 | 60111 | 60111 | 7081 |
  | Trims (Fournitures) | 317 | 60171 | 60171 | 7082 |
  | Packaging (Emballages) | 3261 | 60261 | 60261 | 7082 |
  | Own products (Produits finis) | 35511 | 7245 | 7245 | 7011 |
  | Resold goods (Marchandises) | 301 | 6001 | 6571 | 7001 |
  | Offcuts and rejects (Déchets et chutes) | 35831 | 7248 | 7248 | 7031 |
  | Purchased services (Services achetés > Loyer, Internet...) | none | none | 6132, 6264... | none |

- **Production is booked the SCF way** (checked 21 Oct 2026): with each
  line of a manufacture carrying its item group's expense account, ERPNext
  posts Dr 60111 / 60261 (materials consumed) against Cr 311 / 3261, and
  Dr 35511 against Cr 7245 (production stocked); a sale posts Dr 7245 /
  Cr 35511 (production destocked). A manufacture made from a Work Order gets
  the company's stock adjustment account on every line instead, and the lines
  cancel out (materials straight into finished goods, nothing in 60x or 72):
  `production.py` (Stock Entry validate) gives each line its group's account
  where ERPNext left that default. No monthly reclassification entry is
  needed. The demos absorb labour through 7245 (the advice: a client who
  absorbs labour points the operating cost there). Year-end control: class 72
  equals the change in classes 33 + 35 (report "Clôture du mois").
- **Company defaults** (`setup/accounts.py` COMPANY_ACCOUNTS): receivable
  4111, payable 40132, bank 5121, cash 5311, received not billed 4081,
  stock adjustment 6572, round-off 65881, round-off for opening 479, write-off
  65882, payment discount 668, exchange 666, disposal 6528, asset received not
  billed 4083, depreciation 6812, assets in progress 2328, advances 4191 /
  40913. **Cost of sales and service expense fall back to 6589 "Charges à
  reclasser"**, never to a real account: only an item without group accounts
  or an invoice / receipt difference lands there, and the monthly close
  empties it. A default that is not the wizard's pick or an earlier Daftar
  value was chosen by someone and is kept.
- **Chart changes** (`setup/chart.py`): about 35 accounts added (reserves
  106x, the owner's 108 and 1018, 110 / 119 and 120 / 129, machines 215,
  offcuts 35831, TVA per rate 445711 / 445712, stamp duty 445751, couriers'
  collections 4671x, unidentified receipts 4781, IFU 6428 / 4477, rents 6132 /
  6135, 6589, rounding and settlement gaps 65881 / 65882 / 75882, card
  settlements 51181); 11, 12, 5118, 6588 and 7588 become groups (only while
  they have no entry at all); "Ouverture temporaire" becomes 479 under a new
  class 47 liability group; 666 / 766 lose their "Round Off" type; TAP
  (6421, 6422, 4471, repealed by LF 2024) and the works and studies income
  lines are disabled.
- **Supplier groups** with their payable and advance accounts (stocks 40132,
  services 40162, public bodies 40161, foreign 40133 / 40163, fixed assets
  4042), **payment modes** (Cash 5311, Wire Transfer 5121, Cheque 5111,
  CCP / BaridiMob 5171, Credit Card 51181) and **asset categories** (215,
  2182, 2183, 2184 with 6812).
- **Settings**: moving average valuation (CMP); advances in their own
  accounts; immutable ledger on (cancelling posts a dated reversal, decree
  09-110 art. 13); ledger lines never deleted with a document; nobody may
  delete an accounting or stock document, drafts included (a deleted draft
  leaves a hole in the numbering), nor run "Delete Transactions".
- **Demos run without the immutable ledger**: a demo is wiped and replayed,
  and an immutable ledger would keep each wiped document's lines in its
  month and put their reversal on the day of the wipe. A demo built before
  21 Oct 2026 moves over with a full wipe (`demo/wipe.py`, full=1).
- **Still for the expert-comptable** (doc section 9): 7245 as the cost of
  own products; 4081 without class 38; 6571 / 6572 and 7571 / 7572 for count
  gaps; finished goods at material cost during the year (labour and overheads
  added at the year end, 35519); CMP or FIFO; offcuts at zero value; the
  courier accounts 4671x; the numbers of the owner's accounts (1018, 108);
  110 / 119 and 120 / 129; IFU in 6428 / 4477; the closing file's format.

## Monthly close (21 October 2026)

- **Report "Clôture du mois"** (`closing.py`, `closing_rows`): the checks
  before a month is frozen, OK or À voir with what to do. 6589 "Charges à
  reclasser", 4781 "Versements à identifier", 476 and the opening account
  479 must be empty; suppliers invoiced before their goods arrived (debit
  balances on 4081) are listed; class 72 must equal the change in classes
  33 + 35 since the start of the year (what posts to 479, the opening stock,
  left out). Other
  apps add checks through the hook `dz_closing_checks` (dz_cod: each
  courier's 4671n against the parcels it delivered and still owes for, and
  fees kept without an invoice).
- **Two actions**: reclassify the 4081 debit balances to 4097 at the month
  end, reversed on the 1st (once per month), and freeze the month (Company
  "Accounts Frozen Till Date").
- **No production reclassification entry**: each manufacture posts
  materials consumed (60x) and production stocked (72) itself (`production.py`).
- **Entries made once a period carry a key** (29 October 2026, review of
  27 October, 2.5): the TVA settlement, the 4081 reclassification and its
  reversal, the TVA given back on losses and the IFU entry are found by Journal
  Entry `dz_closing_key` (`tva:2026-10`, `ifu:2026`), no longer by their
  remark. The remark is translated (`_()`), so once translations exist a user
  in another language would not find the month's settlement and could settle
  it twice; and a remark typed by hand on any entry counted as the
  settlement. Each button also locks the Company row first, so two clicks run
  one after the other. Patch `closing_keys` gives older entries their key from
  their French remark.

## Compliance (22 October 2026)

From the SCF advice (Q6, Q13, Q18 to Q20), released as 0.4.0;
docs/COMPLIANCE.md maps decree 09-110 article by article.

- **Journals are computed, not stored** (`books/journals.py`): VE, AC, ST by
  voucher type, CA / BQ for payments and journal entries that move cash
  (53x) or a bank (51x, 52x, 54x), OD otherwise, AN for opening entries. A
  stored field would need a migration of every past line and could drift.
- **The entry export uses the French FEC layout** plus a user column: the
  Algerian specification (decree 09-110 art. 15, LF 2026) is left to an
  arrêté not published, and accounting software in Algeria imports FEC
  files. It exports `is_cancelled = 0` lines: under the immutable ledger
  that is the original and its reversal (a contre-passation). A fiscal
  year's first day gets virtual "AN" lines (art. 14).
- **Our own audit trail, DZ Audit Log**: ERPNext's Activity Log is pruned
  after 90 days and its Version log has no IP or workstation (art. 18).
- **The audit trail is a hash chain** (29 October 2026, review of 27
  October, 4.3; D3 as proposed): each row has its number in its company's
  chain, the previous row's hash and its own (SHA-256 of that and the row's
  content, time included), set when the row is written
  (`books/audit_chain.py`). `verify_chain` finds a row changed, removed or
  slipped in; "Exercice comptable" shows it, and an untouched chain is needed
  for the closing file. One chain per company (the demo wipe deletes a
  company's rows). **Limits:** someone with direct database access can
  recompute a whole chain, so the yearly archive keeps the chain's last hash
  at the year end (`chaine-audit-<year>.txt`, in the register kept
  off-site); writes are ordered by a lock on the Company row and a locking
  read of the tail, so audit rows of one company are written one after the
  other (two validations at the same moment wait for each other at that
  last step; a deadlock with another lock taken after it is possible, and
  MariaDB would then refuse one of the two). Concurrency is not tested with
  two real connections. Patch `chain_audit_log` chains older rows by date.
- **Archives are kept with SHA-256 hashes** (DZ Archive, `sha256sum`
  register): made only by code, never changed, never deleted, nor their
  files; the demo wipes alone forget them. Ten years (CPF art. 64) through
  the site's private files and a yearly off-site backup (DEPLOY section 9).
- **SCF statements as ERPNext 16 Financial Report Templates**, written as
  data in `books/statements.py` and rewritten on every migrate (never edited
  by hand). Every account lands in one row, so the net result equals
  classes 7 - 6 and actif equals passif; the bilan classifies by account,
  not by sign (the engine cannot split an account). The bilan's "Résultat
  de l'exercice en cours" counts only income and expenses after the last
  Period Closing Voucher, computed by Daftar (`result_not_closed`): the
  engine leaves out a closing voucher's reversal of classes 6 and 7 and
  keeps its 12x line, so a closed year would count twice (found on a real
  close, 22 October 2026). Titles say "projet" until an accountant
  validates them.
- **Year end in four buttons** (report "Exercice comptable"): close (ERPNext
  16 wants a completed Stock Closing Entry first, built in the background,
  then the Period Closing Voucher into 120 or 129 by sign), freeze, the
  accountant's closing file (refused while a check fails, or a marked
  draft), the yearly archive (frozen year only). The allocation of the
  result stays a journal entry after the owners' decision. A year is never
  closed on a test site: it would block posting in it. **After the close**
  (29 October 2026, review of 27 October, 1.1): the closing voucher empties
  classes 6 and 7 on the year-end date, so a figure of the year's own
  movements leaves it out (`closing.balance(exclude_closing=True)` for the
  class 72 check, the IFU booked): the 72 check turned "À voir" and refused
  the closing file, and the IFU booked read 0. Balances read from the very
  beginning keep it, or every closed year would count again. Tested with
  closing-voucher lines written in a rolled-back test, not a real voucher.
- **Opening from the trial balance** (`imports/opening.py`): open invoices
  through ERPNext's Opening Invoice Creation Tool's builder but inserted by
  us, all or nothing (the tool itself swallows errors), dated the opening
  day; stock from the import workbook's count; one "Écritures d'à-nouveaux"
  entry; 479 must end at zero or nothing is posted. Existing fixed assets
  are entered by hand. **Advances** (29 October 2026, review of 27 October,
  2.2): only the receivable and payable accounts invoices post to (the
  company's defaults, the accounts on parties and their groups) are compared
  with the open invoices. Others of those types, 4191 advances received and
  40913 advances paid, go to the à-nouveaux entry with the party named in the
  Balance sheet's optional "Tiers" column, one line per party: ERPNext refuses
  such a line without its party, and a workshop holding customers' deposits
  could not be opened before.
- **Every closing button checks the company and the ledger right** (29
  October 2026, review of 27 October, 1.3 and 2.6): `closing.check_company`
  (the user may read that Company, User Permissions respected) on the TVA,
  4081, IFU, year-end, export, archive and closing-file buttons, and
  `result_not_closed` (called by ERPNext's bilan, so reachable by URL) now
  wants GL Entry read: a production worker's login could read the year's
  result. `tests/test_endpoints.py` lists every whitelisted function, read
  from the source, and calls each as a portal user: a new endpoint fails the
  test until it is listed there.
- **The 2027 commitment is a draft** (docs/ENGAGEMENT-EDITEUR.md) that claims
  only what the software does, as the advice says; signed by Daftar once a
  registered entity, revised when the arrêté is published.

## Invoices

- **Legal mentions from decree 05-468**: seller's name, legal form, activity,
  address, RC (or auto-entrepreneur card), NIF, NIS, tax article, capital for
  companies; business buyer's RC, NIF, NIS, tax article; payment method and
  date; stamp and signature. Cancelled invoices print "FACTURE ANNULÉE"
  across the page. To be validated by an accountant before the first client.
- **The totals follow the arithmetic** (20 October 2026): with a discount,
  Total HT (what the lines add up to), Remise, Total HT après remise, then
  each tax after the discount, then TTC. It used to print the discounted HT
  and subtract the discount again under the taxes.
- **"Contre-remboursement" is a payment mode** (20 October 2026): dz_cod
  invoices an online order when it is delivered, paid to the courier.
- **A credit note prints as "FACTURE D'AVOIR"** with its original invoice,
  amounts and words positive ("Arrêté le présent avoir à la somme de…"):
  ERPNext stores it with negative amounts, which printed as a "FACTURE" of
  "moins … et moins cinquante centimes". The exact wording goes to the
  accountant with the rest.

## Import workbook

- **One Excel file per client, French headers, our own importer.** ERPNext's
  Data Import works one doctype at a time with English technical headers;
  a client cannot fill that. The importer checks everything first and creates
  nothing while any row has an error.
- **Never changes existing records.** Same code or name = skipped, so a file
  can be imported twice safely.
- **Clothing: one template item per model, one variant per size and colour,
  one BOM per model.** ERPNext uses the template's BOM for a variant that has
  none, so per-size BOMs are only needed for precise costing (paid extra).
- **Opening stock once per item and warehouse.** It can come in several
  files, but an item that already has stock in a warehouse is refused there:
  after go-live, corrections go through ERPNext's own Stock Reconciliation.
- **The opening count can be dated** (`opening_date`, 19 October 2026):
  a client counts on the 1st and sends the file on the 5th, and the demos
  start 13 weeks back. The batches of that count are made on that date too:
  ERPNext takes the oldest batch first, and an opening batch stamped with the
  import day looked newer than everything produced after it. A dated count is
  posted at 00:00 on its day (21 October 2026): posted at the clock time of
  the import, it came after anything entered earlier in that day's hours.
- **Clients carry NIS and tax article (AI) too** (19 October 2026): the
  buyer's mentions on a business invoice are RC, NIF, NIS and AI; the sheet
  had only the first two. A column added later is optional in the file: a
  file made from an older template still imports.
- **Variants are named in words** ("Chemise manches longues XL Bleu"):
  ERPNext names them with the attribute abbreviations ("…-XL-BLE"), which
  then print on the invoice. The item code keeps ERPNext's form.
- **A lot number belongs to one item** (20 October 2026): ERPNext names a
  batch by its number alone, so "L2026-10" on two jams passed the check and
  failed the import. The check now refuses a lot used by another item (in the
  file or on the site) and suggests adding the item code.
- **The check finds what ERPNext would refuse** (20 October 2026): a count
  without any cost, a recipe unit that nothing converts to the stock unit
  (ERPNext would count 1 for 1), text in a number column (it became 0), the
  same count twice, the same customer or supplier twice.
- **Opening stock is posted 100 lines at a time**: above 100 lines ERPNext
  submits a Stock Reconciliation in a background job, and the importer said
  "done" while it was still a draft.
- **Models and their stock come in two files** when the stock lists variants:
  the check of a file runs before anything is created, so a variant made by
  the "Modèles" sheet is unknown to the "Stock initial" sheet of the same
  file. Data first, then the opening count, which is also the natural order
  of an onboarding.

## Producer reports (20 October 2026)

- **Our own Script Reports, not ERPNext's**, for the questions a workshop
  asks every day: "Coût de revient", "À produire", "À acheter" (then
  "Valeur du stock", "Ventes par mois"). ERPNext has the data but spreads the
  answer over several reports in English vocabulary (BOM Stock Calculated,
  Stock Projected Qty, Stock Ledger). Report names carry no accents (they
  become Python folders); `translations/fr.csv` gives them their accents.
- **Cost per product prices materials at the last receipt by default**: the
  owner wants to know what a jar costs *now*, and a dearer sugar delivery must
  show at once ("Coût moyen en stock" is the other choice). ERPNext's own
  valuation (FIFO by batch) only moves when the old stock is used up.
- **Labour in the cost is what the manufacture entries of the last 90 days
  added per unit**, not BOM operations: workshops keep no job cards
  (DECISIONS, demos). A client who records no labour sees 0.
- **Reorder levels come from the import workbook** (two optional columns,
  "Seuil de réapprovisionnement" and "Quantité à commander"), in the
  warehouse the item's group stores it in. The demos use them too.
- **ERPNext's automatic material requests stay off** (Stock Settings, auto
  indent): they create documents every night that a small workshop does not
  expect. "À acheter" shows what to order; the owner orders.
- **"Valeur du stock" sums the Stock Ledger up to the date**, ERPNext's
  Stock Balance source, so the two totals are equal by construction.
- **"Ventes par mois" compares the last two full months**: set against a
  whole month, the current one always looked like a fall (−38 % on the food
  demo on 19 October).
- **"À produire" lists every ordered product**, with what stock and work
  orders already cover: a workshop that makes ahead sees its orders covered
  rather than an empty page.
- **The Atelier home page is built like dz_cod's COD page** (workspace,
  number cards, dashboard charts, sidebar and a Dock mounted on ERPNext's
  rail, all shipped as files and loaded by `bench migrate`), and `prepare()`
  makes it the landing page (`default_app = dz_core`). A site with dz_cod
  runs dz_cod's setup after, which makes COD the landing page; both menus
  stay on the rail.
  Frappe 16 only follows `default_app` for website users and the apps
  screen: after login it sends desk users to /desk. dz_core's hook
  `get_website_user_home_page` sends them to the default app's route
  instead (the user's own default app first), so COD on a dz_cod site.
- **The low stock alert is a chart, not just a number**: "À acheter" now
  returns a chart (stock against level, per material) and the home page shows
  it, so the materials under their level are named on the page.
- **Who sees what on the home page is Frappe's own rule**: a card or chart
  shows when the user can read its doctype or report. So "Valeur du stock" is
  given only to the roles that can read the Stock Ledger (Stock User,
  Accounts Manager), and the "À acheter" counter is keyed on Material Request
  (buyers, stock, production): otherwise the sales login got an error popup
  and a counter stuck on loading.
- **On a site with dz_cod, an order is COD or a direct sale** (20 October
  2026, dz_cod's sales channel): wholesale and shop orders are direct sales,
  skip the COD checks (phone, wilaya, address) and follow ERPNext's usual
  delivery note and invoice, so a producer who also sells online keeps
  this app's flows. Until then every order went through the COD checks.

## Demos (19 October 2026)

- **Two producer demos, one per sector template**: a food producer and a
  clothing workshop. Each template needs a demo to be checked anyway, and
  Phase 2 has three weeks at about 10 hours a week, which leaves no room for a
  third. With Encre & Fil (dafter-cod's COD demo) that makes three demo sites,
  one per way of buying: Atelier for food, Atelier for clothing, Vente en
  ligne.
- **The food demo is one coherent business** (jams, date paste, honey), not
  the "honey/cosmetics producer" first planned: a prospect has to recognize
  their own trade. Cosmetics share its mechanics (recipes by weight,
  batches, expiry), so the food demo also serves a cosmetics prospect until
  one is in the pipeline.
- **The clothing workshop stays**: garment workshops are one of the two
  verticals named in the October deep-dive, and size-and-colour variants
  with fabric costing are where ERPNext's manufacturing beats billing-only
  tools such as Factee.
- **One demo per tax regime**: food on régime réel (TVA shown), clothing on
  IFU (no TVA, IFU note), so both paths of `apply_tax_regime` are on screen.
- **"Online sellers who make what they sell"** (the deep-dive's other target)
  is shown later by upgrading Encre & Fil with BOMs and work orders, not by a
  new demo site: it already has a workshop warehouse for blank t-shirts.
- **Not built now**: joinery (make-to-order, a different production pattern
  from both demos), bakery, printing. A demo for those comes when a prospect
  in that trade appears, like a third sector template.
- **Built from real figures**: approximate numbers from one real producer per
  sector (Required Data doc, items C1 and C2) beat precise invented ones.
  Until they arrive, plausible placeholders live in `demo/food.py` and
  `demo/clothing.py` only.

### How the demos are built (19 October 2026, docs/DEMO.md)

- **Through the client's door**: `prepare()` and the import workbook set the
  demo up exactly as a client site, so every demo load also tests onboarding.
- **Planned in plain Python, then posted**: `planner.py` keeps its own stock
  and only emits what is possible (nothing delivered before it was made,
  nothing made before its ingredients arrived); `engine.py` posts it as real
  ERPNext documents in date order. Planning without a database makes the
  stories testable in milliseconds (`tests/test_demo.py`).
- **Same story every time**: a day's randomness depends on the seed and that
  day only, and the first day is stored on the site, so loading again later
  replays the same past and adds the days since.
- **Past days' documents are posted at noon** (21 October 2026), not at the
  clock time of the load. The clothing demo, built at 11:33, failed to reload
  at 10:00: its first day's work order fell before the opening stock posted
  that day at 11:33. Today's documents keep the clock time (ERPNext refuses
  stock posted in the future).
- **Working days are Sunday to Thursday.**
- **Outgoing batch lines are split by the engine**, oldest batch first,
  expired ones skipped: ERPNext 16 puts one batch on a line by itself and
  fails when a line needs more than one batch holds.
- **Stock is valued batch by batch (FIFO)**, so a price rise reaches the
  product cost only when the new batches are used. The demos keep their
  opening stock of raw materials small and put the rises (strawberry pulp
  +18 %, jersey +15 %) eight and nine weeks back, so the step shows: on the
  19 October load, strawberry jam 250 g went from 155.83 to 165.18 DA a jar in
  mid-September. Jersey is bought 150 m at a time for the same reason (at
  400 m, the old rolls lasted the whole story).
- **"Today" looks the same whatever the day**: a demo is loaded on any
  date, so what the script shows cannot depend on luck. One supplier per demo
  is slow (the glassworks in Sétif, 8 working days; the mill in Oran, 12) and
  its items are ordered in lots smaller than what is used while waiting: the
  250 g or 500 g jars, and fleece or denim, are under their reorder level
  with an order on the way. `test_demo.py` plans ten different "todays" and
  checks it (`SHOWN_LOW` in each profile), with at most three late orders.
- **A product no longer made sells until its stock runs out**, then the
  order line is refused (fig jam after September, the old quince jam).
  Without this, orders for it waited forever.
- **First come, first served**: an order that is due but not complete keeps
  the stock it needs, so small orders taken after a wholesaler's cannot
  starve it for weeks.
- **Each invoice has its own randomness for its payment**: the "bad payer"
  rule depends on today, and drawing from the day's randomness shifted every
  later order of that day, so a reload replayed a different past (caught by
  `test_same_story_on_a_later_day_starts_the_same`).
- **Labour is an additional cost on each manufacture entry** (per unit, in
  the profile), not BOM operations: operations would need workstations and
  job cards for every work order, which a small workshop does not keep.
- **The manager login has both the Manager and the User roles** of each
  area: ERPNext 16 lets only Manufacturing User and Stock User read a Work
  Order. A reload adds a role missing from an existing login.
- **The import files are attached to the Company**: a private file is shown
  only to its owner (Administrator, who ran the load) or to users who can
  read what it is attached to.
- **Demo logins share one password** (`Demo-2026!`), written in docs/DEMO.md:
  demo sites hold only invented data. **On a public link it is replaced**
  (29 October 2026, review of 27 October, 3.4): the repo is public, so
  `scripts/demo_tunnels.sh` sets a new random password on every demo login at
  each start and prints it, and takes System Manager away from any demo login
  (`loader.secure_logins`): a visitor could otherwise change the site's
  settings, features and users. The tunnels keep `bench serve`, not gunicorn:
  without nginx in front, gunicorn serves no `/assets` (CSS, JS), and
  Werkzeug 3's debugger answers only requests addressed to the PC's own names
  (a tunnel's are `*.trycloudflare.com`), behind a PIN.
- **A load takes about 20 minutes on the WSL bench** (code on the Windows
  disk), against the 10 planned. Acceptable for a demo built once and topped
  up later; to be measured again on the server.

## Operations (29 October 2026, reviews of 20 and 27 October)

- **No password on a command line.** `dz_core/secret_bench.py` runs a bench
  command with `--db-root-password` / `--admin-password` taken from its
  environment and added to its own `sys.argv` in memory: `ps` and
  /proc/<pid>/cmdline show every process's arguments to every local user,
  the environment only to the same user and root. The hub's "Créer le site"
  and the restore drill use it; DEPLOY.md adds `hidepid=2` for other tools.
  Not a separate file of secrets: the hub already keeps the root password
  encrypted in DZ Hub Settings, and a file would be one more copy.
- **Off-site backups leave encrypted or not at all**: `backup_offsite.sh`
  refuses a remote that is not an rclone `crypt` remote (`ALLOW_PLAIN_REMOTE=1`
  for one encrypted another way). Not Frappe's `backup_encryption_key`: that
  would also encrypt the local backups the restore drill reads, and rclone
  crypt covers every file, the site config included.
- **A suspended client keeps read access to their books** (review of 27
  October, 3.5; decision D2 by Adem): `suspension.py`, a doc_events "*" lock
  on save, submit, cancel and delete while site_config has `dz_suspended`
  (set by the hub's *Suspendre*, with the scheduler paused). Logs, the audit
  trail and background report runs stay allowed. Not Frappe's maintenance
  mode: it shuts the client out, and its read-only variant refuses the login
  itself, which writes a session (tried 30 October 2026). The client must be
  able to consult their books for ten years. Limit: a write that skips
  documents (db_set, SQL in code) is not stopped.
- **The restore drill cannot act on the real world, and catches a loss**:
  scheduler paused and e-mails muted on the copy; the live site counted as it
  was at the backup's time (`restore_check.summary(until=)`), and the copy
  must hold at least that much.
