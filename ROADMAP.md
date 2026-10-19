# Roadmap

What to build next in dz_core, in order. Work top to bottom; each item has a
"done when" line, and an item is done only when that line is true and the
tests pass. Online-sales work (orders, couriers) belongs in dafter-cod, not here.

The dates follow the launch plan (checkpoints 29 Nov 2026, 27 Dec 2026,
28 Feb 2027). Move items between phases if reality says so, but write down why
in DECISIONS.md.

Legend: [x] done, [ ] to do, (A) needs the accountant first.

## Phase 0: base app (done, 18 Oct 2026)

- [x] One-command client setup: wizard, sector, warehouses, tax regime, opening-balance account, DZ Core Settings
- [x] Sector templates: Alimentaire et cosmétique, Confection
- [x] Tax regime: IFU (no TVA) or régime réel (19 % default, 9 % available)
- [x] Legal fields (decree 05-468) on Company, Customer, Sales Invoice
- [x] Print formats "Facture DZ" and "Bon de livraison DZ", amounts in French words
- [x] Excel import workbook with a dry run
- [x] Backup and restore-test scripts (copied, not yet run on a server)
- [x] dafter-cod runs on top of dz_core (PR #7)
- [x] Split finished (19 Oct): wilaya list, phone formatting, Customer phone and wilaya, backup scripts, restore check and server guide moved from dafter-cod (docs/SPLIT.md). Feature switches stay in dafter-cod (DECISIONS.md)

## Phase 1: usable on your own laptop (19 Oct to 8 Nov)

Goal: you can set up a client and show it, without help.

- [ ] **Install from GitHub.** `bench get-app` both repos on a clean local bench (Fedora, see dafter-cod docs/LOCAL_TEST.md), then run both test suites.
  Done when: 23 dz_core and 98 dz_cod tests pass on a bench built only from GitHub.
- [ ] **Walk through the code.** Read every file in dz_core and write one line per file in your learning log: what it does, what calls it.
  Done when: you can explain `prepare()` and `import_workbook()` step by step without opening them.
- [ ] **Default print formats.** Make "Facture DZ" and "Bon de livraison DZ" the defaults during `prepare()` (today it is a manual step).
  Done when: a new Sales Invoice prints as Facture DZ without touching Print Settings.
- [ ] **Check the PDF in the browser.** Start the web server (`bench start`), open an invoice, click PDF.
  Done when: the PDF matches the sample (French amount in words, legal mentions, stamp box).
- [ ] **French and Arabic labels.** Complete `dz_core/translations/` (started with the wilaya and contact labels moved from dafter-cod) for every label dz_core adds (fields, settings, messages), and copy dafter-cod's translation test so a forgotten label fails.
  Done when: a user with language Arabic sees Arabic labels on the fields dz_core adds.
- [ ] **Clean up demo noise.** The setup wizard leaves English item groups (Products, Raw Material, Services...). Decide: hide, rename or keep, and do it in the sector template.
  Done when: the Item Group list shows only what the sector needs, or the choice is written in DECISIONS.md.

## Phase 2: demo sites and producer reports (9 Nov to 29 Nov)

Goal: a prospect can log in and see their own trade working.

Two demos, one per sector template (decided 19 Oct 2026, DECISIONS.md "Demos"). Build first the one whose sector your first discovery interviews are in (Required Data doc, C5); both use real figures from one producer (C1, C2).

- [ ] **Food demo.** A `dz_core.demo` module like dafter-cod's: one fictional artisanal food producer (jams, date paste, honey), régime réel, selling to shops and wholesalers. Recipes per batch, batch and expiry tracking, 3 months of purchases, production (work orders), sales and invoices.
  Done when: one command fills an empty site, running it twice adds nothing, and its invoices show TVA (19 %, and 9 % where the accountant says it applies).
- [ ] **Clothing demo.** Same module, second company profile: one fictional confection workshop, IFU, selling wholesale to boutiques. Models with size and colour variants, fabric per piece, trims, work orders, 3 months of history.
  Done when: one command fills an empty site, running it twice adds nothing, and a model's cost shows its fabric and trims.
- [ ] **Cost per product report.** Raw material cost per unit from the BOM, selling price, margin.
  Done when: the confiture in the food demo shows its cost from fruit, sugar and jar prices, and changing the sugar price changes the cost.
- [ ] **Stock value report.** Value of stock per warehouse and per item group, at a chosen date.
  Done when: totals match ERPNext's Stock Balance report on the demo site.
- [ ] **Sales per month report.** Per product and per customer, with the month-on-month change.
  Done when: it opens on the demo site with 3 months of data and the totals match the invoices.
- [ ] **Low stock alert.** Reorder levels from the import workbook (new optional column), shown on a simple workspace.
  Done when: a raw material below its level appears on the workspace.
- [ ] **Workspace "Atelier".** One home page: what to produce, what to buy, today's sales, the three reports.
  Done when: a new user lands there after login and can reach every daily task in one click.

Checkpoint 29 Nov: demo sites ready to show, 8+ discovery conversations held (launch plan).

## Phase 3: accounting V1 and the server (30 Nov to 27 Dec)

Goal: a first pilot can go live on the VPS.

- [ ] (A) **Meeting with the accountant.** Bring: the sample invoice, IFU wording, stamp duty scale, G50 helper needs, the default stock accounts question.
  Done when: answers are written in DECISIONS.md.
- [ ] (A) **Invoice mentions validated.** Apply the accountant's corrections to Facture DZ and the IFU note.
  Done when: the accountant has seen a printed invoice and said yes.
- [ ] (A) **Stamp duty on cash payments.** Configurable scale (DGI circular 14/MF/DGI/LF.2025), applied only when the payment mode is Espèces.
  Done when: a cash invoice gets the right duty for 3 amounts the accountant gives, and a BaridiMob invoice gets none.
- [ ] (A) **IFU turnover report.** Monthly and yearly turnover, ready for the declaration.
  Done when: the accountant says it is what they need.
- [ ] (A) **G50 helper report** (régime réel only). TVA collected and paid per month, exportable to Excel.
  Done when: the accountant checks it against a real month.
- [ ] (A) **Default stock accounts.** Fix the inventory and stock adjustment accounts the Algerian chart maps by default.
  Done when: a purchase receipt posts to the class 3 stock account the accountant chose.
- [ ] **VPS setup.** Production bench, nginx, SSL, one subdomain per client, following docs/DEPLOY.md (then dafter-cod's docs/DEPLOY.md for online sellers).
  Done when: a demo site is reachable over HTTPS on its own subdomain.
- [ ] **Backups for real.** Daily off-server backup and a restore test on the VPS.
  Done when: `scripts/restore_test.sh` passes on the server.

Checkpoint 27 Dec: at least one pilot agreed, VPS live with tested backups (launch plan).

## Phase 4: pilots (from the first pilot)

Goal: real clients use it daily; their requests shape what comes next.

- [ ] **Onboard pilot 1** with the setup checklist (package scope doc), import workbook and training.
  Done when: the pilot records purchases, production and sales for 2 weeks without you.
- [ ] **Fix what pilots hit.** Every pilot request goes to one of: configuration (do it), data (they do it), customization (quote it or say no). Two pilots asking for the same thing: move it into the sector template.
  Done when: each request has a line in DECISIONS.md or LATER.md.
- [x] **Move the remaining pieces from dafter-cod** (docs/SPLIT.md): done 19 Oct 2026, moved ahead of plan while no client site is live. Feature switches stay in dafter-cod by decision.

Checkpoint 28 Feb 2027: one pilot live and using it daily, one paying client who is a stranger. If not: stop selling the service, keep the skills.

## Later (not before a client asks)

- Encre & Fil, the COD demo in dafter-cod, also produces: BOMs (blank t-shirt + print) and work orders on top of its orders, to show Pack Atelier + Vente en ligne on one site. First of these once Phase 2 is done, or sooner if an online seller who makes their products is in the pipeline
- Cosmetics demo data on the food template (same mechanics: recipes by weight, batches, expiry) when a cosmetics prospect is in the pipeline
- A third sector template (bakery, carpentry, printing...) when a client in it signs
- Per-size BOMs for precise clothing costing (paid extra)
- Full SCF financial statements and liasse fiscale, validated by an accountant
- Quality and traceability reports for food producers (batch recall)
- Mobile-friendly stock counting page
