# 02 dz_core (repo dafter-core)

The base every client gets (Pack Atelier): one-command setup, sector
templates, the tax regime, legal invoices, the Excel import workbook, the
69 wilayas, phone numbers, producer reports, the Atelier home page, the
optional-feature switches, backups and the two producer demos.
`required_apps = ["erpnext"]`. 68 tests (13 unit + 55 integration).

```
dafter-core/
  README.md  ROADMAP.md  DECISIONS.md      what, what next, why
  docs/DEMO.md DEPLOY.md SPLIT.md learning/
  scripts/                                  backup_offsite.sh, restore_test.sh, demo_tunnels.sh
  dz_core/
    hooks.py  commands.py  features.py  utils.py  phone.py  reports.py
    setup/      install.py new_client.py sectors.py tax.py accounts.py custom_fields.py wilayas.py restore_check.py
    imports/    workbook.py
    demo/       loader.py planner.py engine.py workbook.py wipe.py food.py clothing.py
    dz_core/    doctype/ report/ print_format/ workspace/ sidebar/ number_card/ dashboard_chart/
    dock/       the Atelier icon on ERPNext's rail
    translations/  tests/
```

Start with `hooks.py`, then `setup/new_client.py` (the `prepare()` story),
then `imports/workbook.py`. Everything else hangs off those three.

---

## hooks.py

**What:** how dz_core plugs into Frappe. Short; read it first.

```python
required_apps = ["erpnext"]
add_to_apps_screen = [{"name": "dz_core", "title": "Atelier", "route": "/desk/atelier", ...}]
get_website_user_home_page = "dz_core.setup.new_client.home_page_after_login"
after_install = "dz_core.setup.install.after_install"
after_migrate = "dz_core.setup.install.after_migrate"
extend_bootinfo = ["dz_core.features.boot"]
doc_events = {"Customer": {"validate": "dz_core.phone.normalize_customer_phone"}}
jinja = {"methods": ["dz_core.utils.montant", "dz_core.utils.montant_en_lettres"]}
```

- `after_install` / `after_migrate`: every migrate re-runs our setup (custom
  fields, wilayas, features). That is why setup must be idempotent.
- `get_website_user_home_page`: Frappe 16 sends desk users to `/desk`; this
  sends them to the default app's page (Atelier, or COD on a dz_cod site).
- `extend_bootinfo`: the browser gets `frappe.boot.dz_features`, the list of
  features this site has, so JS can hide buttons.
- `jinja`: `montant()` and `montant_en_lettres()` become callable inside
  print formats.

## setup/install.py

**What:** runs after `install-app dz_core` and after every `bench migrate`.
**Called by:** hooks `after_install`, `after_migrate`.

```python
def setup_all():
	setup_custom_fields()
	setup_wilayas()
	move_legacy_key()      # site_config "dz_cod_features" -> "dz_features"
	apply_features()       # reports / print formats match the site's list
	frappe.db.commit()
```

The client-specific part (company, sector, tax) is not here: it is
`new_client.prepare`, run once per client.

## setup/new_client.py — `prepare()`

**What:** prepares a fresh client site in one command. **Called by:** you
(`bench execute`), dz_cod's own `prepare` (which calls this first), the hub's
*Créer le site*, the demo loader.

```bash
bench --site client1.localhost execute dz_core.setup.new_client.prepare \
    --kwargs "{'company': 'Miel Atlas', 'abbr': 'MA', 'sector': 'Alimentaire et cosmétique', 'tax_regime': 'IFU'}"
```

```python
def prepare(company, abbr, sector, tax_regime=IFU):
	run_setup_wizard(company, abbr)            # French, Algeria, DZD, Algerian chart of accounts
	warehouses = apply_sector(sector, company) # sectors.py: groups, units, attributes, 3 warehouses
	apply_tax_regime(company, tax_regime)      # tax.py: IFU = no TVA, réel = 19 % + 9 %
	opening_account(company)                   # accounts.py: "Ouverture temporaire"
	set_default_print_formats()                # Facture DZ, Bon de livraison DZ
	allow_printing_cancelled()                 # so FACTURE ANNULÉE can print
	set_address_template()                     # Algerian address, no "Algeria" line
	make_atelier_the_home_page()               # System Settings default_app = dz_core
	settings = frappe.get_doc("DZ Core Settings")
	settings.update({"company": company, "sector": sector, "tax_regime": tax_regime, **warehouses})
	...
	set_default_accounts(company)              # accounts.py: SCF defaults instead of the wizard's picks
```

Step by step, the part to be able to tell without opening the file:

1. **`run_setup_wizard`** calls Frappe's own `setup_complete()` with
   `language "Français"`, `country "Algeria"`, `timezone "Africa/Algiers"`,
   `currency "DZD"`, the chart "Algerie - Plan Comptable General 2 avec
   code" and a calendar fiscal year. If the wizard already ran, it only
   checks that the company exists under this exact name (else a French
   error listing the site's companies). Saving Global Defaults as a document
   also sets every user's default company.
2. **`apply_sector`** (below) creates the trade's item groups, units,
   attributes, the three warehouses, and which group is stored where.
3. **`apply_tax_regime`** (below).
4. **`opening_account`**: the Algerian chart has no "Temporary" account and
   ERPNext's opening stock refuses to post without one.
5. **`set_default_print_formats`**: a Property Setter `default_print_format`,
   unless the client already chose one (a non-system Property Setter):

   ```python
   chosen = frappe.db.exists("Property Setter",
       {"doc_type": doctype, "property": "default_print_format", "is_system_generated": 0})
   if not chosen:
       make_property_setter(doctype, None, "default_print_format", print_format, "Data", for_doctype=True)
   ```
6. **`allow_printing_cancelled`**: Print Settings `allow_print_for_cancelled = 1`.
7. **`set_address_template`**: replaces ERPNext's stock "Algeria" template
   (which ends with "Algeria" in English) only if nobody edited it.
8. **`make_atelier_the_home_page`**: `default_app = dz_core`, then clears the
   System Settings caches so it applies at once.
9. **DZ Core Settings** gets company, sector, regime, the three warehouses,
   and for IFU the invoice note `IFU_NOTE`.

Stays manual: the Company's legal mentions, users, then the client's data
through the import workbook.

**`home_page_after_login(user)`**: for a System User, when the site or the
user has a default app, returns `frappe.apps.get_default_path()`; website
users and guests keep Frappe's rules (return `None`).

## setup/sectors.py

**What:** sector templates as plain data plus `apply_sector()`. Adding a
sector = one more entry in `SECTORS`, no new code.

```python
SECTORS = {
	FOOD: {        # "Alimentaire et cosmétique"
		"item_groups": ["Matières premières", "Emballages", "Produits finis"],
		"uoms": [("Pot", 1), ("Flacon", 1), ("Sachet", 1), ("Carton", 1), ("Bocal", 1), ("Barquette", 1)],
		"batch_groups": ["Matières premières", "Produits finis"],   # batch + expiry by the importer
		"item_attributes": {},
		"stock_settings": {"enable_serial_and_batch_no_for_item": 1},
	},
	CLOTHING: {    # "Confection"
		"item_groups": ["Tissus", "Fournitures", "Emballages", "Produits finis"],
		"uoms": [("Pièce", 1), ("Rouleau", 1), ("Carton", 1), ("Cône", 0)],   # 0 = fractions allowed
		"item_attributes": {"Taille": [...XS..XXL], "Couleur": [("Noir", "NOI"), ...]},
		...
	},
}
WAREHOUSES = [("Matières premières", "raw_materials_warehouse"),
              ("Travaux en cours", "wip_warehouse"), ("Produits finis", "finished_goods_warehouse")]
```

`apply_sector` creates what is missing only, then:
- `setup_company_warehouses`: Company `default_wip_warehouse` /
  `default_fg_warehouse` (v16 keeps them on the Company), only when empty;
- `setup_item_group_warehouses`: an Item Group default per company: groups in
  `FINISHED_GROUPS` go to Produits finis, every other group to Matières premières;
- `remove_wizard_item_groups`: deletes the wizard's English groups (Products,
  Raw Material, Sub Assemblies, Consumable) unless an item or anything else
  uses them (`LinkExistsError` is caught). "Services" stays.

Why "Cône" allows fractions: a T-shirt uses about 0.02 of a cone of thread,
and ERPNext refuses a fraction of a whole-number unit in a BOM.

## setup/tax.py

**What:** IFU or régime réel.

```python
def apply_tax_regime(company, regime):
	if regime == IFU:
		unset_default_templates(company)          # no TVA by default
	elif regime == REEL:
		set_default_templates(company)            # the wizard's 19 % template is the default
		create_reduced_rate_templates(company)    # a 9 % copy if the site has none
```

`template_with_rate(doctype, company, rate)` finds a template whose only
rate is `rate`. `IFU_NOTE = "Contribuable soumis à l'IFU : TVA non facturée."`
(editable in DZ Core Settings). Not built, waiting for the accountant: stamp
duty on cash, G50 helper, IFU turnover report.

## setup/accounts.py

`opening_account(company)`: the company's leaf account of type "Temporary",
else creates "Ouverture temporaire" under the liability root. Used by the
opening stock import and the demos.

`set_default_accounts(company)`: the setup wizard fills the Company's
default accounts with the last account of each type in the Algerian chart
(receivables in 4172, the bank in 5176, stock in 3451...). This puts the SCF
accounts there by number (`COMPANY_ACCOUNTS`: 4111, 40132, 5121, 5311, 4081,
35511, 6031, 7011, 7245, 6588, 6812, 2328), only where the wizard's pick or
nothing is, so a choice someone made is kept. It adds 35511 "Produits finis"
(the chart has no ledger for finished goods), gives the three warehouses
311 / 3311 / 35511, and moves the modes of payment that pointed to the old
cash or bank account. Patch `scf_default_accounts` did the same on existing
sites. DECISIONS.md "Default accounts" lists what the accountant must confirm.

## setup/custom_fields.py

**What:** the legal mentions of decree 05-468 and the Customer's phone and
wilaya, as Custom Fields. All start with `dz_` and must never clash with
dz_cod's (search both repos before adding one).

| Doctype | Fields |
| --- | --- |
| Company | section "Mentions légales (facture)": `dz_legal_form` (Auto-entrepreneur … SPA), `dz_activity`, RC or AE card, NIF, NIS, AI, capital |
| Customer | section "Coordonnées": `dz_phone`, `dz_wilaya` (Link DZ Wilaya); legal section: `dz_rc`, `dz_nif`, `dz_nis`, `dz_ai` |
| Sales Invoice | `dz_payment_mode` (Espèces, Chèque, Virement, CCP / BaridiMob, Carte (TPE), À terme), `allow_on_submit` |

```python
create_custom_fields({"Company": COMPANY_FIELDS, "Customer": CUSTOMER_FIELDS,
                      "Sales Invoice": SALES_INVOICE_FIELDS}, update=True)
```

`update=True` makes it safe on every migrate: existing fields are updated,
not duplicated.

## setup/wilayas.py

**What:** the 69 wilayas (58 of law 84-09 + 11 of law 26-06 / decree 26-206,
2026), each 2026 wilaya with its parent, and `find_wilaya()`.

```python
WILAYAS = [("01", "Adrar", None), ..., ("16", "Alger", None), ..., ("59", "Aflou", "03"), ...]

def find_wilaya(text):
	"""The DZ Wilaya record for "16", "16 - Alger" or "Alger" (accents and case ignored)."""
	if frappe.db.exists("DZ Wilaya", text): return text
	if text.isdigit(): return frappe.db.get_value("DZ Wilaya", {"code": text.zfill(2)})
	wanted = simplify(text)          # "Béjaïa" -> "bejaia"
	...
```

Record names are "16 - Alger" (`wilaya_docname`). `setup_wilayas` makes the
69 then, in a second pass, sets the parents. The parents of 59–69 come from
press reports: to check against the Journal officiel. dz_cod adds the
delivery rates to each wilaya as custom fields.

## setup/restore_check.py

**What:** what `scripts/restore_test.sh` compares between a live site and
its restored copy: counts per doctype, the newest invoice, and whether every
stored password decrypts with the site's `encryption_key`.

```python
COUNTED = ["Sales Invoice", "Delivery Note", "Purchase Receipt", "Work Order", "BOM", "Customer",
           "Supplier", "Item", "Stock Ledger Entry", "GL Entry", "File", "User"]
def with_hooks(names, hook):
	return names + [name for name in frappe.get_hooks(hook) if name not in names]
```

An app on top adds its records by hook, without dz_core knowing it
(`dz_restore_check_counted`, `dz_restore_check_last`; dz_cod adds Sales
Order and Courier Settlement). This is rule 2 in practice.

## phone.py

**What:** Algerian phone numbers, pure Python. **Called by:** the Customer
`validate` hook, the import workbook, dz_cod's order and phone checks.

```python
MOBILE = re.compile(r"^0[567]\d{8}$")     # Ooredoo, Mobilis, Djezzy
LANDLINE = re.compile(r"^0[1-4]\d{7}$")   # 9 digits

def normalize_phone(phone):
	digits = re.sub(r"\D", "", phone)
	if digits.startswith("00213"): digits = "0" + digits[5:]
	elif digits.startswith("213"): digits = "0" + digits[3:]
	if is_valid_phone(digits): return digits
	return phone.strip()          # never destroy what the operator typed
```

## utils.py

**What:** the two Jinja helpers of the print formats.

- `montant_en_lettres(32400.5)` → "trente-deux mille quatre cents dinars
  algériens et cinquante centimes". Always French (`num2words(lang="fr")`),
  whatever the user's language; adds "de" after million/milliard.
- `montant(32400)` → "32 400,00" (`fmt_money(..., format="# ###,##")`).

## features.py and commands.py — the optional features

**What:** the mechanism of à-la-carte features. The features themselves
belong to the apps that declare them (dz_cod has four; dz_core none yet).
Rules in dafter-cod docs/FEATURES.md.

An app declares them in its hooks.py: `dz_features = ["dz_cod.features.FEATURES"]`.
The site's list lives in `site_config.json`, key `dz_features`, so only the
vendor can change it.

```python
def enabled():
	known = catalog()                 # merge of every installed app's dz_features dicts
	value = configured()              # the list in site_config, "all", or None
	if value is None:
		return set()                  # key missing = the base only
	if value == ALL:
		return set(known)             # "all": demo and test sites
	return {name for name in value if name in known}

def requires_feature(feature):        # decorator, put UNDER @frappe.whitelist()
	def decorator(function):
		@functools.wraps(function)
		def wrapper(*args, **kwargs):
			check(feature)            # raises FeatureNotEnabled "Fonction non incluse dans votre offre"
			return function(*args, **kwargs)
		return wrapper
	return decorator

def apply_features():                 # after every migrate: migrate re-enables standard records
	for name, feature in catalog().items():
		disabled = 0 if name in on else 1
		# Report.disabled, Print Format.disabled, then feature["on_change"](on)
```

- `catalog()` uses `frappe.get_hooks` (installed apps only).
- `bench_catalog()` imports every app's `hooks` module directly: the hub site
  does not install the client apps, and `frappe.get_hooks(app_name=...)` and
  `frappe.get_attr` refuse them there.
- `boot(bootinfo)` → `frappe.boot.dz_features` in the browser.
- `set_features(list | ALL)` writes site_config and applies. `move_legacy_key()`
  moves the old `dz_cod_features`.
- `patches/keep_all_features_on_existing_sites.py`: until 20 October 2026 a
  missing key meant everything; sites made before got "all" on migrate. New
  sites skip it (Frappe marks an app's patches done on install).

`commands.py` adds the bench command (Frappe reads `commands = [...]`):

```bash
bench --site client1.localhost dz-features --list
bench --site client1.localhost dz-features --enable phone_checks --disable labels_reports
bench --site client1.localhost dz-features --set courier_api,phone_checks   # exact list; "" = base only
bench --site client1.localhost dz-features --all                            # remove the key
bench --site client1.localhost dz-features --json                           # for the hub
```

## reports.py

**What:** helpers shared by the reports and the home page.

- `get_company(filters)`: the filter, else DZ Core Settings, else the user default.
- `Rates(basis)`: one unit's price, cached per report run. `LAST_PURCHASE`
  ("Dernier prix d'achat") = the last submitted Purchase Receipt line
  (`base_net_rate / conversion_factor`), else the item's last purchase rate,
  else stock value; `STOCK_VALUE` ("Coût moyen en stock") = `SUM(stock_value) / SUM(actual_qty)` over Bins.
- `get_to_buy_card()`: the "À acheter" number card (a Custom card calls a
  whitelisted method returning `{"value", "fieldtype", "route"}`).

## imports/workbook.py — the import workbook

**What:** the client fills one Excel file (French headers), we check it and
import it in one go. ERPNext's Data Import is one doctype at a time with
English technical headers; a client cannot fill that.

```bash
# 1. empty workbook for the site's sector
bench --site client1.localhost execute dz_core.imports.workbook.make_template --kwargs "{'path': '/tmp/client1.xlsx'}"
# 2. check (dry run, the default): creates nothing
bench --site client1.localhost execute dz_core.imports.workbook.import_workbook --kwargs "{'path': '/tmp/client1.xlsx'}"
# 3. import for real
bench --site client1.localhost execute dz_core.imports.workbook.import_workbook --kwargs "{'path': '/tmp/client1.xlsx', 'dry_run': 0}"
```

The sheets (`SHEETS`: sheet → `(header, key, required)`): Fournisseurs,
Clients (with Wilaya, NIF, RC, NIS, AI), Articles (code, désignation, groupe,
unité, prices, batch / expiry / shelf life, reorder level and quantity),
Modèles (clothing sites only: one template per model, sizes and colours
separated by commas), Nomenclatures (BOMs: product, quantity produced,
component, quantity), Stock initial (code, warehouse, quantity, unit cost,
batch, expiry). A "Lisez-moi" sheet (`README`) explains it; every sheet has
one "EXEMPLE" row, skipped.

```python
def import_workbook(path, dry_run=1, opening_date=None):
	report = Report()
	wb = load_workbook(resolve_path(path), data_only=True)
	data = {sheet: read_rows(wb, sheet, report) for sheet in SHEETS}
	plan = check(data, settings, report)        # validates EVERY row, creates nothing
	if report.errors or dry_run:
		... print the errors and "would create" counts; return
	create(plan, settings, report, opening_date)
	frappe.db.commit()
```

Step by step:
1. `read_rows` reads each sheet by header text, skips EXEMPLE rows; helpers
   `yes_no`, `as_date`, `as_number` record errors per sheet and row number.
2. `check` validates against the site *and* the rest of the file: units and
   groups exist, a BOM's components are known, the wilaya resolves
   (`find_wilaya`), an item already stocked in a warehouse is refused there.
   Anything that already exists (same code or name) is **skipped**, never
   changed: importing twice creates nothing.
3. Nothing is created while one row has an error.
4. `create` in order: suppliers, customers (phone normalized into `mobile_no`
   and `dz_phone`, `dz_wilaya`, customer type Company when NIF or RC),
   items (+ `reorder_rows` in the warehouse of the item's group), models
   (`create_model`: template + variants named in words, "Chemise manches
   longues XL Bleu"), BOMs, then `create_opening_stock`.
5. `create_opening_stock`: one Stock Reconciliation "Opening Stock" against
   `opening_account()`, dated `opening_date` if given. Its batches get that
   date as manufacturing date: ERPNext takes the oldest batch first, and an
   opening batch stamped with the import day would look newer than what is
   produced after it.

Clothing models and their variants' stock go in two files: the check runs
before anything is created, so a variant made by "Modèles" is unknown to
"Stock initial" in the same file.

## dz_core/doctype/

| Doctype | Files | What |
| --- | --- | --- |
| **DZ Core Settings** (single) | `dz_core_settings.json/.py` | company, sector, tax regime, invoice note, the three warehouses. `validate` refuses a warehouse of another company. `get_settings()` = cached doc. Constants `SECTORS`, `IFU`, `REEL` live here |
| **DZ Wilaya** | `dz_wilaya.json/.py` | code, name, parent wilaya. `validate` pads the code to two digits ("1" → "01"). dz_cod adds rate fields |

## dz_core/print_format/

- **Facture DZ** (Sales Invoice) and **Bon de livraison DZ** (Delivery Note):
  HTML + CSS inside the JSON. The lines that matter in Facture DZ:

  ```jinja
  {%- set co = frappe.get_doc("Company", doc.company) -%}
  {%- set buyer = frappe.db.get_value("Customer", doc.customer, ["dz_rc", "dz_nif", "dz_nis", "dz_ai"], as_dict=1) or {} -%}
  {%- set note = frappe.db.get_single_value("DZ Core Settings", "invoice_note") -%}
  {%- if doc.docstatus == 2 %}<div class="dz-watermark">{{ _("FACTURE ANNULÉE") }}</div>
  {% elif doc.docstatus == 0 %}<div class="dz-watermark">{{ _("BROUILLON") }}</div>{% endif -%}
  ...
  {{ _("Arrêtée la présente facture à la somme de") }} : {{ montant_en_lettres(doc.rounded_total or doc.grand_total) }}.
  ```

  Seller mentions from the Company custom fields, buyer mentions from the
  Customer, the IFU note, a stamp-and-signature box. To be validated by an accountant.

## dz_core/report/ — the producer reports

Script Reports: `<name>.json` (the record: roles, ref doctype), `<name>.py`
(`execute(filters)` returns `columns, rows, message, chart, summary`),
`<name>.js` (filters). Names carry no accents (they are Python folders);
`translations/fr.csv` gives them their accents. Plain SQL, readable for
someone who knows Oracle SQL.

| Report | Answers | The idea that matters |
| --- | --- | --- |
| **Cout de revient** (`cout_de_revient.py`) | What one unit of each product costs and earns | One row per default BOM; `materials_of()` prices each component with `Rates` (a component with its own BOM is priced from it, depth ≤ 5); labour = `total_additional_costs` of the Manufacture entries of the last 90 days ÷ qty made; "Dernier lot : coût réel" = the finished item's `valuation_rate` on the last manufacture. Rows indented: product, then its materials |
| **A produire** (`a_produire.py`) | What to make for orders already taken | Per product (variant): ordered − in Produits finis − in production; every ordered product listed; "Seulement ce qui manque" keeps the shortfalls |
| **A acheter** (`a_acheter.py`) | Materials under their reorder level | `Item Reorder` joined with `Bin`; "À commander" when stock + ordered < level, else "Commandé"; suggested qty = max(reorder qty, level − stock − ordered); usual supplier = last PO's; `count_under_level()` feeds the home card; its chart is the home page's low-stock alert |
| **Valeur du stock** (`valeur_du_stock.py`) | What stock is worth at a date, per warehouse and item group | Stock Ledger, the same source as ERPNext's Stock Balance: value = `SUM(stock_value_difference)`, quantity = `qty_after_transaction` of the latest move (window functions), so totals equal Stock Balance by construction |
| **Ventes par mois** (`ventes_par_mois.py`) | What sells, who buys, is it growing | Submitted Sales Invoices, amounts HT; credit notes negative; by product (variants added under their model), customer or customer group; "Évolution" compares the last two **full** months |

The heart of "Coût de revient":

```python
for bom in frappe.get_all("BOM", conditions, ["name", "item", "item_name", "uom"], order_by="item"):
	components = materials_of(bom.name, rates)
	materials = sum(line["amount"] for line in components)
	made = manufactured(bom.item)           # labour per unit, last batch's real cost
	cost = materials + made["labour"]
	price = selling_price(bom.item, filters.price_list)
	... "margin": price - cost, "margin_pct": 100 * (price - cost) / price
```

The heart of "Valeur du stock":

```sql
SELECT item_code, warehouse, qty_after_transaction,
	SUM(stock_value_difference) OVER (PARTITION BY item_code, warehouse) AS value,
	ROW_NUMBER() OVER (PARTITION BY item_code, warehouse ORDER BY posting_datetime DESC, creation DESC) AS latest
FROM `tabStock Ledger Entry`
WHERE company = %(company)s AND posting_date <= %(date)s AND is_cancelled = 0 AND docstatus < 2
-- then keep latest = 1
```

## The Atelier home page

All shipped as files and loaded by `bench migrate`:

| Folder | Records |
| --- | --- |
| `workspace/atelier/` | the page: 5 number cards, 3 charts, link cards |
| `number_card/` | Ventes du jour (Sum of today's invoices), Commandes à livrer (Count of SO "To Deliver…"), Fabrication en cours (Work Orders Not Started / In Process), À acheter (Custom: `dz_core.reports.get_to_buy_card`, keyed on Material Request), Factures en retard (Overdue invoices) |
| `dashboard_chart/` | Atelier Sales Per Month (Sum of invoices), Atelier Stock Value (Report: Valeur du stock), Atelier To Buy (Report: A acheter) |
| `sidebar/atelier/` | the Atelier menu: daily documents and the reports |
| `dock/dz_core/dz_core.json` | `"mount_on": "erpnext"`, icon `factory`: the Atelier entry on ERPNext's left rail |

Who sees what is Frappe's own rule: a card or chart shows when the user can
read its doctype or report. So "Valeur du stock" is given only to roles that
can read the Stock Ledger, and the "À acheter" card is keyed on Material
Request (DECISIONS.md "Producer reports").

## demo/ — the producer demos

Two fictional producers with 13 weeks of history (docs/DEMO.md). On a
dedicated site with ERPNext + dz_core only.

```bash
bench --site food-demo.localhost execute dz_core.demo.loader.load --kwargs "{'profile': 'food'}"
bench --site atelier-demo.localhost execute dz_core.demo.loader.load --kwargs "{'profile': 'clothing'}"
```

| File | What | Lines that matter |
| --- | --- | --- |
| `food.py`, `clothing.py` | The businesses as data: `COMPANY`, `SECTOR`, `TAX_REGIME`, `LEGAL`, suppliers, customers, items, `BOMS`, `OPENING`, prices, `buying_rate(code, day)` (the price rises), `labour_rate`, `orders(rng, day)` (who orders what today), `SHOWN_LOW` | Placeholder figures; replace with a real producer's and reload |
| `workbook.py` | Writes the profile into **the client import workbook** and imports it (data file, then opening count) | The demo goes through the same door as a client: every load tests onboarding |
| `planner.py` | Plans the story day by day **without a database**: receive purchases, finish work orders, deliver, take orders, start work orders, order materials, invoices, payments, returns, month-end counts | `day_rng(seed, day)` = `random.Random(f"{seed}-{day.isoformat()}")`: a day's randomness depends on that day only, so a later load replays the same past. It keeps its own stock so every event is possible |
| `engine.py` | Posts the events as real ERPNext documents, in date order, backdated (`posting_date` + `set_posting_time`) | `run()`: skip events after today or already done; `mark()` stores `dz_demo::<profile>::<key>` → docname as a site default. `split_batches` splits outgoing lines oldest batch first (ERPNext 16 needs one batch per line) |
| `loader.py` | The five steps | `check_site_is_for_demo` refuses a site of another company; `story_start` stores the first day once; `once(profile, step, fn)` makes each step run once |
| `wipe.py` | Cancels and deletes the story newest first, forgets the done events; keeps company, masters, opening stock, prices, users | Faster total reset: drop the site |

```python
def load(profile="food", weeks=13, seed=2026):
	p = importlib.import_module(f"dz_core.demo.{profile}")
	check_site_is_for_demo(p)
	start = story_start(profile, int(weeks))
	setup_company(p, start)                                      # prepare(), fiscal years, legal mentions
	once(profile, "masters", lambda: import_masters(profile, p, start))   # the import workbook
	setup_extras(p)                                              # customer groups, prices, users
	events = plan(p, start, getdate(nowdate()), int(seed))       # planner.py, pure Python
	posted = Engine(profile, p).run(events)                      # engine.py, real documents
```

## translations/

`fr.csv` (report names with accents), `en.csv` and `ar.csv` (wilaya,
contact, home page and report labels so far). Completing them is ROADMAP
Phase 1.

## scripts/

| Script | What |
| --- | --- |
| `backup_offsite.sh` | Daily (cron 02:30): `bench --site <s> backup --with-files --compress` for every real site (skips `restore-test.*`), `rclone copy` of the last 24 h to `offsite:erp-backups/<host>/<site>`, then deletes local backups older than 7 days **only after a successful copy**; pings `HEALTHCHECK_URL` (or `/fail`). `set -uo pipefail`: one failed site does not stop the others |
| `restore_test.sh` | Monthly drill: restores the latest backup into `restore-test.localhost`, puts back the original `encryption_key`, migrates, runs `restore_check.summary` on both sites and compares (the restored copy may have less only if the live site kept working), then drops the test site (`KEEP=1` keeps it) |
| `demo_tunnels.sh` | Serves the three demo sites on ports 8001–8003 and opens a Cloudflare quick tunnel to each; `stop` closes them (docs/DEMO.md) |

## tests/

`bench --site test.localhost run-tests --app dz_core` (68 tests).

| File | Checks |
| --- | --- |
| `test_core.py` | `prepare()` guard and idempotence, sector template, warehouses per group, tax regimes, default print formats, cancelled invoices printable, address template, wizard groups removed, legal fields, the workbook (errors create nothing, full import then re-import, older templates), invoice rendering, amounts in French words |
| `test_places_and_phones.py` | phone formats (unit), 69 wilayas and parents, `simplify`, `find_wilaya`, Customer phone normalized |
| `test_features.py` | catalogue per app, missing key = base only, "all", list followed, the patch for older sites, legacy key, `requires_feature` message, boot, `bench_catalog` reads apps not installed |
| `test_reports.py` | Coût de revient follows the last purchase; À acheter; À produire |
| `test_accounts.py` | the SCF default accounts after `prepare()`, warehouses' stock accounts; the wizard's picks are replaced and a choice is kept; the patch twice |
| `test_reports_stock_sales.py` | Valeur du stock equals Stock Balance (total, quantities, at a date); Ventes par mois equals the invoices, evolution, by customer, credit notes |
| `test_home.py` | home page records loaded, counters equal the lists, a material under its level shows, login opens Atelier |
| `test_restore_check.py` | counts, hooks from apps on top, a password from another key is reported |
| `test_demo.py` | (unit, no database) every code is an item, prices and suppliers, the story never goes below zero, has every kind of event, same story on a later day, today shows low stock on order and few late orders, events in date order, every wilaya resolves |

The first dz_core test run on a never-prepared site can fail; the second passes.
