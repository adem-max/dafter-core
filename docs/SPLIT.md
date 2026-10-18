# Splitting dz_cod and dz_core

dz_core is the base; dz_cod runs on top of it for online sellers. This file
lists what has moved, what is still to move, and the changes dz_cod needs.
Do the split now, while no client site is live: moving records between apps
on live sites needs migration patches.

## Already in dz_core

| dz_core | Came from dz_cod | Change |
| --- | --- | --- |
| `setup/new_client.py` `run_setup_wizard` | `setup/new_client.py` | Same code |
| `setup/tax.py` | `remove_default_vat` | Now a choice: IFU (no TVA) or régime réel (19 % + 9 %) |
| `setup/restore_check.py` | `setup/restore_check.py` | Counts generic records (invoices, BOMs, work orders) instead of COD ones |
| `scripts/backup_offsite.sh`, `scripts/restore_test.sh` | `scripts/` | Paths point to dz_core |

New in dz_core: sector templates, DZ Core Settings, legal custom fields,
"Facture DZ" and "Bon de livraison DZ", the import workbook.

## Changes to make in dz_cod

1. `hooks.py`: `required_apps = ["erpnext", "dz_core"]`
2. `setup/new_client.py` `prepare()`: call dz_core first, then do only the
   COD part. Roughly:

   ```python
   from dz_core.setup.new_client import prepare as prepare_core


   def prepare(company, abbr, courier=None, features=None, sector="Confection", tax_regime="IFU"):
   	prepare_core(company, abbr, sector, tax_regime)
   	# then: features, Retours warehouse, delivery-fee account, courier, COD Settings
   ```

   Then delete dz_cod's own `run_setup_wizard` and `remove_default_vat`.
3. COD Settings `main_warehouse`: use dz_core's "Produits finis" instead of
   creating "Stock principal". Keep the "Retours" warehouse in dz_cod.
4. `scripts/` and `setup/restore_check.py`: delete the copies in dz_cod once
   the servers use dz_core's (keep dz_cod's restore check if you want the
   COD counts too).
5. `demo/loader.py` and `tests/helpers.py`: they call dz_cod's setup
   functions; point them at dz_core's where those moved, then run dz_cod's
   tests with dz_core installed.
6. `LATER.md`: manufacturing is no longer out of scope, it is the core of
   the new target and lives in dz_core.

## Still to move (later, one at a time, tests green after each)

| Piece | Why it waits |
| --- | --- |
| Wilaya and commune lists (DZ Wilaya, DZ Commune) | DZ Wilaya carries COD delivery rates. Move the list, then add the rate fields from dz_cod as custom fields on it |
| Phone formatting (`cod/phone.py`) and the Customer phone field | Used by dz_cod's phone checks; move when dz_core needs phone numbers itself |
| Feature switches (`features.py`, `commands.py`) | Every switch today is a COD feature. Move the mechanism when dz_core gets its first optional feature |
| `docs/DEPLOY.md` | Server guide is generic; rewrite it for dz_core and keep a COD section in dz_cod |
