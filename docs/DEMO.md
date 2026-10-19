# The producer demos

Two fictional producers with 13 weeks of history, built to be shown to a
prospect in 10 minutes. Each runs on its own site with **ERPNext + dz_core
only**: this is Pack Atelier, without the COD app.

| | Food producer | Clothing workshop |
| --- | --- | --- |
| Company | Les Délices de la Mitidja SARL, Boufarik (Blida) | Atelier Nour Confection, Sétif |
| Tax regime | Régime réel: TVA 19 % on every invoice | IFU: no TVA, IFU note on invoices |
| Site | `food-demo.localhost` | `atelier-demo.localhost` |
| Makes | 6 jams, date paste, 3 honeys (batches + expiry dates) | 6 models in sizes and colours (44 variants) |
| Buys | Fruit pulp, sugar, dates, bulk honey, jars, lids, labels, cartons | Jersey, fleece, denim, poplin, thread (by the cone), buttons, zips, rivets, labels, bags |
| Sells to | 3 wholesalers, 12 superettes, 15 grocers, 5 individuals, in 10 wilayas | 3 wholesalers, 11 boutiques, 4 companies (work coats), in 8 wilayas |
| 13 weeks (load of 19 Oct) | 151 orders, 146 invoices, 124 work orders, 41 purchases; about 980 documents | 78 orders, 76 invoices, 92 work orders, 32 purchases; about 580 documents |

**The figures are placeholders**, plausible but not a real producer's. They
live in `dz_core/demo/food.py` and `clothing.py` only; replace them with real
ones from the `data requested` folder and reload.

## Create a demo site

Keep `bench start` running in another terminal (the load posts hundreds of
backdated documents and ERPNext's workers follow them).

```bash
cd ~/frappe-bench
bench new-site food-demo.localhost --install-app erpnext      # MariaDB root password, then an admin password
bench --site food-demo.localhost install-app dz_core
bench --site food-demo.localhost execute dz_core.demo.loader.load --kwargs "{'profile': 'food'}"
```

Same for the clothing workshop with `atelier-demo.localhost` and
`'profile': 'clothing'`. A load takes about 20 minutes (clothing: 10) on the WSL bench
(code on the Windows disk); it prints its steps and a summary at the end.

On a laptop, `bench start` shows only the default site. To open a demo next
to it, without changing anything: `bench --site food-demo.localhost serve
--port 8001`, then http://food-demo.localhost:8001 (clothing: port 8002).
Or make it the default (dafter-cod docs/LOCAL_TEST.md section 5).

## Logins

| Login | Role in the demo | Language |
| --- | --- | --- |
| `gerant@<site>` | The owner: everything | Français |
| `production@food-demo.localhost`, `atelier@atelier-demo.localhost` | Production and stock | Français |
| `ventes@<site>` | Sales and payments | العربية (to show the Arabic interface) |

Password for all: `Demo-2026!` (demo sites only). `Administrator` keeps the
password chosen at `new-site`.

## Load again, wipe, reset

- **Load again** (any day): `load` skips everything already posted and adds
  the days since the last load, so the demo always ends "today".
- **Wipe the story, keep the site**:
  `bench --site food-demo.localhost execute dz_core.demo.wipe.run --kwargs "{'profile': 'food'}"`,
  then `load` again. Keeps the company, imported masters, opening stock, prices
  and users; takes several minutes.
- **Total reset** (faster, and the story starts again 13 weeks before today):
  `bench drop-site food-demo.localhost --force`, then "Create a demo site".

## How it is built

1. `prepare()` sets the company up exactly as for a client: wizard, sector,
   warehouses, tax regime, default print formats.
2. The masters go in through **the client import workbook**, in two files, as
   a client's would: data first, then the opening stock count (dated the first
   day of the story). Both files stay in **File** (private files attached to
   the Company, so the demo users see them; Frappe adds a few characters to
   the names: `import-demo-<profile>-1-donnees….xlsx`) to show a prospect.
3. `planner.py` plans the 13 weeks day by day (Sunday to Thursday), keeping
   its own stock so every document is possible: orders come in, work orders
   start when finished stock runs low, raw materials are ordered below their
   reorder level, invoices are paid on each customer group's terms.
4. `engine.py` posts the plan as real documents, in date order: purchase order
   → receipt (supplier batch) → supplier invoice → payment; work order →
   transfer to Travaux en cours → manufacture (new batch, labour added to the
   cost); sales order → delivery note (oldest batches first) → Facture DZ →
   payments; one cancelled and reissued invoice, one credit note, a stock
   count at each month end.

## What a prospect sees (and where)

| What | Where |
| --- | --- |
| Their Excel file becomes their data | File (or the Company's attachments) → `import-demo-food-1-donnees….xlsx`; Stock → Item, Customer, BOM |
| Recipes and work orders | Manufacturing → BOM, Work Order (one in progress today) |
| Cost per batch, and a price rise reaching it | Stock → report "Livre d'Inventaire" (Stock Ledger), item "Confiture de fraise 250 g": column "Prix d'Entrée" on the rows whose "Type de Référence" is Stock Entry, one per batch made; it steps up once the pulp bought after the 18 % rise (eight weeks ago) is used (T-shirts: jersey +15 %, nine weeks ago; item "T-shirt col rond" variants) |
| Batches and expiry dates, oldest sold first | Stock → Batch; the last quince jam batch expires within 30 days |
| Legal invoices | Accounts → Sales Invoice → Print: Facture DZ by default, amount in words, legal mentions; one cancelled invoice prints FACTURE ANNULÉE |
| Who owes what | Accounts → Accounts Receivable: about fifteen overdue invoices (clothing: eight); Superette Le Panier stopped paying its last invoices |
| What to buy | Stock → report "Qté de Stock Projeté" (Stock Projected Qty), warehouse Matières premières: "Quantité Réelle" under "Niveau de réapprovisionnement", with "Qté Commandée"; the 250 g or 500 g jars are under their reorder level with orders on the way (the glassworks delivers 8 working days after the order); in the workshop, fleece or denim from the Oran mill (12 working days). Buying → Purchase Order: the ones still to receive |
| What to deliver | Selling → Sales Order: orders to deliver and bill |
| Month-end counts | Stock → Stock Reconciliation: a few breakages found |
| Arabic | Log in as `ventes@…`: the whole interface right-to-left |

## A 10-minute script

Food producer first; the clothing workshop follows the same order with models
and sizes instead of jams.

1. **"Send us your Excel"** (1 min). Open File, show the two import files.
   Explain: we fill your data once in this file; the import checks every line
   and creates nothing while one line is wrong.
2. **A batch is made** (2 min). Manufacturing → Work Order: the one in
   progress, its materials already in Travaux en cours. Open a completed one:
   its stock entry, the jars made, the batch number and expiry date.
3. **What a jar costs** (2 min). Report "Livre d'Inventaire", item
   "Confiture de fraise 250 g": on the Stock Entry rows, the "Prix d'Entrée"
   of an August batch (about 156 DA), then an October one (about 165 DA). The pulp price went up: the new batches carry
   it, the old stock kept its cost. (The cost-per-product report of Phase 2
   will show this in one screen.)
4. **The invoice** (2 min). Sales Invoice → any paid one → Print: legal
   mentions, TVA 19 %, amount in French words. Then the cancelled one:
   FACTURE ANNULÉE. (Clothing: no TVA, the IFU note at the bottom.)
5. **Money** (1 min). Accounts Receivable: who is late, by how much.
6. **Stock to watch** (1 min). The quince batch close to expiry; jars from
   the glassworks under their reorder level, with their purchase orders on
   the way (report "Qté de Stock Projeté"). Quince and, after September, fig jam are no longer
   made: they sell until their stock runs out, then customers are told no.
7. **Arabic and roles** (1 min). Log in as `ventes@…`: Arabic, and only sales
   and payments.

## Code

`dz_core/demo/`: `food.py` and `clothing.py` (the businesses), `workbook.py`
(the import files), `planner.py` (the story), `engine.py` (the documents),
`loader.py` (the steps), `wipe.py`. Tests: `dz_core/tests/test_demo.py`
checks both profiles and their planned stories without a database.
