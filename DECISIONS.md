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
- **An opening-balance account is added** ("Ouverture temporaire", type
  Temporary, under the liability root): the Algerian chart has none and the
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
- **The catalogue is read with plain imports for the hub**
  (`bench_catalog`): the hub site does not install the client apps, and
  `frappe.get_hooks(app_name=...)` and `frappe.get_attr` both refuse an app
  that is not installed on the current site.

## Tax

- **IFU is the default.** Most very small producers pay the IFU (individuals
  up to 8 million DA turnover) and charge no TVA, so the 19 % template made
  by the setup wizard is not applied by default for them. This replaced
  dz_cod's own "remove the default 19 % VAT" step.
- **Régime réel**: the 19 % template stays the default. ERPNext's wizard
  already makes a 9 % one (reduced rate: basic foodstuffs and listed
  essentials, extended by the 2026 finance law); one is added only if missing.
- **Waiting for the accountant, not built:** stamp duty on cash payments
  (scale from circular 14/MF/DGI/LF.2025; electronic payments are exempt),
  the G50 helper for régime réel, the turnover report for IFU, and the exact
  wording of the IFU mention on invoices (`IFU_NOTE` in `tax.py`, editable
  in DZ Core Settings), and the stock accounts ERPNext maps by default for the
  Algerian chart (a fresh site points "Default Inventory Account" at a class 3
  services account).

## Invoices

- **Legal mentions from decree 05-468**: seller's name, legal form, activity,
  address, RC (or auto-entrepreneur card), NIF, NIS, tax article, capital for
  companies; business buyer's RC, NIF, NIS, tax article; payment method and
  date; stamp and signature. Cancelled invoices print "FACTURE ANNULÉE"
  across the page. To be validated by an accountant before the first client.

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
  import day looked newer than everything produced after it.
- **Clients carry NIS and tax article (AI) too** (19 October 2026): the
  buyer's mentions on a business invoice are RC, NIF, NIS and AI; the sheet
  had only the first two. A column added later is optional in the file: a
  file made from an older template still imports.
- **Variants are named in words** ("Chemise manches longues XL Bleu"):
  ERPNext names them with the attribute abbreviations ("…-XL-BLE"), which
  then print on the invoice. The item code keeps ERPNext's form.
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
- **On a site with dz_cod, every sales order goes through the COD checks**
  (phone, wilaya, address), wholesale ones included: dz_cod has no "not a
  COD order" path yet. To decide before a producer who also sells online
  goes live (dafter-cod).

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
  demo sites hold only invented data.
- **A load takes about 20 minutes on the WSL bench** (code on the Windows
  disk), against the 10 planned. Acceptable for a demo built once and topped
  up later; to be measured again on the server.
