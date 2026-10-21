# 04 dz_hub (repo dz_adm, private)

The vendor's own site to manage every Daftar client: who they are, which
site is theirs, what they pay for (packs and options), their monthly
invoices, and suspension when they don't pay. Installed **only** on the hub
site (`hub.localhost` here), never on a client site. `required_apps =
["erpnext"]`. 22 tests. Renamed from `dz_cod_hub` on 19 October 2026, when it
started managing producers too.

```
dz_adm/
  README.md
  dz_hub/
    hooks.py  hooks_permission.py
    setup.py      what you sell: DZ Feature records, billing items, monthly plans
    billing.py    one ERPNext Subscription per client
    remote.py     actions on a client's site: create, apply options, suspend, reactivate
    patches/      rename_billing.py, clients_were_online_sellers.py (the move from dz_cod_hub)
    dz_hub/doctype/  DZ Client (+ DZ Client Feature), DZ Feature, DZ Hub Settings
    dz_hub/report/   Clients en retard
    tests/test_hub.py
```

## How it fits

The hub never runs code inside a client site. It runs `bench` commands
against each client site **on the same server** and reads what can be sold
from the client apps' code on the bench (they are not installed on the hub
site itself):

```
hub site (ERPNext + dz_hub)
   │  reads dz_core.features.bench_catalog()   -> every app's dz_features (plain imports)
   │  imports dz_core.setup.sectors.SECTORS     -> checks a client's sector
   └─ runs: python -m frappe.utils.bench_helper frappe --site <client site> <command>
              new-site / install-app / execute ...prepare / dz-features --set / set-maintenance-mode
```

On the hub site `frappe.get_hooks(app_name=...)`, `frappe.get_attr` and
`bench execute dz_core...` all refuse the client apps: use plain imports
(workspace CLAUDE.md, traps).

## hooks.py, hooks_permission.py

```python
required_apps = ["erpnext"]
add_to_apps_screen = [{"name": "dz_hub", "title": "Hub DZ", "route": "/desk/dz-client",
                       "has_permission": "dz_hub.hooks_permission.is_system_manager"}]
after_install = "dz_hub.setup.after_install"
after_migrate = "dz_hub.setup.after_migrate"
```

`is_system_manager()`: the tile shows only to System Managers. The hub is for the vendor.

## setup.py — what you sell

**What:** after install and every migrate, one **DZ Feature** per thing you
sell, each with a service Item ("Abonnement - …", group *Abonnements DZ*) and
a monthly Subscription Plan ("DZ - …", Fixed Rate, price 0 until you set it).

```python
PACKS = [
	(BASE, "Pack Atelier", "Production, stock, achats, ventes, factures, import Excel.", CORE_APP, 1),
	(ONLINE, "Vente en ligne", "Commandes COD, transporteurs, retours, versements.", ONLINE_APP, 0),
]

def feature_list():
	from dz_core.features import bench_catalog
	features = [(code, label, description, app, "Pack", is_base) for ... in PACKS]
	features += [(code, f["label"], f["description"], f["app"], "Option", 0)
	             for code, f in bench_catalog().items()]       # today dz_cod's four
	return features
```

- `BASE = "base"` (Pack Atelier, always billed), `ONLINE = "vente_en_ligne"`.
- A new feature declared by an app becomes a new option on the next hub migrate.
- Existing records are never overwritten (your labels and prices stay); only
  `kind` and `app` are filled on older records.
- Skips everything until the hub's setup wizard made a company.

## DZ Feature, DZ Hub Settings

| Doctype | Fields |
| --- | --- |
| **DZ Feature** (named by `code`) | code, label, kind (Pack / Option), app, is_base, item, subscription plan, description |
| **DZ Hub Settings** (single) | company that bills, days until due, tolerance days (*Clients en retard*), MariaDB root password (only for *Créer le site*) |

## DZ Client (`dz_client.py`, `dz_client.js`)

**What:** one per client: the ERPNext Customer to bill, the site name,
status (Actif / Suspendu / Résilié), start date, *Vente en ligne* ticked or
not, the options (child table **DZ Client Feature**), company and
abbreviation, sector and tax regime (passed to dz_core's `prepare`), first
courier, admin password, and what the last action did (subscription, site
created, applied features and date, last action, log).

```python
def validate(self):
	self.site_name = (self.site_name or "").strip().lower()
	check_site_format(self.site_name)
	if any(row.feature == ONLINE for row in self.features):
		self.online_sales = 1                 # packs are fields, not options
	self.features = [row for row in self.features if row.feature not in (BASE, ONLINE)]
	self.check_options()                      # a dz_cod option needs "Vente en ligne"
	self.check_sector()                       # against dz_core's SECTORS, IFU / REEL (plain imports)

def apps(self):
	return [CORE_APP, ONLINE_APP] if self.online_sales else [CORE_APP]

def on_update(self):
	changed = any(self.has_value_changed(f) for f in ("features", "status", "online_sales"))
	if changed or not self.subscription:
		sync_subscription(self)               # billing.py
```

The form's buttons (group *Site*) call `dz_hub.remote.start(client, action)`:
*Créer le site*, *Appliquer au site*, *Suspendre* / *Réactiver*, and
*Mettre à jour l'abonnement*. An orange banner shows when the site's applied
features differ from what the client pays for.

## billing.py — monthly invoices with ERPNext's Subscription

```python
def plans_for(client):
	codes = [BASE] + ([ONLINE] if client.online_sales else [])
	codes += [row.feature for row in client.features if row.feature not in (BASE, ONLINE)]
	return [frappe.db.get_value("DZ Feature", code, "subscription_plan") for code in codes]

def sync_subscription(client):
	# Résilié -> cancel the Subscription. Otherwise create or update it:
	# party = the Customer, monthly from the start date, submit_invoice = 1,
	# invoice at the beginning of the period, days_until_due from DZ Hub Settings,
	# plans = plans_for(client), one line each
```

ERPNext's daily job turns each Subscription into one Sales Invoice a month
(one line per plan); an unpaid invoice past its due date becomes "Overdue".

## report Clients en retard

Clients with an Overdue invoice, minus the tolerance days of DZ Hub Settings.
Suspension stays a manual click on the client.

## remote.py — actions on a client's site

**What:** each action is a background job (queue "long") that runs `bench`
for the client's site **in a separate process**, exactly like typing it:
a site's config and cache can only be changed safely from that site's own
process. The output goes into the client's *Journal de la dernière action*.

```python
def run_bench(site, args, timeout=300):
	command = [sys.executable, "-m", "frappe.utils.bench_helper", "frappe", "--site", site, *args]
	result = subprocess.run(command, cwd=f"{get_bench_path()}/sites",
	                        capture_output=True, text=True, timeout=timeout, check=False)
	if result.returncode != 0:
		raise BenchError(output[-4000:])
	return output
```

An argument list, no shell, and site names checked against
`^[a-z0-9]([a-z0-9.-]*[a-z0-9])?$`: nothing a user types can become a shell command.

| Action | What it runs |
| --- | --- |
| `do_create_site` | `new-site <site> --mariadb-root-password … --admin-password … --install-app erpnext`; `install-app dz_cod` (online seller: it installs dz_core first) or `install-app dz_core`; `prepare(client)`; `dz-features --set … --json`; `enable-scheduler`. Local bench only: DNS, nginx and SSL stay manual (DEPLOY.md §7) |
| `do_apply_features` | refuses a site without dz_core; installs dz_cod and runs its prepare if the client took *Vente en ligne* since; never uninstalls dz_cod (that would delete orders), only switches its options off; then `dz-features --set` |
| `do_suspend` / `do_reactivate` | `set-maintenance-mode on` / `off`, status Suspendu / Actif |

```python
def prepare(client):
	kwargs = {"company": client.company_name, "abbr": client.company_abbr,
	          "sector": client.sector or "Confection", "tax_regime": client.tax_regime or "IFU"}
	if client.online_sales:
		kwargs.update({"courier": client.courier or None, "features": features_of(client)})
		return ["execute", "dz_cod.setup.new_client.prepare", "--kwargs", json.dumps(kwargs)]
	return ["execute", "dz_core.setup.new_client.prepare", "--kwargs", json.dumps(kwargs)]

def set_features(client):
	output = run_bench(client.site_name, ["dz-features", "--set", ",".join(features_of(client)), "--json"])
	answer = json.loads(output.strip().splitlines()[-1])   # what the site really has now
	return output, sorted(name for name, on in answer["features"].items() if on)
```

`start()` is whitelisted, `frappe.only_for("System Manager")`, checks write
permission and enqueues `run_action` after commit. `run_action` runs under a
savepoint: a failed command is logged on the client and changes nothing else.

## patches/

Run once by `bench migrate` on a hub that ran the old `dz_cod_hub`:
`rename_billing` (*Abonnements DZ COD* → *Abonnements DZ*, `DZCOD-…` → `DZ-…`,
*Base COD* → *Pack Atelier*), `clients_were_online_sellers` (ticks *Vente en
ligne* on old clients: the old hub only made dz_cod sites).

## tests/test_hub.py (and test_version.py: refused on a dz_core older than `DZ_CORE_MIN`)

`bench --site hub-test.localhost run-tests --app dz_hub`. The `bench` calls
are mocked: no site is created or changed. Tests: two packs and one option
per app feature; the subscription follows the features; an Atelier-only
client pays the base pack; COD options need the online pack; packs are not
options; one monthly invoice with one line per plan; an overdue invoice lists
the client; a cancelled client cancels the subscription; site names are
checked; `run_bench` uses an argument list without shell; apply records what
the site answered; suspend and reactivate; a failed command is logged and
changes nothing; create site for an online seller / for a producer (dz_core
only); taking the online pack later adds dz_cod.

## Daily use (README)

1. New client: Customer → DZ Client (site, *Vente en ligne* or not, options,
   company + abbreviation, sector, tax regime, first courier) → *Créer le site*.
2. Change of offer: edit the client → save (the Subscription follows) → *Appliquer au site*.
3. Each month ERPNext makes the invoices; record payments as usual.
4. *Clients en retard* → open the client → *Suspendre*; after payment → *Réactiver*.
