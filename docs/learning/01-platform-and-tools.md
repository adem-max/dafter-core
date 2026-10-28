# 01 Platform and tools

What the three apps stand on, and every tool used to build, test, run and
show them.

## Frappe and ERPNext in ten ideas

| Idea | What it is | Oracle EBS equivalent (dafter-cod STUDY_GUIDE §0) |
| --- | --- | --- |
| **bench** | The `~/frappe-bench` folder and the `bench` command that manages it | Application tier: `APPL_TOP`, `adadmin`, `adcmctl` |
| **app** | A Python package under `apps/` (frappe, erpnext, dz_core, dz_cod, dz_hub) | A product top; our apps are your `XX_TOP` |
| **site** | One client: one database, one `sites/<name>/site_config.json`; all sites share the bench's code | One instance |
| **DocType** | A table + its form + its REST API + its permissions, described in one JSON file | A table with its form and API |
| **document** | One record of a DocType (one Sales Order with its item rows) | A row and its child rows |
| **hooks.py** | The app's registration: which of our functions run on which event | Registering a concurrent program or a business event subscription |
| **`bench migrate`** | Syncs doctype JSON to the database, runs patches, then `after_migrate` hooks | `adpatch` + `autoconfig` |
| **workers + scheduler** | Background jobs (`frappe.enqueue`) and timed jobs (`scheduler_events`) on Redis queues | Concurrent managers |
| **docstatus** | 0 draft (editable), 1 submitted (locked, posts stock and ledger), 2 cancelled | Entered / Approved / Cancelled |
| **Workflow** | States and buttons on a doctype, with roles per transition | AME / workflow builder |

The golden rule: never edit `apps/frappe` or `apps/erpnext`. Our code lives
in our apps and `hooks.py` plugs it in, so `bench update` can upgrade ERPNext
without losing our work.

### Anatomy of one of our apps

```
dafter-core/                 the git repo = the Frappe app (bench get-app works on it directly)
  pyproject.toml             package metadata (flit), ruff settings (line 110, py314)
  .pre-commit-config.yaml    checks run before each commit (see "Tools")
  dz_core/                   the Python package
    __init__.py              __version__
    hooks.py                 how the app plugs into Frappe/ERPNext (read it first)
    modules.txt              the module(s) its doctypes belong to ("DZ Core")
    patches.txt              one-off data migrations, run once per site by migrate
    dz_core/                 the module folder: everything Frappe loads from files
      doctype/<name>/        <name>.json (definition), <name>.py (rules), <name>.js (form)
      report/<name>/         Script Report: .json (record), .py (execute), .js (filters)
      print_format/<name>/   print format record (HTML + CSS inside the JSON)
      workspace/, sidebar/, number_card/, dashboard_chart/   the home page, as files
    setup/, imports/, demo/  plain Python called by hooks or by `bench execute`
    translations/            fr.csv, en.csv, ar.csv
    tests/                   test_*.py, run by `bench run-tests`
```

Records shipped as files (doctypes, reports, print formats, workspaces,
number cards, charts, sidebars, docks) are **standard**: `bench migrate`
imports them into every site. That is why a report needs no setup code.

### The hooks we use

| Hook | Meaning | Used in |
| --- | --- | --- |
| `required_apps` | Install these first | dz_core: erpnext; dz_cod: erpnext, dz_core; dz_hub: erpnext |
| `after_install`, `after_migrate` | Run our setup (custom fields, workflow, records) | all three |
| `doc_events` | Call our function on a document event (`before_validate`, `validate`, `before_submit`, `on_update_after_submit`...) | dz_core (Customer), dz_cod (Sales Order, Customer, Supplier, Webhook) |
| `doctype_js` | Extra JavaScript on a standard form | dz_cod (Sales Order, Supplier) |
| `scheduler_events` | Timed jobs | dz_cod (hourly courier sync) |
| `jinja` | Functions usable in print formats | dz_core (`montant`, `montant_en_lettres`), dz_cod (`code128_svg`) |
| `extend_bootinfo` | Add data to `frappe.boot` in the browser | dz_core (`frappe.boot.dz_features`) |
| `add_to_apps_screen` | A tile on the apps screen, and the route of the default app | all three |
| `get_website_user_home_page` | Where a user lands after login | dz_core |
| `default_log_clearing_doctypes` | Old log records deleted after N days | dz_cod (Courier Webhook Event, 30) |
| Our own: `dz_features`, `dz_restore_check_counted`, `dz_restore_check_last` | Read by dz_core with `frappe.get_hooks` | dz_cod declares them |

A typo in `hooks.py` breaks every save of that doctype: read the last line
of the traceback first, then the first line in `apps/dz_*` going up
(STUDY_GUIDE §13).

### The commands you will type most

```bash
bench start                                    # web (8000), socketio (9000), workers, scheduler, Redis
bench --site <site> migrate                    # after any JSON or hooks change
bench --site <site> execute dz_core.setup.new_client.prepare --kwargs "{...}"   # call any function
bench --site <site> console                    # Python shell inside the site
bench --site <site> mariadb                    # SQL shell on the site's database
bench --site <site> run-tests --app dz_core    # tests (site needs allow_tests)
bench --site <site> serve --port 8001          # serve one site on its own port (demos)
bench --site <site> dz-features --list         # our command (dz_core/commands.py)
bench new-site / drop-site / backup / restore / set-maintenance-mode
```

## Versions

ERPNext and Frappe v16 (16.51.1 on the dev bench, 20 October 2026; built on
16.50 and 16.51). Python 3.14, Node 24, MariaDB 10.11, Redis 7, Ubuntu 24.04
(dafter-cod DECISIONS.md "Platform"). v16 details the code relies on:

- Default warehouses moved to the Company (section "Warehouse Defaults"),
  and in 16.51 the general `default_warehouse` too.
- Desk users land on `/desk` after login whatever the default app, hence
  dz_core's login hook.
- Docks put an app's menu on ERPNext's left rail (`dz_core/dock`, `dz_cod/dock`).
- Batch tracking needs Stock Settings `enable_serial_and_batch_no_for_item`.

## Tools

| Tool | Where | What for |
| --- | --- | --- |
| **WSL Ubuntu 24.04** | Windows PC | Runs the bench (`~/frappe-bench`). `apps/dz_core`, `apps/dz_cod`, `apps/dz_hub` are symlinks to the repos on the Windows disk, so an edit in Windows is live on the bench |
| **bench (frappe-bench CLI)** | `~/.local/bin/bench` (uv tool) | Creates sites, runs migrate, tests, the dev server |
| **uv / uvx** | `~/.local/bin` | Installs bench; `uvx ruff@0.14.0` lints with a recent ruff (the bench's own is too old for py314) |
| **MariaDB 10.11** | WSL | One database per site; root password `root` on this PC only |
| **Redis** | started by `bench start` | Cache, job queues, socketio; `new-site` needs it running |
| **honcho** | inside `bench start` | Starts the processes of `Procfile` (web, socketio, workers, schedule, Redis) |
| **git + GitHub** | three repos | `adem-max/dafter-core`, `adem-max/dafter-cod`, `adem-max/dz_adm` (all public). LF line endings, `core.autocrlf=false`, `core.filemode=false` |
| **gh** | Git Bash | Pull requests |
| **pre-commit** | `.pre-commit-config.yaml` in each repo | trailing whitespace, merge markers, `check-ast`, JSON/TOML/YAML checks, no `debug-statements`; **ruff** (lint + import order + format); **prettier** and **eslint** for JS |
| **ruff** | `pyproject.toml` `[tool.ruff]` | Lint rules F, E, W, I, UP, B, RUF; line length 110; tabs (Frappe style) |
| **flit** | `pyproject.toml` build backend | Makes the app a pip-installable package (`bench get-app` runs `pip install -e`) |
| **Frappe test runner** | `bench run-tests` | `IntegrationTestCase` (real database, rolled back per class) and `UnitTestCase` (no database). Sites: `test.localhost` (dz_core, dz_cod), `hub-test.localhost` (dz_hub), with `allow_tests` on |
| **openpyxl** | dz_core import workbook | Reads and writes the client's Excel file |
| **num2words** | dz_core `utils.py` | Amount in French words on invoices |
| **requests** | dz_cod Yalidine connector | HTTP calls to the courier API |
| **rclone** | `~/.local/bin/rclone`, `scripts/backup_offsite.sh` | Copies each night's backups off the server |
| **cron** | server | Runs the daily backup (DEPLOY.md §9) |
| **healthchecks.io** (optional) | `HEALTHCHECK_URL` | E-mails you when the backup stops pinging |
| **cloudflared** | `~/.local/bin/cloudflared` | Cloudflare quick tunnels: public links to local demos (`scripts/demo_tunnels.sh`, docs/DEMO.md) |
| **nginx, supervisor, Let's Encrypt** | production server | `bench setup production`, SSL (DEPLOY.md §6–7; not yet run on a real server) |
| **n8n** | client's choice | Receives dz_cod's order webhooks (dafter-cod docs/WEBHOOKS.md) |
| **Yalidine API** | courier | Parcels, statuses, prices, communes, signed webhooks (dafter-cod docs/COURIER_INTEGRATION.md) |
| **Headless Chromium / the browser pane** | checks | Forms, dialogs and reports checked in a real browser |

### On this PC

```bash
wsl -d Ubuntu-24.04 -- bash ~/start.sh       # bench start
wsl -d Ubuntu-24.04 -- bash -lc 'cd ~/frappe-bench && bench --site test.localhost run-tests --app dz_core'
wsl --terminate Ubuntu-24.04                 # stop everything
```

Sites: `demo.localhost` (shop), `food-demo.localhost`, `atelier-demo.localhost`
(producer demos), `client1/2.localhost`, `test.localhost`, `hub.localhost`,
`hub-test.localhost`. Traps (workspace CLAUDE.md): in Git Bash, `$var` and
quotes inside `wsl ... bash -lc '...'` get mangled, so put commands in a
script with LF endings; a site not migrated after a hooks change serves old
cached hooks; on the hub site `frappe.get_hooks(app_name=...)` and
`frappe.get_attr` refuse the client apps (use plain imports).

## Languages

The apps are written in French for users and English in code. Frappe
translates through `<app>/translations/<lang>.csv` (`source,translation`):

- `fr.csv` gives French names to what is English in code (doctype names,
  report names without accents such as "A acheter" → "À acheter").
- `en.csv` and `ar.csv` translate the French texts for users whose language
  is English or Arabic (User → Language); Frappe mirrors the screen
  right-to-left for Arabic by itself.
- Stored values never change: an order stays "Livrée" in the database and
  shows as "Delivered" in English (dafter-cod DECISIONS.md "Interface").
- dz_cod's `tests/test_translations.py` fails when a French text has no
  English line; dz_core's translations cover the wilaya, contact and report
  labels so far (ROADMAP Phase 1).
