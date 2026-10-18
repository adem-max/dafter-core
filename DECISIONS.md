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
  have them. dz_cod still writes Stock Settings `default_warehouse`, which
  no longer does anything on v16.
- **An opening-balance account is added** ("Ouverture temporaire", type
  Temporary, under the liability root): the Algerian chart has none and the
  opening stock import needs one.
- **Algerian chart of accounts**: "Algerie - Plan Comptable General 2 avec
  code", shipped with ERPNext, same as dz_cod.

## Tax

- **IFU is the default.** Most very small producers pay the IFU (individuals
  up to 8 million DA turnover) and charge no TVA, so the 19 % template made
  by the setup wizard is not applied by default for them. dz_cod already
  removed it for COD sellers for the same reason.
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
