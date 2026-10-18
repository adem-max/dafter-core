# DZ Core

The base every client gets, on top of ERPNext v16: setup in one command,
sector templates, legal invoices, an Excel import workbook, and backups.

```
frappe   (framework)
erpnext  (stock, sales, purchases, manufacturing, accounting) - never edited
dz_core  (this app: what every client gets)
dz_cod   (optional, on top: orders, couriers and returns for online sellers)
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
| Backups | `scripts/`, `dz_core/setup/restore_check.py` | Daily off-server backup and a restore test |

## Set up a new client

```bash
bench new-site client1.localhost --install-app erpnext
bench --site client1.localhost install-app dz_core
bench --site client1.localhost execute dz_core.setup.new_client.prepare \
    --kwargs "{'company': 'Miel Atlas', 'abbr': 'MA', 'sector': 'Alimentaire et cosmétique', 'tax_regime': 'IFU'}"
```

Sectors: `Alimentaire et cosmétique`, `Confection`.
Tax regimes: `IFU`, `Régime réel`.

Then, by hand: the legal mentions on the Company form, the company address,
users, and the default print formats (Sales Invoice: "Facture DZ", Delivery
Note: "Bon de livraison DZ", in Print Format Builder or Customize Form).

## Import the client's data

```bash
# 1. empty workbook for the site's sector, to send to the client
bench --site client1.localhost execute dz_core.imports.workbook.make_template --kwargs "{'path': '/tmp/client1.xlsx'}"
# 2. check what they sent back (creates nothing)
bench --site client1.localhost execute dz_core.imports.workbook.import_workbook --kwargs "{'path': '/tmp/client1.xlsx'}"
# 3. import for real once the check shows no errors
bench --site client1.localhost execute dz_core.imports.workbook.import_workbook --kwargs "{'path': '/tmp/client1.xlsx', 'dry_run': 0}"
```

## Not done yet (full plan: ROADMAP.md)

- Stamp duty on cash payments, G50 helper, IFU turnover report: waiting for the accountant's rules
- Invoice legal mentions: checked against decree 05-468, still to be validated by an accountant
- Wilaya list, phone formatting, feature switches and the deployment guide still live in dz_cod (`docs/SPLIT.md`)

## Tests

```bash
bench --site test.localhost set-config allow_tests true
bench --site test.localhost run-tests --app dz_core
```
