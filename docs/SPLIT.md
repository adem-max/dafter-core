# Splitting dz_cod and dz_core

**Status: done (19 October 2026).** Nothing is left to move. This file stays
as the record of what moved, what deliberately stays in dz_cod, and the rule
for new work.

dz_core is the base; dz_cod runs on top of it for online sellers
(`required_apps = ["erpnext", "dz_core"]`). The split was done while no
client site was live: moving records between apps on a live site needs
migration patches.

## The rule from now on

- Something every client needs (producers who sell by phone or wholesale
  too) goes in **dz_core** (repo dafter-core).
- Something only an online seller needs (orders, couriers, returns,
  Versements) goes in **dz_cod** (repo dafter-cod).
- dz_core never imports dz_cod. When dz_core needs something from the app on
  top, it offers a hook (example: `dz_restore_check_counted`).

## What moved to dz_core

| dz_core | Came from dz_cod | Notes |
| --- | --- | --- |
| `setup/new_client.py` `run_setup_wizard` | `setup/new_client.py` | dz_cod's `prepare` calls dz_core's first (PR #7, 18 Oct) |
| `setup/tax.py` | `remove_default_vat` | Now a choice: IFU (no TVA) or régime réel (19 % + 9 %). The demo loader uses `unset_default_templates` |
| "Produits finis" warehouse | "Stock principal" | dz_cod's COD Settings use it as the main warehouse; "Retours" stays in dz_cod |
| `setup/restore_check.py` | `setup/restore_check.py` | Counts what every client has. dz_cod adds orders and Versements through two hooks, so dz_cod's copy and its test were deleted (19 Oct) |
| `scripts/backup_offsite.sh`, `scripts/restore_test.sh` | `scripts/` | dz_cod's copies deleted (19 Oct); servers use `apps/dz_core/scripts/` |
| Doctype **DZ Wilaya** (code, name, parent wilaya) and `setup/wilayas.py` (the 69 wilayas, `find_wilaya`) | `dz_cod/doctype/dz_wilaya`, `setup/wilayas.py` | 19 Oct. The rate fields (Livrable, zone, 4 rates, stop desk available) became dz_cod custom fields with the same field names, so no data moved: on a migrated site the records and their rates stay as they were |
| `phone.py` (`normalize_phone`, `is_valid_phone`) and a Customer hook that normalizes `dz_phone` | `cod/phone.py` | 19 Oct. dz_cod's order and phone checks import it from dz_core |
| Customer fields `dz_section` ("Coordonnées"), `dz_phone`, `dz_wilaya` | dz_cod `CUSTOMER_FIELDS` | 19 Oct. The import workbook now fills them (phone normalized, wilaya checked against the list), so imported customers work in COD orders |
| `docs/DEPLOY.md` (server, backups, restore, updates, security, new client) | `docs/DEPLOY.md` | 19 Oct. dz_cod's DEPLOY.md keeps only what COD adds |
| `translations/` (fr, en, ar) for the moved labels | `translations/` | Start of the Phase 1 translations item in ROADMAP.md |

## What stays in dz_cod, and why

| Piece | Why it stays |
| --- | --- |
| Feature switches (`features.py`, `commands.py`, `dz-cod-features`) | Every switch is a COD feature, and the hub (dz_cod_hub) imports `dz_cod.features` and calls `dz-cod-features`. Move the mechanism only when dz_core gets an optional feature of its own, and keep the old command name working for the hub |
| DZ Commune, DZ Stop Desk | They are Yalidine's communes and offices (named by Yalidine's ids), not a courier-neutral list. A neutral commune list is in dz_cod's LATER.md #4; if it is built, it belongs in dz_core |
| Customer `dz_commune`, `dz_address` | The delivery snapshot COD orders copy. Producers use ERPNext's own Address |
| Wilaya rate fields and example rates (`setup/wilayas.py` zones) | Delivery pricing is COD's |
| Demo shop (Encre & Fil) | A COD demo. dz_core gets its own sector demos (ROADMAP Phase 2) |

## How an existing site moves over

Done on every dev site (demo, client1, client2, test; each backed up first)
and checked on a fresh site:

```bash
bench --site <site> install-app dz_core   # if the site predates PR #7
bench --site <site> migrate               # DZ Wilaya now belongs to DZ Core; rates kept as custom fields
```
