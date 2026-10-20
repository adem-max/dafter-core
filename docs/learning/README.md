# Learning the Daftar code

A guided walk through the three Daftar apps on ERPNext v16: what each one
is for, the tools around them, every file, and the few lines in each file
that you need to understand. Compiled on 20 October 2026 from the code and
docs already in the repos (READMEs, DECISIONS.md, docs/, docstrings). When
this guide and the code disagree, the code is right: fix the guide.

| Chapter | What |
| --- | --- |
| [01 Platform and tools](01-platform-and-tools.md) | Frappe, ERPNext, bench, sites, doctypes, hooks; the tools used (WSL, MariaDB, Redis, git, ruff, pre-commit, rclone, cloudflared...) |
| [02 dz_core (dafter-core)](02-dz-core.md) | The base every client gets: setup, sectors, tax, legal invoices, import workbook, reports, home page, features, backups, demos |
| [03 dz_cod (dafter-cod)](03-dz-cod.md) | Online sellers: COD order workflow, stock, shipping fees, couriers, Versements, webhooks, reports, demo shop |
| [04 dz_hub (dz_adm)](04-dz-hub.md) | The vendor's hub: clients, packs and options, billing, actions on client sites |
| [05 How they work together](05-how-they-connect.md) | End-to-end flows across the three apps: a new client, a feature switch, login, an order, a backup, a demo |

## The three apps in one picture

```
frappe    framework: doctypes, forms, permissions, REST API, jobs      (never edited)
erpnext   stock, sales, purchases, manufacturing, accounting           (never edited)
dz_core   repo dafter-core   every client (Pack Atelier)               public
dz_cod    repo dafter-cod    online sellers (Pack Vente en ligne)      public, needs dz_core
dz_hub    repo dz_adm        the vendor's own site                     private, only on the hub site
```

- A **producer** site has ERPNext + dz_core.
- An **online seller** site has ERPNext + dz_core + dz_cod.
- The **hub** site has ERPNext + dz_hub; dz_core and dz_cod sit on the same
  bench (their code is there), but are not installed on the hub site.

The rules that shape every file (dafter-core DECISIONS.md, dafter-cod README):

1. ERPNext and Frappe are never edited: custom fields, hooks, settings,
   setup code and print formats in our apps only, so `bench update` stays safe.
2. What every client needs goes in dz_core; only online-sales work goes in dz_cod.
   dz_core never imports dz_cod: when it needs something from an app on top,
   it offers a hook (`dz_features`, `dz_restore_check_counted`, `dz_restore_check_last`).
3. Per-client differences live in settings (DZ Core Settings, COD Settings,
   site_config `dz_features`), never in `if client == ...` code.
4. Setup is code, not fixtures: it creates what is missing and never
   overwrites what a client changed. Safe to run on every `bench migrate`.
5. Standard doctypes first; a new doctype only when nothing fits (each one is
   justified in a DECISIONS.md).
6. English in code, French for users; English and Arabic by translation files.

## How to read this guide

Each file entry gives **what it does**, **who calls it**, and when it
matters, **the lines that matter**. Read with the file open next to it.

A suggested order, about four weeks of evenings (it extends the plan in
dafter-cod docs/STUDY_GUIDE.md §14 to the three repos):

| Week | Read | Do |
| --- | --- | --- |
| 1 | Chapter 01, chapter 02 up to "Import workbook" | Create a test client site with `prepare()`, fill the import workbook, import it. Walk the food demo with docs/DEMO.md |
| 2 | Rest of chapter 02, chapter 05 §"Login" and §"Backups" | Open each producer report next to its `.py`. Run `restore_test.sh` on a site. Run the dz_core tests |
| 3 | Chapter 03, with dafter-cod docs/STUDY_GUIDE.md chapters 0, 3, 4, 7 | Walk the shop demo script; do the "break it on purpose" exercises of the study guide; run the dz_cod tests |
| 4 | Chapter 04, chapter 05 §"A new client" and §"A feature switch" | On hub-test, create a DZ Client, change its options, *Appliquer au site*; run the dz_hub tests |

Done when (dafter-core ROADMAP Phase 1): you can explain `prepare()` and
`import_workbook()` step by step without opening them, and say for any file
what it does and what calls it.

## Other docs this guide draws on

| Repo | File | For |
| --- | --- | --- |
| dafter-core | README.md, ROADMAP.md, DECISIONS.md | What exists, what is next, why |
| dafter-core | docs/DEMO.md | The producer demos, the three demo sites, public links |
| dafter-core | docs/DEPLOY.md | Ubuntu server, sites, SSL, backups, restore, updates, security |
| dafter-core | docs/SPLIT.md | What moved from dz_cod to dz_core, and the rule since |
| dafter-cod | docs/STUDY_GUIDE.md | **The deep course on dz_cod**: mental models, exercises, failure modes |
| dafter-cod | docs/FEATURES.md, WEBHOOKS.md, COURIER_INTEGRATION.md, LOCAL_TEST.md, DEPLOY.md, DEMO.md | One topic each |
| dafter-cod | DECISIONS.md, LATER.md | Why, and what is not built yet |
| dz_adm | README.md | The hub: install, daily use, the move from dz_cod_hub |
| workspace | `C:\Users\ademb\Documents\daftar erp\CLAUDE.md` | Where the code runs on this PC, sites, traps |
