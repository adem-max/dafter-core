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
| 13 weeks (load of 20 Oct) | 154 orders, 150 invoices, 130 work orders, 45 purchases; about 1 100 documents | 78 orders, 79 invoices, 92 work orders, 32 purchases; about 690 documents |

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
`'profile': 'clothing'`. A load takes about 20 minutes (clothing: 15) on the WSL bench
(code on the Windows disk); it prints its steps and a summary at the end.

On a laptop, `bench start` shows only the default site. To open a demo next
to it, without changing anything: `bench --site food-demo.localhost serve
--port 8001`, then http://food-demo.localhost:8001 (clothing: port 8002).
Or make it the default (dafter-cod docs/LOCAL_TEST.md section 5).

## The three demo sites on one bench

The two producer demos above, plus the online shop **Encre & Fil**
(dafter-cod docs/DEMO.md: ERPNext + dz_cod, which installs dz_core first):

```bash
cd ~/frappe-bench
# food producer and clothing workshop (Pack Atelier): "Create a demo site" above
# online shop (Pack Atelier + Vente en ligne), 2 to 5 minutes
bench new-site demo.localhost --install-app erpnext
bench --site demo.localhost install-app dz_cod
bench --site demo.localhost execute dz_cod.demo.loader.load
```

| Site | Pack | Port (`demo_tunnels.sh`) | Owner login |
| --- | --- | --- | --- |
| `food-demo.localhost` | Atelier, régime réel | 8001 | `gerant@food-demo.localhost` |
| `atelier-demo.localhost` | Atelier, IFU | 8002 | `gerant@atelier-demo.localhost` |
| `demo.localhost` | Atelier + Vente en ligne | 8003 | `gerant@demo.localhost` (added by `demo_tunnels.sh`) |

The shop's loader makes no demo login (only `Administrator`, with the
password chosen at `new-site`); `scripts/demo_tunnels.sh` adds
`gerant@demo.localhost` with the manager and user roles of sales, stock and
accounts, password `Demo-2026!`.

## Show the demos from another computer

`scripts/demo_tunnels.sh` serves each demo on its own port and opens a
Cloudflare quick tunnel to each (no account; `cloudflared` in
`~/.local/bin`), then prints one public `https://….trycloudflare.com` link
per site:

```bash
bash ~/frappe-bench/apps/dz_core/scripts/demo_tunnels.sh          # start (bench start must be running)
bash ~/frappe-bench/apps/dz_core/scripts/demo_tunnels.sh stop     # close the links and the demo servers
```

From Windows: `wsl -d Ubuntu-24.04 -- bash ~/frappe-bench/apps/dz_core/scripts/demo_tunnels.sh`.

- The links change at every start, and die when WSL stops or the PC sleeps.
- Anyone with a link reaches the login page: stop the tunnels after the demo.
- Live updates (Frappe's realtime, port 9000) don't go through the tunnel:
  pages, reports and printing work, notifications don't pop up.
- Walking the script changes the data (the shop's steps create delivery
  notes and a Versement): reload, or cancel the test documents afterwards.
- Logs: `~/demo-tunnels/` (one `serve-<port>.log` and `tunnel-<port>.log` per site).

## Logins

| Login | Role in the demo | Language |
| --- | --- | --- |
| `gerant@<site>` | The owner: everything | Français |
| `production@food-demo.localhost`, `atelier@atelier-demo.localhost` | Production and stock | Français |
| `ventes@<site>` | Sales and payments | العربية (to show the Arabic interface) |

Password for all: `Demo-2026!` (demo sites only). `Administrator` keeps the
password chosen at `new-site`. Every login lands on the Atelier home page
(`/desk/atelier`); the factory icon on the left rail opens its menu.

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

Figures from the loads of 20 October 2026 (food / clothing); a later load
moves them a little.

| What | Where |
| --- | --- |
| The day at a glance | Atelier home page (where every login lands): today's sales, orders to deliver, work in progress, materials to buy, overdue invoices (food: 5, 6, 5, 16; clothing: 0, 0, 2, 6, everything ordered is delivered), then sales per month, stock value per warehouse and the materials under their level |
| Their Excel file becomes their data | File (or the Company's attachments) → `import-demo-food-1-donnees….xlsx`; Atelier → Articles, Clients, Nomenclatures |
| Recipes and work orders | Atelier → Nomenclatures, Fabrication (food: six in progress today) |
| What a product costs, and a price rise reaching it | Report "Coût de revient": one row per product (food: 10, average margin 48.5 %; clothing: 6 models, 37.8 %); open a row for its materials at the last purchase price. Strawberry jam 250 g: 140.18 DA of materials + 25 DA labour = 165.18 DA, sold 350 DA, margin 52.8 %; the pulp is at 448 DA/kg since the 18 % rise (1 September, 380 before), and "Dernier lot : coût réel" shows the last batch really cost 165.18 DA (155.83 before the rise). T-shirt: jersey 747 DA/m since 26 August (650 before, +15 %), 593 DA of materials + 150 labour = 743 DA, sold 1 200, margin 38.1 % (batches before the rise: 670.50 DA) |
| Batches and expiry dates, oldest sold first | Stock → Batch; the last quince jam batch (450 g) expires on 14 November |
| Legal invoices | Atelier → Factures → Print: Facture DZ by default, amount in words, legal mentions; one cancelled invoice prints FACTURE ANNULÉE |
| What to buy | Home page chart "À acheter : sous le seuil" and report "À acheter": food, 5 materials under their level (cartons, labels, eucalyptus honey, 250 g and 450 g jars; the 250 g jars at 422 for a level of 1 000, 720 on order from the glassworks, which delivers 8 working days after the order); clothing, denim and fleece from the Oran mill (12 working days). All already ordered, so "À commander" is 0 |
| What to deliver and to make | Report "À produire"; Atelier → Commandes (food: five orders to deliver) |
| Sales per month | Report "Ventes par mois": July to today, per product (or customer, or group). Food 7 724 100 DA HT, October 1 719 580, September against August −31.5 %; clothing 3 956 050 DA HT, October 876 680, −21.8 % |
| Who owes what | Report "Balance âgée clients" (Accounts Receivable): 16 overdue invoices for 1 357 922 DA (clothing: 6, 251 660 DA); Superette Le Panier stopped paying its last invoices |
| Stock value | Report "Valeur du stock": food 3 024 458 DA in 3 warehouses, clothing 5 970 687 DA, equal to ERPNext's Stock Balance |
| Month-end counts | Stock → Stock Reconciliation: a few breakages found |
| Arabic | Log in as `ventes@…`: the whole interface right-to-left, a home page with sales counters only |

## A 10-minute script

Food producer first; the clothing workshop follows the same order with models
and sizes instead of jams. Log in as `gerant@…`: the Atelier home page opens.

1. **"Send us your Excel"** (1 min). Open File, show the two import files.
   Explain: we fill your data once in this file; the import checks every line
   and creates nothing while one line is wrong. Back on the home page: the
   day at a glance, built from that data and 13 weeks of work.
2. **A batch is made** (2 min). Home page → "Fabrication en cours" (6): the
   work orders in progress, their materials already in Travaux en cours. Open
   a completed one: its stock entry, the jars made, the batch number and
   expiry date.
3. **What a jar costs** (2 min). Report "Coût de revient": one line per
   product, cost, selling price and margin. Open "Confiture de fraise 250 g":
   pulp, sugar, pectin, jar, lid, label and carton at their last purchase
   price, 140.18 DA, plus 25 DA labour: 165.18 DA, sold 350 DA. The pulp went
   up 18 % on 1 September (380 → 448 DA/kg): the cost follows at once, and
   "Dernier lot : coût réel" shows the batches made since then really cost
   165.18 DA instead of 155.83. (Clothing: the T-shirt, jersey +15 %, 743 DA
   instead of 670.50.)
4. **The invoice** (2 min). Factures → any paid one → Print: legal mentions,
   TVA 19 %, amount in French words. Then the cancelled one: FACTURE ANNULÉE.
   (Clothing: no TVA, the IFU note at the bottom.)
5. **Money** (1 min). Report "Ventes par mois": 7.7 million DA HT since July,
   which jams and honeys sell, September 31.5 % under August (switch to
   "Client" to see who buys). Then "Balance âgée clients": 16 invoices late,
   who and by how much.
6. **What to buy** (1 min). The home page chart "À acheter : sous le seuil",
   then the report: five materials under their level, all already ordered
   (the 250 g jars: 422 left for a level of 1 000, 720 coming from the
   glassworks). Stock → Batch: the quince batch that expires on 14 November;
   quince and, after September, fig jam are no longer made: they sell until
   their stock runs out.
7. **Arabic and roles** (1 min). Log in as `ventes@…`: Arabic, the same home
   page with sales counters only, and only sales and payments.

## Code

`dz_core/demo/`: `food.py` and `clothing.py` (the businesses), `workbook.py`
(the import files), `planner.py` (the story), `engine.py` (the documents),
`loader.py` (the steps), `wipe.py`. Tests: `dz_core/tests/test_demo.py`
checks both profiles and their planned stories without a database.
