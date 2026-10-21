# 03 dz_cod (repo dafter-cod)

The online-sales part (Pack Vente en ligne), on top of dz_core: a
cash-on-delivery order desk for Algerian sellers (Instagram, Facebook,
website). Phone confirmation, stock reservation, shipping fees by wilaya,
courier hand-over, returns, courier cash settlement ("Versement"), webhooks
to n8n, three reports, a demo shop. `required_apps = ["erpnext", "dz_core"]`.
118 tests (24 unit + 94 integration).

**The deep course on this app already exists:** dafter-cod
`docs/STUDY_GUIDE.md` (mental model, the lines that matter, "break it on
purpose", "rebuild it yourself" and failure modes for each part). This
chapter is the file-by-file map; the study guide chapter is given for each part.

```
dafter-cod/
  README.md DECISIONS.md LATER.md
  docs/  STUDY_GUIDE.md DEMO.md DEPLOY.md FEATURES.md WEBHOOKS.md COURIER_INTEGRATION.md LOCAL_TEST.md
  dz_cod/
    hooks.py  features.py  commands.py
    cod/        states.py order.py stock.py shipping.py settlement.py phone_checks.py home.py barcode.py
    couriers/   base.py mock.py yalidine.py yalidine_import.py yalidine_webhook.py places.py sync.py zrexpress.py
    setup/      install.py new_client.py custom_fields.py workflow.py wilayas.py webhooks.py home_block/
    dz_cod/     doctype/ report/ print_format/ workspace/ sidebar/ number_card/ dashboard_chart/ module_onboarding/ onboarding_step/
    dock/  public/js/  demo/  translations/  tests/
```

Read in this order: `hooks.py`, `setup/workflow.py`, `cod/order.py`,
`cod/stock.py`, then the rest.

---

## hooks.py (STUDY_GUIDE §0)

```python
required_apps = ["erpnext", "dz_core"]
after_install = "dz_cod.setup.install.after_install"
after_migrate = "dz_cod.setup.install.after_migrate"
doctype_js = {"Sales Order": "public/js/sales_order.js", "Supplier": "public/js/supplier.js"}
doc_events = {
	"Sales Order": {
		"before_validate": "dz_cod.cod.order.before_validate",
		"validate": "dz_cod.cod.order.validate",
		"before_submit": "dz_cod.cod.order.before_submit",
		"before_update_after_submit": "dz_cod.cod.order.before_update_after_submit",
		"on_update_after_submit": "dz_cod.cod.order.on_update_after_submit",
	},
	"Customer": {"validate": "dz_cod.cod.phone_checks.warn_duplicate_customer"},
	"Supplier": {"validate": "dz_cod.features.check_courier_connector"},
	"Webhook": {"validate": "dz_cod.features.check_webhook"},
}
dz_features = ["dz_cod.features.FEATURES"]                      # read by dz_core
scheduler_events = {"hourly": ["dz_cod.couriers.sync.sync_shipped_orders"]}
jinja = {"methods": ["dz_cod.cod.barcode.code128_svg"]}
dz_restore_check_counted = ["Sales Order", "Courier Settlement"]  # read by dz_core's restore check
dz_restore_check_last = ["Sales Order"]
default_log_clearing_doctypes = {"Courier Webhook Event": 30}
```

Almost everything starts from `after_migrate` (our setup) or the Sales Order
`doc_events` (what happens at each step).

## The order life cycle

```
Nouvelle ──Confirmer──> Confirmée ──Préparer──> Préparée ──Expédier──> Expédiée ──Marquer livrée──> Livrée ──Marquer réglée──> Réglée
   │ ▲                     │                       │                     │
   │ └─Pas de réponse─> Injoignable (call counter) │                     └──Marquer retournée──> Retournée
   └─Annuler─> Annulée     └────────Annuler────────┴──> Annulée après confirmation
```

How ERPNext sees it: Nouvelle / Injoignable / Annulée are **drafts**
(docstatus 0); **Confirmer = submit** (ERPNext reserves the stock); later
moves are "update after submit"; Annulée après confirmation = **cancel**.

A **direct sale** (field *Canal* = Vente directe, `cod/channel.py`: the
customer's usual channel, else COD Settings') takes a short path in the same
workflow, Nouvelle ──Valider──> Validée, then ERPNext's own delivery note and
invoice. Every hook in `cod/order.py` returns at once for it (`is_cod`), and
the transition conditions show the COD buttons on COD orders only.

### cod/states.py

The state and button names as constants (`NEW = "Nouvelle"`, `CONFIRMED =
"Confirmée"`, `ACTION_SHIP = "Expédier"`...), plus `MAIN_PATH`, `ALL_STATES`,
`SHIPPED_OR_LATER`. Always use them in code: a typo in a French string would
silently break a check. Two cancel states because Frappe cannot cancel a draft.

### setup/workflow.py (STUDY_GUIDE §3)

**What:** describes the Workflow "Commande COD" on Sales Order: WHO may move
an order and WHERE. Like a routing: states are operations, transitions are moves.

```python
# (state, docstatus, colour, role allowed to edit in this state)
STATES = [(S.NEW, 0, "Primary", SALES), (S.UNREACHABLE, 0, "Warning", SALES),
          (S.CONFIRMED, 1, "Info", STOCK), ..., (S.CANCELLED_AFTER_CONFIRMATION, 2, "Inverse", MANAGER)]

CALLS_LEFT = ("(doc.dz_call_attempts or 0) < "
              "int(frappe.db.get_value('COD Settings', 'COD Settings', 'max_call_attempts') or 3)")

# (from state, action button, to state, role, condition)
TRANSITIONS = [
	(S.NEW, S.ACTION_CONFIRM, S.CONFIRMED, SALES, None),
	(S.NEW, S.ACTION_NO_ANSWER, S.UNREACHABLE, SALES, CALLS_LEFT),
	...
	(S.SHIPPED, S.ACTION_RETURN, S.RETURNED, STOCK, None),
	(S.DELIVERED, S.ACTION_SETTLE, S.SETTLED, ACCOUNTS, None),
]
```

Standard roles only: Sales User confirms, Stock User prepares / ships /
delivers / returns, Accounts User settles, Sales Manager edits cancelled
orders. The call counter is the Workflow's own "update field" on
Injoignable: no code.

### cod/order.py (STUDY_GUIDE §3)

**What:** WHAT HAPPENS when an order moves. Wired by the Sales Order `doc_events`.

```python
def before_validate(order, method=None):     # every save of a draft
	order.dz_phone = normalize_phone(order.dz_phone)          # dz_core.phone
	if not order.dz_courier: order.dz_courier = settings.default_courier
	if not order.set_warehouse: order.set_warehouse = settings.main_warehouse
	apply_shipping_charge(order)                               # shipping.py

def validate(order, method=None):            # after ERPNext computed totals
	order.dz_cod_amount = flt(order.rounded_total or order.grand_total)
	warn_refused_parcels(order)                                # phone_checks.py (optional feature)

def before_submit(order, method=None):       # Confirmer
	check_delivery_details(order)            # valid phone, wilaya, commune + address for Domicile
	get_adapter(order.dz_courier).check_order(order)           # e.g. Yalidine knows the commune
	problems = stock.check_available_stock(order)              # warn, or block (COD Settings)
	order.dz_courier_fee = courier_cost; order.dz_confirmed_on = event_date(order)

def before_update_after_submit(order, ...):  # checks and dates BEFORE the new state is saved
	if state == S.SHIPPED: prepare_shipment(order)   # courier + tracking (typed or from the connector)

def on_update_after_submit(order, ...):      # stock AFTER the new state is saved
	if state == S.SHIPPED: order.db_set("dz_delivery_note", stock.create_delivery_note(order, ...))
	elif state == S.RETURNED:
		order.db_set("dz_return_note", stock.create_return(order, ...)); stock.close_order(order.name)
```

- Both after-submit hooks start with `if not order.has_value_changed("workflow_state"): return`:
  an edit that is not a move does nothing.
- `event_date(order)` = `order.flags.dz_event_date or today()`: only the demo
  loader sets the flag, to replay history with past dates.
- `set_shipping_details` (whitelisted) is called by the *Expédier* dialog to
  save courier, tracking and stop desk just before the workflow action.

### cod/stock.py (STUDY_GUIDE §4)

**What:** the stock movements, all with standard ERPNext documents.

| Step | Planning analogy | Code |
| --- | --- | --- |
| Confirmer | material allocation | ERPNext's reserved qty on submit; `check_available_stock` compares Bin `actual_qty - reserved_qty` |
| Expédier | material issue | `create_delivery_note`: `make_delivery_note(order.name)`, courier and tracking copied into `transporter` / `lr_no`, submitted |
| Retournée | receipt into quarantine | `create_return`: `make_sales_return(dn)` with every line into the **Retours** warehouse; then `close_order` so ERPNext never reserves it again |
| Inspecter le retour | quality decision | `inspect_return`: quantities must match the return exactly; good pieces → Material Transfer Retours → main; damaged → Material Issue; both linked by `dz_sales_order` |

### cod/shipping.py (STUDY_GUIDE §5)

**What:** the delivery fee from the wilaya rate table, added as a line in
the standard "Taxes and Charges" table (type "Actual"), exactly like
ERPNext's Shipping Rule, so totals, delivery note and ledger include it.

```python
def get_rates(wilaya, delivery_type):
	doc = frappe.get_cached_doc("DZ Wilaya", wilaya)
	if not doc.enabled: frappe.throw(...)                    # "n'est pas livrable"
	if delivery_type == STOP_DESK:
		return doc.stopdesk_rate, doc.stopdesk_courier_cost
	return doc.home_rate, doc.home_courier_cost

def apply_shipping_charge(order):
	if not order.dz_manual_shipping:                          # "manual rate" for free delivery
		order.dz_shipping_charge, _cost = get_rates(order.dz_wilaya, order.dz_delivery_type)
	set_shipping_row(order, flt(order.dz_shipping_charge))    # one row on the shipping income account
```

### cod/settlement.py + doctype Courier Settlement (STUDY_GUIDE §7)

**What:** the Versement: a courier's statement matched line by line against
our orders (a three-way match). `settlement.py` holds the rules as pure
functions (easy to test); the doctype applies them.

```python
def line_status(order_state, order_courier, settlement_courier, net_paid, expected_net, tolerance):
	if order_state is None: return UNKNOWN                    # "Inconnue"
	if order_state == S.SETTLED: return ALREADY_SETTLED       # "Déjà réglée"
	if order_state != S.DELIVERED or order_courier != settlement_courier: return INVALID
	if abs(net_paid - expected_net) <= tolerance: return OK
	return GAP                                                # "Écart"
```

In `CourierSettlement.match_lines()`: `net_amount = collected − courier fee`,
`expected_net = remaining_due(expected amount − expected fee, already received)`,
`difference = net − expected_net`. "Déjà versé" = what earlier submitted
Versements of the same courier paid on the order, so an order can be paid
over several Versements.

- `on_submit`: every OK line (and Écart ticked *Accepter*) → workflow action
  *Marquer réglée*, `dz_settlement` set on the order.
- `on_cancel`: a Workflow cannot go backwards, so orders are put back to
  Livrée by writing the fields directly, with a comment.
- `before_cancel`: refused while a later Versement settled one of its
  disputed orders on the rest.
- `load_delivered_orders` (*Charger les commandes livrées*) pre-fills one line
  per delivered order; `get_missing_orders` lists delivered orders not in the statement.

### cod/invoicing.py (COD accounting)

- `invoice_delivered_order`: when an order becomes Livrée (`on_update_after_submit`),
  its Sales Invoice is made from the delivery note (`make_sales_invoice`), dated the
  delivery, payment mode "Contre-remboursement", submitted and linked on the order
  (`dz_sales_invoice`). dz_core's sales reports then count online sales.
- `settlement_entry`: on a Versement's submit, one Journal Entry. Debit the bank and the
  courier fees; credit each order's invoice with what the courier collected; an accepted
  short payment is written off ("Écarts sur versements"); unknown parcels wait in
  "Versements à identifier". Cancelling the Versement cancels the entry.
- The accounts are COD Settings fields (section Comptabilité), made by `prepare` and on migrate.

### cod/phone_checks.py

Warnings, never blocks (optional feature `phone_checks`): an order whose
phone already had parcels sent back (`refused_parcels`, threshold in COD
Settings), and a customer saved with another customer's phone.

### cod/home.py, setup/home_block/

The welcome guide on the COD home page (a Custom HTML Block created by
`install.setup_home_block` from `home.html/.css/.js`); `set_guide_state`
remembers open / collapsed / hidden per user.

### cod/barcode.py

Code 128 (set B) as inline SVG, pure Python, for the "Bordereau COD" label:
`{{ code128_svg(doc.dz_tracking_number) }}`. Checksum:
`(START_B + sum(position * value)) % 103`.

## Couriers (STUDY_GUIDE §6)

**Adapter pattern:** the rest of the app calls three methods and never
knows which courier is used.

```python
class CourierAdapter:                         # couriers/base.py
	def check_order(self, order): ...         # optional, no network
	def create_shipment(self, order): ...     # -> tracking number, or None (typed by hand)
	def get_status(self, tracking_number): ...# -> IN_TRANSIT / DELIVERED / RETURNED / UNKNOWN (our words)
	def get_statuses(self, tracking_numbers): # many at once (Yalidine: 50 per call)
	def get_tracking(self, tracking_number): ...

ADAPTERS = {"Manuel": ManualAdapter, "Mock": MockAdapter,      # couriers/__init__.py
            "Yalidine": YalidineAdapter, "ZR Express": ZRExpressAdapter}

def get_adapter(courier_name):
	courier = frappe.get_cached_doc("Supplier", courier_name)
	adapter_name = courier.get("dz_courier_adapter") or "Manuel"
	if adapter_name in API_ADAPTERS and not is_enabled("courier_api"):
		adapter_name = "Manuel"               # not in this client's offer
	return ADAPTERS[adapter_name](courier)
```

A courier is a **Supplier** with "Is Transporter" ticked; its connector,
API keys and webhook secret are custom fields on the Supplier.

| File | What |
| --- | --- |
| `base.py` | The interface and **Manuel** (the default: tracking typed, status moved by hand) |
| `mock.py` | Offline courier for demos and tests: tracking `MOCK-<order>`, statuses in the Redis cache (`set_mock_status`) |
| `yalidine.py` | Yalidine API (`api.yalidine.app/v1/`, headers `X-API-ID` / `X-API-TOKEN`): create parcel (reuses one already created for the order), statuses 50 per call, history; `map_status` turns Yalidine's words into ours (only "Livré" and "Retourné au vendeur" move an order). `call()` remembers exhausted quota windows and `Retry-After` in Redis, shared by web and workers: a click gets a clear message, a job waits up to 60 s. **Built from a copy of the docs, tested with a fake HTTP layer only: check with a real account first** (COURIER_INTEGRATION.md §4) |
| `yalidine_import.py` | Buttons on the courier: import Yalidine prices into the wilayas' *courier* costs (one call per wilaya, 1.5 s apart), import communes and stop desks; background jobs, `@requires_feature("courier_api")` |
| `yalidine_webhook.py` | `receive()` at `/api/method/dz_cod.couriers.yalidine_webhook.receive`: answers the CRC check (GET), checks `X-YALIDINE-SIGNATURE` = HMAC-SHA256(raw body, secret) against each Yalidine courier, stores each event as a **Courier Webhook Event** named by its `event_id` (a duplicate is refused by the database), answers 200 at once and applies the events in a job |
| `places.py` | Pick lists on the order: the order's courier's communes and stop desks of a wilaya (or of its parent for 59–69); none for a courier without a list (Manuel) |
| `sync.py` | Hourly job (if *Synchroniser les statuts* is on and `courier_api`): asks each courier about its shipped parcels at once and presses the normal workflow buttons, so stock moves and webhooks run as if a person clicked; one failure never stops the others |
| `zrexpress.py` | "Coming soon": works like Manuel until ZR's new platform has docs |

The signature check, the line that keeps fake webhooks out:

```python
def courier_for_signature(raw_body, signature):
	for courier in frappe.get_all("Supplier", filters={"dz_courier_adapter": "Yalidine"}, pluck="name"):
		secret = get_decrypted_password("Supplier", courier, "dz_webhook_secret", raise_exception=False)
		if secret and hmac.compare_digest(sign(raw_body, secret), signature):
			return courier
	return None
```

## features.py — the four optional features

The mechanism is dz_core's (chapter 02); this file declares the features and
keeps the guards that are about couriers and webhooks. It re-exports
`is_enabled`, `requires_feature`... so COD code imports from one place.

| Feature | Gets | Guard |
| --- | --- | --- |
| `courier_api` | Yalidine (ZR later): parcels, label, imports, webhooks, sync | `get_adapter` falls back to Manuel; `check_courier_connector` on Supplier validate; imports and webhook refuse |
| `phone_checks` | refused-parcel and duplicate-customer warnings | `is_enabled` in phone_checks.py |
| `n8n_webhooks` | the 4 webhooks to n8n | `on_change: apply_webhooks` switches them off and back as they were; `check_webhook` on Webhook validate |
| `labels_reports` | Bordereau COD, Commandes par jour, Taux de retour | `reports` / `print_formats` disabled by `apply_features` |

## setup/

| File | What |
| --- | --- |
| `install.py` | `setup_all()` after install / migrate: custom fields, workflow, wilaya rates, webhooks, Selling Settings (no reservation on returns), the home block, defaults for new COD Settings fields, then `apply_features()` **last** (migrate re-enables our reports) |
| `new_client.py` | `prepare(company, abbr, courier, features, sector, tax_regime)`: **calls dz_core's prepare first**, then the Retours warehouse, the account "Frais de livraison facturés", COD Settings (orders leave from dz_core's Produits finis), one courier, the features (`set_features`), COD as the home page |
| `custom_fields.py` | Sales Order: phone(s), wilaya, commune (Autocomplete), address, delivery type (Domicile / Stop desk), stop desk, source (Instagram…), shipping charge and manual flag, amount to collect, courier, tracking and the courier's own status, call counter (`dz_call_attempts`), the date of each step (`dz_confirmed_on` … `dz_settled_on`), delivery and return notes, `dz_return_inspected`, settlement; Customer: commune, address; Supplier: connector, API id / token, webhook secret, departure wilaya; Stock Entry: `dz_sales_order`; DZ Wilaya: `enabled` ("Livrable"), `zone`, `home_rate`, `stopdesk_rate`, `home_courier_cost`, `stopdesk_courier_cost`, `stopdesk_available`. `allow_on_submit: 1` on what changes after confirmation. List view properties via Property Setters, never over the user's own |
| `wilayas.py` | Example rates by zone (400 DA Alger home … 1,400 DA far south) written once per wilaya: placeholders for the courier's rate card |
| `webhooks.py` | Four Webhooks "COD - Confirmée / Expédiée / Livrée / Retournée", **created disabled** with a placeholder URL; the client's URL, Enabled and headers are never touched; the template is refreshed only if nobody edited it (a fingerprint is kept) |

The webhook condition that makes it fire once per move:

```python
def webhook_condition(state, event):
	if event == "on_submit":
		return f'doc.workflow_state == "{state}"'
	return f'doc.workflow_state == "{state}" and doc.has_value_changed("workflow_state")'
```

In the Jinja payload write `doc["items"]`, not `doc.items` (that is the dict method). Payload: docs/WEBHOOKS.md.

## dz_cod/doctype/

| Doctype | What |
| --- | --- |
| **COD Settings** ("Paramètres COD", single) | company, main and returns warehouse, shipping income account, block confirmation without stock, max call attempts, refused-parcel warning threshold, settlement tolerance, default courier, automatic status sync |
| **Courier Settlement** + **Courier Settlement Item** ("Versement") | above |
| **DZ Commune**, **DZ Stop Desk** | Each courier's communes and offices, one list per connector, named `<connector>-<courier's id>` (`Yalidine-1630`) so a new import updates; the order's pick lists show its courier's list |
| **Courier Webhook Event** | one per pushed event, named by `event_id`; cleared after 30 days |

DZ Wilaya is dz_core's; this app only adds fields to it.

## dz_cod/report/ (STUDY_GUIDE §9)

| Report | Answers |
| --- | --- |
| **COD Courier Outstanding** ("Encours transporteurs") | Cash each courier still owes: Livrée orders, net of fees and of what earlier Versements paid; "En litige", "Sur la route"; detail per order. In the base |
| **COD Daily Orders** ("Commandes par jour") | Per order date, how many orders are now in each state. Feature `labels_reports` |
| **COD Return Rate** ("Taux de retour") | returned / (delivered + returned) per product, variant or wilaya, with a minimum sample. Feature `labels_reports` |

Plus the print format **Bordereau COD** (100 × 150 mm label with barcode),
the **COD** workspace, sidebar, number cards (to confirm, to ship, in
transit, cash with couriers), two charts, a module onboarding, and the dock
on ERPNext's rail.

## public/js/

| File | What |
| --- | --- |
| `sales_order.js` | Courier filter, commune and stop desk pick lists; the *Expédier* dialog (courier + tracking saved by `set_shipping_details` before the workflow action); the *Inspecter le retour* dialog on a returned order; *Bordereau* button (feature) |
| `supplier.js` | On a courier: only Manuel / Mock without `courier_api` (reads `frappe.boot.dz_features`); Yalidine import buttons; ZR "coming soon" notice |

## demo/ (STUDY_GUIDE §10, docs/DEMO.md)

The shop Encre & Fil: 30 products / ~260 variants, 80 customers, 200 orders
over 60 days in every state, weekly Versements.

| File | What |
| --- | --- |
| `data.py` | The catalogue, names, communes (edit to change the shop) |
| `loader.py` | `load(return_rate=0.2)`: company and settings, items, customers, two Mock couriers, opening stock 65 days back, `plan_orders` (each order gets a small story), `replay_stories` through the **real workflow** (`apply_workflow` with `order.flags.dz_event_date`), inspections, `create_settlements` with a few disputes. Skips what exists |
| `wipe.py` | Deletes the demo data, keeps the company and settings |

## tests/ (STUDY_GUIDE §11)

`bench --site test.localhost run-tests --app dz_cod`. `helpers.py` builds a
company, warehouses, one item with stock, one customer, a Mock and a Manuel
courier (rolled back per class).

| File | Tests |
| --- | --- |
| `test_rules.py` (unit) | settlement line statuses and amounts, every transition uses known states and allowed docstatus moves, every wilaya has a rate zone, variant combinations |
| `test_order_flow.py` | shipping fees (home, stop desk, change of wilaya, manual, not delivered), confirm reserves stock, missing phone / address, blocked when short, call counter, both cancels, illegal jump refused, ship creates the delivery note, delivery date, return to Retours then inspection |
| `test_settlement.py` | statuses and summary, accepted gap and cancel, paid twice, second Versement expects only the rest, cancel guard, outstanding report, home card |
| `test_checks_and_label.py` | refused-parcel and duplicate warnings, return-rate small samples, webhook template refresh (kept when edited), Code 128 checksum, the label |
| `test_couriers_and_webhooks.py` | Mock statuses move orders, Manuel, ZR "coming soon", webhook fires once per state change, payload is valid JSON, reports run |
| `test_yalidine.py` (unit, fake HTTP) | parcels, statuses, quotas, imports, signed webhooks |
| `test_places.py` | two couriers' communes and offices don't mix; the patch that renamed the Yalidine-only records |
| `test_channel.py` | a direct sale skips the COD checks and fee and goes Nouvelle → Validée, then ERPNext's delivery note and invoice; the customer's channel; the COD counters ignore direct sales; the channel patch |
| `test_invoicing.py` | Livrée makes one submitted invoice (taxes, delivery fee, Contre-remboursement); a Versement's Journal Entry (paid, accepted gap, open gap, unknown, overpaid lines) balances; cancelling reverses it |
| `test_lots.py` | a COD line that needs two lots ships, comes back and is inspected |
| `test_new_client.py` | the online seller's `prepare()` on a fresh company, twice |
| `test_version.py` (unit) | refused on a dz_core older than `DZ_CORE_MIN` |
| `test_features.py` | each feature off hides and refuses its part |
| `test_home.py` | COD home page records |
| `test_translations.py` (unit) | every French text has an English line (`i18n_strings.py`) |

## translations/

`fr.csv` (doctypes and reports in French: "Commande", "Versement",
"Paramètres COD"), `en.csv` (~320 lines), `ar.csv` (~335 lines). STUDY_GUIDE §15.

## What is not built (LATER.md)

Yalidine checked on a real account and its payments into Versements, ZR
Express, an order intake endpoint for n8n, a commune master list, rates per
courier, exchanges, hard stock reservation, SMS.
