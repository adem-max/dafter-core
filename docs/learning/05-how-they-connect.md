# 05 How the three apps work together

Six flows that cross app boundaries, traced through the files of chapters
02–04. If you can tell each of them from memory, you know the system.

## 1. A new client

```
hub: DZ Client saved ─► billing.sync_subscription ─► ERPNext Subscription (Pack Atelier [+ Vente en ligne] + options)
hub: "Créer le site" ─► remote.start ─► job remote.run_action ─► do_create_site
   bench new-site <site> --install-app erpnext
   bench --site <site> install-app dz_core | dz_cod          (dz_cod's required_apps installs dz_core first)
        └─ dz_core.setup.install.after_install: custom fields, 69 wilayas, features
        └─ dz_cod.setup.install.after_install: COD fields, workflow, rates, webhooks, home block, features
   bench --site <site> execute dz_core.setup.new_client.prepare          (producer)
                       or  dz_cod.setup.new_client.prepare              (online seller)
        └─ dz_cod's prepare calls dz_core's prepare first:
             wizard (French, Algeria, DZD, Algerian chart) → sector → tax regime → opening account
             → print formats → address template → Atelier home page → DZ Core Settings
           then adds: Retours warehouse, "Frais de livraison facturés", COD Settings, courier, features,
             COD as home page
   bench --site <site> dz-features --set <options> --json                 (dz_core/commands.py)
   bench --site <site> enable-scheduler
```

Then by hand: the Company's legal mentions, users, and the client's data
through the import workbook (`make_template` → client fills it →
`import_workbook` dry run → `dry_run: 0`). For an online seller: the courier
rate card in the wilaya list, then the webhooks if they use n8n.
Without the hub, the same steps are typed (README of each repo, DEPLOY.md §13).

## 2. A feature switch

```
hub: tick an option on DZ Client, save (Subscription follows), "Appliquer au site"
  └─ remote.do_apply_features ─► bench --site <site> dz-features --set a,b --json
       └─ dz_core.features.set_features(["a", "b"])
            writes site_config.json "dz_features"
            apply_features():
              Report.disabled / Print Format.disabled for each feature's records
              feature["on_change"](on)  e.g. dz_cod.features.apply_webhooks
  └─ the JSON answer (what the site really has) is stored on the client: applied_features
browser: next page load, frappe.boot.dz_features (hook extend_bootinfo) hides buttons
server:  @requires_feature / is_enabled refuse with "Fonction non incluse dans votre offre"
migrate: after_migrate re-runs apply_features (migrate re-imports standard reports as enabled)
```

Who owns what: dz_core owns the mechanism (`features.py`, the command, the
boot data); dz_cod owns its four features (`FEATURES`) and their guards;
the hub owns who pays for which, and reads the catalogue with
`bench_catalog()` (plain imports, because the apps are not installed on the
hub site). Key missing in site_config = the base only; `"all"` = everything
(demo and test sites).

## 3. Login and the home page

```
prepare()  ─► System Settings default_app = dz_core          (dz_core/setup/new_client.py)
dz_cod's prepare ─► default_app = dz_cod                       (online sellers land on COD)
login ─► hook get_website_user_home_page ─► home_page_after_login(user)
           System User + a default app (user's or site's) ─► frappe.apps.get_default_path()
           ─► the app's add_to_apps_screen route: /desk/atelier or /desk/cod
the page ─► workspace + number cards + dashboard charts (shipped as files, loaded by migrate)
the rail ─► Dock records mount Atelier (and COD) on ERPNext's left rail
```

Frappe 16 alone sends desk users to `/desk`; the hook is why they land on
their app. Cards and charts show only to users who can read their doctype
or report.

## 4. A COD order (online seller site)

```
draft save      dz_cod.cod.order.before_validate   phone normalized (dz_core.phone), courier, warehouse,
                                                   fee from DZ Wilaya rates (dz_cod fields on a dz_core doctype)
                dz_cod.cod.order.validate          amount to collect; refused-parcel warning (feature)
Confirmer       workflow submit ─► before_submit   phone / wilaya / address checks, courier check_order,
                                                   stock check; ERPNext reserves stock
                                                   webhook "COD - Confirmée" (feature n8n_webhooks)
Préparer        workflow, no code
Expédier        sales_order.js dialog ─► set_shipping_details ─► workflow
                before_update_after_submit ─► prepare_shipment ─► adapter.create_shipment (Yalidine…)
                on_update_after_submit ─► Delivery Note submitted (stock out)
Livrée          by hand, hourly couriers/sync.py, or a Yalidine webhook (if automatic sync is on)
Retournée       return Delivery Note into Retours, order closed; then "Inspecter le retour":
                good ─► Material Transfer to main, damaged ─► Material Issue
Réglée          Courier Settlement submitted: OK lines press "Marquer réglée"
```

Nothing posts a Sales Invoice yet (dafter-cod LATER.md #1): COD revenue is
not in the ledger. On a site with dz_cod, every Sales Order goes through
this workflow, wholesale ones included (dafter-core DECISIONS.md).

## 5. Backups and the restore drill

```
cron 02:30 ─► dz_core/scripts/backup_offsite.sh
               bench --site <each site> backup --with-files --compress
               rclone copy last 24 h ─► offsite:erp-backups/<host>/<site>
               delete local > 7 days, only after a good copy; ping HEALTHCHECK_URL
monthly    ─► dz_core/scripts/restore_test.sh <site>
               new restore-test.localhost ← latest backup, original encryption_key, migrate
               bench execute dz_core.setup.restore_check.summary on both sites
                  COUNTED + frappe.get_hooks("dz_restore_check_counted")   ← dz_cod adds Sales Order, Courier Settlement
                  LAST    + frappe.get_hooks("dz_restore_check_last")      ← dz_cod adds Sales Order
                  passwords that do not decrypt
               compare, RESTORE TEST OK / FAILED, drop the test site
```

The hooks are how dz_core checks dz_cod's records without importing dz_cod.

## 6. The three demos

| Demo | Site | Apps | Built by |
| --- | --- | --- | --- |
| Les Délices de la Mitidja (food, régime réel) | `food-demo.localhost` | ERPNext + dz_core | `dz_core.demo.loader.load(profile="food")` |
| Atelier Nour Confection (clothing, IFU) | `atelier-demo.localhost` | ERPNext + dz_core | `dz_core.demo.loader.load(profile="clothing")` |
| Encre & Fil (online shop) | `demo.localhost` | ERPNext + dz_core + dz_cod | `dz_cod.demo.loader.load()` |

```
dz_core demos:  prepare() ─► import workbook (the client's door) ─► planner.py (pure Python story)
                ─► engine.py (real documents, backdated, in date order, each event once)
dz_cod demo:    setup ─► items, customers, Mock couriers ─► 200 order stories replayed
                through the real workflow (order.flags.dz_event_date) ─► weekly Versements
show remotely:  dz_core/scripts/demo_tunnels.sh ─► bench serve per site (8001–8003)
                ─► one Cloudflare quick tunnel each ─► three https://….trycloudflare.com links
```

Both loaders refuse a site that holds another company's data, skip what
exists, and continue the story when run again later. Walkthroughs:
dafter-core docs/DEMO.md (10-minute producer script) and dafter-cod
docs/DEMO.md (10-minute shop script).

## Where a change goes

| You want to… | Repo / file |
| --- | --- |
| Add a field every client needs (legal mention, customer data) | dafter-core `setup/custom_fields.py` (search both repos for the name first) |
| Add a sector | dafter-core `setup/sectors.py` `SECTORS` (+ a demo profile if it is shown) |
| Add a producer report | dafter-core `dz_core/dz_core/report/<name>/`, helpers in `reports.py`, translation in `translations/fr.csv` |
| Change what happens when an order moves | dafter-cod `cod/order.py`; who may move it: `setup/workflow.py` |
| Add a courier | dafter-cod `couriers/<name>.py` with the three methods, one line in `ADAPTERS` |
| Add an optional feature | the app's `features.py` `FEATURES` (+ guards, + `frappe.boot.dz_features` in JS, + tests); the hub picks it up on migrate |
| Sell something new / change billing | dz_adm `setup.py` (packs), prices on the Subscription Plans |
| Something dz_core needs from an app on top | a new hook name read with `frappe.get_hooks(...)` in dz_core, declared in the app's hooks.py, never an import |
