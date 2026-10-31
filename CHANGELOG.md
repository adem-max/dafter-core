# Daftar changelog

What changed in the three Daftar apps, release by release, and why it was done that way.
Newest first. The full reasoning lives in each repo's `DECISIONS.md`; this file is the
short history across all three.

| Repo | App | Role |
| --- | --- | --- |
| `dafter-core` | `dz_core` | The base every client gets |
| `dafter-cod` | `dz_cod` | Online sellers (cash on delivery), on top of dz_core |
| `dz_adm` | `dz_hub` | The vendor's hub: clients, packs, billing, actions on client sites |

The three apps share one version number. dz_cod and dz_hub refuse to load on an older
dz_core (`DZ_CORE_MIN`).

## Where things stand (31 October 2026)

- **Releases:** 0.2.0 to 0.4.2 are tagged (`v0.2.0` ... `v0.4.2`) in the three repos.
  - 0.4.1 and 0.4.2 are tagged on `main`, where everything up to them is merged (PRs since 30 Oct 2026).
- **Tests:** on local test sites and on GitHub CI (green in the three repos; dafter-core's CI
  also runs dz_cod's tests on its dz_core). The counts are in CI's log.
- **Sites:** the demo, client and hub sites are not migrated to 0.4.2 yet.
- **This file** lives in dafter-core since 0.4.2 (until then in the Daftar workspace), so that
  anyone deploying from GitHub sees it.
- **Demos:** the three demos were reloaded on 0.4.0 and their ledgers checked.
  - food-demo: régime réel, stamp duty on.
  - atelier-demo: IFU.
  - demo.localhost: the online shop.
- **Waiting on others:**
  - **The accountant:** invoice mentions, the SCF statement layout, the IFU rates, switching on the stamp duty.
  - **The tax office:** the stamp duty on cash on delivery, the arrêtés of the 2027 software rules.
  - The questions are listed in section 9 of the SCF advice doc.

---

## 0.4.2: second look at the fixes (31 October 2026)

**Why.**
- A second outside review, of 0.4.1 the same day, checked every fix and found four gaps
  around them. Each was checked against Frappe 16's own code before it was fixed.

**Changes.**
- **Suspension (dz_core):** also stops changes to submitted documents (a workflow step on a
  confirmed order, a Versement): Frappe runs `before_validate` only on save and submit, so
  the lock now listens to `before_update_after_submit` too. A suspended client can export
  again: the archive an export or a closing file writes is allowed (DZ Archive written by the
  code, and its files), other uploads stay refused.
- **Session after "Marquer livrée" (dz_cod):** the step that runs ERPNext's payment builder
  as Administrator gives the request back its own session (`as_administrator()`). Frappe's
  `set_user` replaced the session's id and data, and a browser request saved that emptied
  session at its end; it recovered only through Frappe's fallback to the database copy.
- **Order fields (dz_cod):** nobody may change Daftar's read-only fields of a submitted order
  (`dz_settlement`, `dz_payment_entry`, the dates...) through the API; Stock and Accounts
  Users change only the courier, tracking number and stop desk. Through the API, an Accounts
  User could hide an unpaid parcel from the month's courier check.
- **Demo links (dz_core):** `bench serve` starts without Werkzeug's debugger and console, and
  without Frappe's dev-server tracebacks.
- **Docs:** this changelog moved into dafter-core; ROADMAP without stale test counts.

**Versions.** `DZ_CORE_MIN` is 0.4.2 in dz_cod (dz_core's suspension must cover its order
steps); the hub is unchanged apart from its version.

**After updating a site:** `bench --site <site> migrate` (the suspension hook is new: a site
not migrated serves the old cached hooks).

---

## 0.4.1: fixes from the outside review (31 October 2026)

**Why.**
- An outside review of 27 October found bugs in permissions, closings, couriers and
  operations before the first client. Every finding is fixed or recorded; the full list,
  the reason for each fix and the limits are in `FIXES-DONE-2026-10-29.md`.

**Changes.**
- **Accounting (dz_core):** opening advances (4191, 40913) keep their party; monthly entries
  found by a fixed key (`dz_closing_key`), not a remark; the year-end checks leave the closing
  voucher out; company checks on every closing button.
- **Audit trail (dz_core):** a hash chain per company, its last hash in the yearly archive.
- **Operations (dz_core, dz_hub):** passwords never on a command line (`secret_bench`);
  off-site backups only to an encrypted remote; a safe restore drill that reads Frappe 16
  backups; a suspended client can read and export but save nothing; one hub action at a time
  per client; demo links get a new password at each start and no System Manager.
- **Online sales (dz_cod):** Stock User and Accounts User can move the orders of their own
  steps; return inspection adds rows up; signed webhooks with valid JSON; tracking numbers
  looked up on the order's own courier; one computation of what an order already received.
- **Quality:** indexes on looked-up fields, declared dependencies, CI runs each app's tests
  against the others and every week.

**Versions.** `DZ_CORE_MIN` is 0.4.1 in dz_cod (its tests use dz_core's new test helpers and
feature gate) and in dz_hub (it calls `secret_bench` and `suspension`).

**After updating a site:** `bench --site <site> migrate` runs two patches (closing keys from
past remarks, the audit chain over past rows), adds the new fields and indexes, gives Stock
User and Accounts User their Sales Order rights, and signs the COD webhooks.

---

## 0.4.0: compliance and outputs (22 October 2026)

**Why.**
- From 1 January 2027 (loi de finances 2026), Daftar has to give every client a signed
  publisher's commitment, and be able to hand over the books' data on request.
- The SCF advice set the rule: sign only for features that exist.
- So this release builds what the commitment depends on (decree 09-110). It adds what the
  accountant needs at the year end, and what IFU and auto-entrepreneur clients must file.

**Changes (dz_core unless said).**
- **Journals:** every ledger line gets a journal (VE, AC, CA, BQ, ST, OD, AN).
  - *Why computed, not stored:* no migration of past lines, and nothing that can drift.
- **Entry export** (report "Export des écritures"): in the French FEC layout, plus the user on each line.
  - *Why FEC:* the Algerian format is left to an arrêté not yet published, and accounting software used in Algeria imports FEC files.
  - It includes cancelled entries and their reversals: the immutable ledger keeps both.
  - It adds opening (à-nouveaux) lines on a fiscal year's first day.
- **Audit trail** (new doctype DZ Audit Log): user, IP address and browser on every validation, cancellation and change after validation.
  - *Why our own:* ERPNext's Activity Log is deleted after 90 days and its Version log has no IP.
- **Archives** (new doctype DZ Archive): files kept with their SHA-256 hash and a `sha256sum` register.
  - An archive cannot be changed or deleted, nor can its files.
  - *Why:* 10-year retention (CPF art. 64), and proof the files were not altered.
- **SCF statements:** compte de résultat par nature and bilan, as ERPNext 16 Financial Report Templates.
  - They are written as data in code and rewritten on every migrate.
  - Titles say "projet" until an accountant validates them.
- **Year end** (report "Exercice comptable"), four buttons:
  1. close the year: Stock Closing Entry, then the Period Closing Voucher into 120 (profit) or 129 (loss);
  2. freeze the year;
  3. make the accountant's closing file (Excel, PDF, entry export);
  4. make the yearly archive.
- **Opening from the accountant's trial balance:**
  - open invoices are created through ERPNext's opening tool, but inserted by Daftar, all or nothing;
  - the remaining balances go in one opening journal entry;
  - 479 must end at zero, or nothing is posted.
- **Stamp duty** (circular 14/2025 scale): built, but **off** until the accountant agrees.
  - It is set per payment mode: added to the invoice, or paid by the seller.
  - Cash on delivery can only be paid by the seller: the courier collects a fixed amount.
  - Cheques and transfers with their references on the invoice are exempt, and so are card and BaridiMob.
- **Auto-entrepreneur:** a third tax regime (no TVA, its own invoice note). The hub accepts it.
- **Registers and "Aide G12":**
  - sales and purchases registers to copy into the paper books (the law allows no computerised keeping);
  - turnover, the IFU on it (5 % goods, 12 % services, 0.5 % auto-entrepreneur, to confirm), and a button that books it;
  - "Clôture du mois" reminds the next returns: G50 by the 20th, G12 by 30 June, G12 bis by 20 January.
- **Warnings:**
  - a purchase line above 60,000 DA a unit is probably a fixed asset;
  - a purchase "sans facture" may not carry TVA;
  - a supplier invoice above 1 M DA paid in cash loses its TVA deduction;
  - régime réel: Aide G50 gives back the TVA on stock lost, stolen, destroyed or given away.
- **Documents** in `dafter-core/docs`: `COMPLIANCE.md`, `ENGAGEMENT-EDITEUR.md` (draft commitment) and `MANUEL-PROCEDURES.md`.
- **dz_cod:** a courier made again under the same name gets its old account back.

**Found while checking, and fixed.**
- **The bilan counted a closed year's result twice.**
  - ERPNext's engine keeps the closing voucher's line on 120/129 but drops its reversal of classes 6 and 7.
  - Daftar now computes the "result in progress" line itself.
  - Found by running a real year close on a throwaway site.
- **An archived CSV's hash never matched:** Frappe drops the file's first byte (its BOM) when reading it back. The check now reads the raw file.
- **CI failed:** GitHub's runner had no wkhtmltopdf for the PDFs. Both workflows now install it.

**Not built, on purpose:**
- cash-basis statements: the accountant should say first whether they want them;
- the fresh-date exemption: no client sells fresh dates;
- foreign advertising and platform withholdings, micro-importers: they wait for a written answer from the tax office;
- fixed assets in the opening import: they are entered by hand.

---

## 0.3.0: SCF set-up (21 October 2026)

**Why.**
- A reasoning model answered the accounting questions in the doc "Daftar: SCF default
  accounts and compliance advice". Several of its answers can only be applied before a
  company's first stock entry, so they had to land before the first pilot.
- It also disagreed with what 0.2.0 shipped:
  - cost of sales on 7245;
  - stock adjustment on 6031;
  - round-off on 6588;
  - stock accounts per warehouse;
  - a Versement that credited each invoice.

**Changes.**
- **Chart of accounts:** about 33 accounts added (reserves, the owner's account, machines, couriers' collections 4671n, 4781, IFU, 6589 "charges à reclasser"...).
  - 11, 12, 5118, 6588 and 7588 became groups, only while empty.
  - Some accounts were re-typed so ERPNext's pickers offer them.
  - The repealed TAP accounts (and other unused ones) were disabled.
  - The opening account became 479, under a class 47 liability group.
- **Default accounts by SCF number:**
  - cost of sales falls back to 6589, which is emptied every month;
  - stock adjustment goes to 6572, round-off to 65881.
  - Only the setup wizard's choices or earlier Daftar choices are replaced. *Why:* never overwrite a choice someone made.
- **Stock accounts per item group, valued at moving average (CMP):** every item group carries its own stock, cost, consumption and income accounts.
  - *Why:* one courier warehouse can hold several kinds of goods, and trims and packaging stop posting to 311.
  - ERPNext then refuses an item whose group has no stock account.
  - A new subgroup copies its parent's accounts.
- **Ledger rules:**
  - immutable ledger on: a cancellation adds a dated reversal and never deletes;
  - nobody may delete accounting or stock documents, drafts included;
  - "Delete Transactions" is blocked.
  - *Why:* decree 09-110 art. 13. Demos run without the immutable ledger, because a wipe would leave reversals dated the wipe day.
- **Manufacturing:** a manufacture posts consumption (60x) and production stocked (7245), the SCF way.
  - *Why:* this replaces the planned monthly reclassification entry. A spike showed ERPNext does it on its own once item groups carry the accounts; a hook fixes work-order manufactures.
- **TVA per rate:**
  - collected TVA on 445711 (19 %) and 445712 (9 %), deductible on 44566 and 44562;
  - Item Tax Templates on the item groups;
  - report "Aide G50", with a button for the settlement entry.
  - "Add taxes from item tax template" is switched off, or IFU invoices got TVA.
- **"Clôture du mois" report:**
  - 6589, 4781, 476 and 479 must be empty;
  - 4081 debit balances are reclassified to 4097;
  - class 72 must equal the change in classes 33 and 35;
  - each courier's account must match its parcels (dz_cod);
  - then freeze the month.
- **Supplier groups, payment modes and asset categories** with their accounts.
- **dz_cod, COD redesign:**
  - at shipment, the parcel moves to a "Chez transporteur" warehouse;
  - at delivery, it is invoiced and paid into the courier's account 4671n;
  - a refused parcel is moved back, with no sale and no reversal;
  - the Versement is one journal entry that clears 4671n, with the courier's fees on its supplier account and differences on 65882 / 75882;
  - the delivery fee is an item line taxed like the goods.
  - *Why:* the tax falls when the buyer receives the goods. Many COD parcels are refused, and reversing a sale for each one was noise.
- **Decided against the advice:** no generic "Clients vente en ligne" customer. *Why:* dz_cod's warnings about refused parcels and its per-customer sales channel need one customer per buyer.

**Found while checking, and fixed.**
- A migrate failed: 6588 could not become a group while it was still the default round-off account.
- A migrate failed: an older site was missing a sector's item group.
- The demo wipes overflowed Frappe's job queue (over 1,000 jobs). They now wait for the workers.
- Work-order manufactures landed on the stock adjustment account; `production.py` fixes their accounts.
- The shop demo's opening stock went into the results (7245 / 6571); it now goes to 479.
- The shop wipe undid a shipment before its delivery note. A parcel's moves are now undone together, latest first.
- Some companies had no 479 account. It is now created directly as 479 under class 47.
  - ERPNext only renames an account when no ledger entry changed in the last 5 minutes.
  - A busy site is logged and skipped instead of failing the migrate.

---

## 0.2.0: review of 20 October 2026, sections 1 and 2 (21 October 2026)

**Why.** A review of the three repos (`REVIEW-2026-10-20.md`) found bugs and structural
problems to settle before the first client who has both the workshop and online sales.

**Bugs fixed (review section 1).**
- **Hub:** creating a site for an online seller with no courier failed. It now survives that and resumes after a failed step.
- **Import workbook:**
  - lot numbers were treated as per item, but ERPNext lots are global;
  - opening stock over 100 lines was submitted in the background without a word;
  - the dry run missed things the real import refuses.
- **Facture DZ:**
  - the totals did not add up with a discount;
  - credit notes printed as "FACTURE" with negative words.
- **dz_cod:** it failed its own lint (ruff 0.14.10).

**Structural changes (review section 2).**
- **COD orders now become invoices** at "Livrée", and each Versement is booked.
  - *Why:* the home page and the reports count invoices.
- **A "direct sale" channel next to COD:** the COD workflow no longer takes over every Sales Order on the site.
- **Optional features are off by default:** no feature list means the base only; "all" is for demo and test sites.
  - *Why:* a client gets what it pays for, even on a site made by hand or restored.
- **COD orders of batch-tracked products ship across lots**, and ERPNext picks the lots, oldest first.
- **Versions between the apps:** one version number, plus the `DZ_CORE_MIN` check.
- **Couriers' communes and stop desks** are kept per connector, not keyed by Yalidine ids.
- **CI on every push in the three repos:** lint, then the tests on a fresh site.
  - Sibling repos are taken at the branch of the same name.

**Not done from the review:** section 3 (encrypted backups, the restore drill's
safety, signed webhooks, the demo tunnel...) and section 4 (smaller things) are not
recorded as done. Check the review before the server goes live.

---

## Before 0.2.0: building the base (9 to 20 October 2026)

**dz_cod first (9 to 16 October).**
- **What was built:**
  - COD order workflow, wilayas, settings, reports, the Accueil home page;
  - the demo shop;
  - English and Arabic per user;
  - the Yalidine connector (parcels, statuses, communes, stop desks, prices, webhook);
  - backups with a restore drill;
  - optional features per client site;
  - one command to prepare a client site.
- **Decision:** Versements count money already paid on disputed orders.
  - *Why:* a demo walk found an order booked as paid twice.
- **Decision:** no default VAT on new sites. *Why:* most small sellers are IFU.

**The hub (16 October).** Clients, monthly billing and actions on client sites.

**dz_core, the base for every client (18 October).**
- **Decision:** split the base out of dz_cod.
  - What every client needs goes in dz_core: setup, sector templates, tax regime, legal invoices, the import workbook, wilayas, phones, backups, the server guide.
  - Only online-sales work stays in dz_cod.
  - dz_core never imports dz_cod; it offers hooks instead.
  - The split finished on 19 October (`dafter-core/docs/SPLIT.md`).
- **Decision:** repo names say "dafter" but app names stay `dz_core` / `dz_cod`. *Why:* renaming a Frappe app breaks live sites.
- **Decision:** the feature switches live in dz_core. The hub was renamed `dz_cod_hub` → `dz_hub` (19 October, before any live site) and manages every client through dz_core.
  - It sells two packs: Atelier (dz_core) and Vente en ligne (dz_cod).
- **What dz_core shipped:**
  - legal mentions from decree 05-468;
  - the "Facture DZ" and "Bon de livraison DZ" print formats, with amounts in French words;
  - the Excel import workbook with a dry run.

**Producer demos and reports (19 to 20 October).**
- **Decision:** two demos, a food producer (régime réel) and a clothing workshop (IFU), built through `prepare()` and the import workbook.
  - *Why:* show each prospect their own trade; the demo data is exactly what the app produces.
- **Reports:**
  - "Coût de revient": cost per product, margin;
  - "À produire": what to produce;
  - "À acheter": what to buy;
  - "Valeur du stock": stock value;
  - "Ventes par mois": sales per month.
- **Atelier home page,** where users land after login.
  - It needed a hook: Frappe 16.51 sent desk users to /desk.
- **Demo reloads no longer depend on the hour:** past days post at noon.

---

## Recurring rules (from all of the above)

- **Per-client differences** live in settings, custom fields or feature switches, never in `if client == ...` code.
- **Never overwrite** what someone chose: setup steps fill only what is empty or was set by the wizard or an older Daftar.
- **Before the first stock entry** are the irreversible choices: stock accounts per item group, moving average, the chart changes. `prepare()` runs them.
- **Never reinstall a demo or client site:** a demo is emptied with a full wipe.
- **Never close a year on a test or demo site:** nothing can post in it afterwards.
- **Sign only for what exists:** the 2027 commitment, the docs and the invoice note claim no feature that is not built.
- **Every release:**
  - the three suites pass locally and on CI;
  - the dev sites are migrated;
  - the demos are reloaded and their ledgers checked;
  - then one version in all three repos and a tag.
