# DZ Core

The base every client gets, on top of ERPNext v16: setup in one command,
sector templates, legal invoices, an Excel import workbook, and backups.

```
frappe   (framework)
erpnext  (stock, sales, purchases, manufacturing, accounting) - never edited
dz_core  (this app: what every client gets)
dz_cod   (optional, on top: orders, couriers and returns for online sellers)
dz_hub   (private, the vendor's own site: clients, offers, billing; talks to dz_core)
```

Pack Atelier = a site with `dz_core`.
Pack Atelier + Vente en ligne = a site with `dz_core` and `dz_cod`.

## What it does

| Part | Where | What |
| --- | --- | --- |
| New client setup | `dz_core/setup/new_client.py` | Setup wizard (French, Algeria, DZD, Algerian chart of accounts), sector template, tax regime, DZ Core Settings |
| Sector templates | `dz_core/setup/sectors.py` | Item groups, units, size and colour attributes, 3 warehouses, manufacturing defaults. One dict per sector |
| Tax regime | `dz_core/setup/tax.py` | IFU: no TVA by default. Régime réel: 19 % default plus a 9 % template |
| Legal mentions | `dz_core/setup/custom_fields.py` | Company: legal form, activity, RC or AE card, NIF, NIS, AI, capital. Customer: RC, NIF, NIS, AI. Invoice: payment method |
| Print formats | `dz_core/dz_core/print_format/` | "Facture DZ" (Sales Invoice) and "Bon de livraison DZ" (Delivery Note) |
| Import workbook | `dz_core/imports/workbook.py` | One Excel file: suppliers, customers, items, clothing models, BOMs, opening stock |
| Wilayas | `dz_core/setup/wilayas.py`, doctype DZ Wilaya | The 69 wilayas (2026), each 2026 one with its parent; customers get a wilaya. dz_cod adds delivery rates to each |
| Phone numbers | `dz_core/phone.py` | Algerian numbers cleaned to one format (`+213 555…` → `0555…`) on the Customer and in imports |
| Backups | `scripts/`, `dz_core/setup/restore_check.py` | Daily off-server backup and a restore test (apps on top add their records by hook) |
| Optional features | `dz_core/features.py`, `dz-features` command | What each client may switch on, per site. Apps declare their features with a `dz_features` hook (dz_cod has four); the hub (dz_hub) sells and applies them |
| Server guide | `docs/DEPLOY.md` | Ubuntu server, one site per client, SSL, backups, restore, updates, security, new client in 2 hours |
| Demo sites | `dz_core/demo/`, `docs/DEMO.md` | A food producer (régime réel) and a clothing workshop (IFU) with 13 weeks of history, set up through `prepare()` and the import workbook; a 10-minute script for prospects |

## Set up a new client

```bash
bench new-site client1.localhost --install-app erpnext
bench --site client1.localhost install-app dz_core
bench --site client1.localhost execute dz_core.setup.new_client.prepare \
    --kwargs "{'company': 'Miel Atlas', 'abbr': 'MA', 'sector': 'Alimentaire et cosmétique', 'tax_regime': 'IFU'}"
```

Sectors: `Alimentaire et cosmétique`, `Confection`.
Tax regimes: `IFU`, `Régime réel`.

Full server guide (Ubuntu, SSL, backups, the 2-hour checklist): `docs/DEPLOY.md`.

`prepare` also makes "Facture DZ" and "Bon de livraison DZ" the default print
formats and removes the English item groups ERPNext's wizard leaves unused.

Then, by hand: the legal mentions on the Company form, the company address,
and users.

## Import the client's data

```bash
# 1. empty workbook for the site's sector, to send to the client
bench --site client1.localhost execute dz_core.imports.workbook.make_template --kwargs "{'path': '/tmp/client1.xlsx'}"
# 2. check what they sent back (creates nothing)
bench --site client1.localhost execute dz_core.imports.workbook.import_workbook --kwargs "{'path': '/tmp/client1.xlsx'}"
# 3. import for real once the check shows no errors
bench --site client1.localhost execute dz_core.imports.workbook.import_workbook --kwargs "{'path': '/tmp/client1.xlsx', 'dry_run': 0}"
# opening stock counted on another day: add 'opening_date': '2026-11-01'
```

Clothing models and the stock of their size/colour variants go in two files:
the models first, then the opening count (a variant must exist before its
stock line is checked).

## Demo sites

```bash
bench --site food-demo.localhost execute dz_core.demo.loader.load --kwargs "{'profile': 'food'}"
bench --site atelier-demo.localhost execute dz_core.demo.loader.load --kwargs "{'profile': 'clothing'}"
```

On dedicated sites with ERPNext + dz_core only. Logins, what each demo shows,
and a 10-minute script for prospects: `docs/DEMO.md`.

## Not done yet (full plan: ROADMAP.md)

- Stamp duty on cash payments, G50 helper, IFU turnover report: waiting for the accountant's rules
- Invoice legal mentions: checked against decree 05-468, still to be validated by an accountant
- Translations: only the wilaya and contact labels have English and Arabic so far (`dz_core/translations/`)

The split with dz_cod is finished: `docs/SPLIT.md` lists what moved here, what
stays in dz_cod and why, and the rule for new work.

## Tests

```bash
bench --site test.localhost set-config allow_tests true
bench --site test.localhost run-tests --app dz_core     # 40 tests (13 unit + 27 integration)
```
