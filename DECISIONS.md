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
- **Feature switches stay in dz_cod** until dz_core has an optional feature
  of its own: all four are COD features and the hub depends on dz_cod's
  command.

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
