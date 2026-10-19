"""Food demo: "Les Délices de la Mitidja SARL", a fictional jam, date-paste and
honey producer in Boufarik (Blida), on the régime réel (TVA 19 %).

PLACEHOLDER FIGURES: prices, recipes and volumes are plausible estimates, not
a real producer's. Replace them with the figures in `data requested/C-demo`
(Required Data doc, item C1) when they arrive; nothing else needs to change.
All names (company, suppliers, customers, people) are invented.

Fruit is bought as frozen pulp so jams are made all year; figs stop with the
end of the season (30 September), so fig jam runs out in the demo.
"""

import datetime

from dz_core.dz_core.doctype.dz_core_settings.dz_core_settings import REEL
from dz_core.setup.sectors import FOOD

COMPANY = "Les Délices de la Mitidja SARL"
ABBR = "LDM"
SECTOR = FOOD
TAX_REGIME = REEL

LEGAL = {
	"dz_legal_form": "SARL",
	"dz_activity": "Fabrication de confitures, de pâte de dattes et conditionnement de miel",
	"dz_rc": "09/00-0000001B26 (démo)",
	"dz_nif": "000000000000001",
	"dz_nis": "000000000000001",
	"dz_ai": "09000000001",
	"dz_capital": 1_000_000,
}
ADDRESS = {"line": "Zone d'activités, lot 14", "city": "Boufarik", "wilaya": "Blida"}

_TODAY = datetime.date.today()

RAW_GROUP, PACKAGING, FINISHED = "Matières premières", "Emballages", "Produits finis"
RAW_WH = "Matières premières"

# ---------------------------------------------------------------- suppliers

SUGAR_CO = "Sucres du Centre (démo)"
PULP_CO = "Pulpes Surgelées El Djazaïr (démo)"
DATES_CO = "Dattes de Tolga (démo)"
HONEY_CO = "Rucher des Aurès (démo)"
JARS_CO = "Verrerie et Emballages de Sétif (démo)"
LABELS_CO = "Étiquettes Express Alger (démo)"
BOXES_CO = "Cartonnerie de l'Ouest (démo)"
INGREDIENTS_CO = "Ingrédients Alimentaires DZ (démo)"

SUPPLIERS = [
	{
		"name": SUGAR_CO,
		"phone": "+213 25 41 22 10",
		"address": "Route de Blida",
		"city": "Boufarik",
		"nif": "000000000000101",
	},
	{
		"name": PULP_CO,
		"phone": "0550 12 34 01",
		"address": "Zone industrielle",
		"city": "Rouiba",
		"nif": "000000000000102",
	},
	{
		"name": DATES_CO,
		"phone": "0661 45 78 02",
		"address": "Route de Biskra",
		"city": "Tolga",
		"nif": "000000000000103",
	},
	{
		"name": HONEY_CO,
		"phone": "00213 770 11 22 03",
		"address": "Cité des abeilles",
		"city": "Batna",
		"nif": "000000000000104",
	},
	{
		"name": JARS_CO,
		"phone": "036 84 12 04",
		"address": "Zone industrielle",
		"city": "Sétif",
		"nif": "000000000000105",
	},
	{
		"name": LABELS_CO,
		"phone": "0555 90 10 05",
		"address": "Rue Hassiba Ben Bouali",
		"city": "Alger",
		"nif": "000000000000106",
	},
	{
		"name": BOXES_CO,
		"phone": "041 33 22 06",
		"address": "Zone d'activités",
		"city": "Es Sénia",
		"nif": "000000000000107",
	},
	{
		"name": INGREDIENTS_CO,
		"phone": "0698 76 54 07",
		"address": "Rue des Frères Bouadou",
		"city": "Bir Mourad Raïs",
		"nif": "000000000000108",
	},
]

# ---------------------------------------------------------------- items
# (code, name, group, unit, buying price, retail price, shelf life in days)

_ITEMS = [
	("MP-SUCRE", "Sucre cristallisé", RAW_GROUP, "Kg", 105, None, 720),
	("MP-PECTINE", "Pectine de fruits", RAW_GROUP, "Kg", 3200, None, 720),
	("MP-PULPE-FRAISE", "Pulpe de fraise surgelée", RAW_GROUP, "Kg", 380, None, 180),
	("MP-PULPE-ABRICOT", "Pulpe d'abricot surgelée", RAW_GROUP, "Kg", 330, None, 180),
	("MP-PULPE-FIGUE", "Pulpe de figue surgelée", RAW_GROUP, "Kg", 360, None, 180),
	("MP-PULPE-ORANGE", "Pulpe d'orange amère", RAW_GROUP, "Kg", 180, None, 180),
	("MP-DATTE", "Dattes Deglet Nour dénoyautées", RAW_GROUP, "Kg", 520, None, 180),
	("MP-MIEL-JUJUBIER", "Miel de jujubier en vrac", RAW_GROUP, "Kg", 6800, None, 720),
	("MP-MIEL-EUCALYPTUS", "Miel d'eucalyptus en vrac", RAW_GROUP, "Kg", 4200, None, 720),
	("MP-MIEL-MULTIFLEUR", "Miel toutes fleurs en vrac", RAW_GROUP, "Kg", 3500, None, 720),
	("EMB-POT-250", "Pot en verre 250 g", PACKAGING, "Pot", 38, None, None),
	("EMB-POT-450", "Pot en verre 450 g", PACKAGING, "Pot", 52, None, None),
	("EMB-POT-500", "Pot en verre 500 g (miel)", PACKAGING, "Pot", 55, None, None),
	("EMB-COUVERCLE", "Couvercle métal twist-off", PACKAGING, "Nos", 12, None, None),
	("EMB-ETIQUETTE", "Étiquette imprimée", PACKAGING, "Nos", 6, None, None),
	("EMB-BARQUETTE", "Barquette 500 g", PACKAGING, "Nos", 18, None, None),
	("EMB-CARTON", "Carton de 12", PACKAGING, "Carton", 60, None, None),
	("PF-CONF-FRAISE-250", "Confiture de fraise 250 g", FINISHED, "Pot", None, 350, 365),
	("PF-CONF-FRAISE-450", "Confiture de fraise 450 g", FINISHED, "Pot", None, 560, 365),
	("PF-CONF-ABRICOT-250", "Confiture d'abricot 250 g", FINISHED, "Pot", None, 340, 365),
	("PF-CONF-ABRICOT-450", "Confiture d'abricot 450 g", FINISHED, "Pot", None, 540, 365),
	("PF-CONF-FIGUE-450", "Confiture de figue 450 g", FINISHED, "Pot", None, 600, 365),
	("PF-CONF-ORANGE-250", "Confiture d'orange amère 250 g", FINISHED, "Pot", None, 360, 365),
	("PF-CONF-COING-450", "Confiture de coing 450 g", FINISHED, "Pot", None, 520, 365),
	("PF-PATE-DATTE-500", "Pâte de dattes 500 g", FINISHED, "Barquette", None, 480, 180),
	("PF-MIEL-JUJUBIER-250", "Miel de jujubier 250 g", FINISHED, "Pot", None, 2900, 730),
	("PF-MIEL-EUCALYPTUS-500", "Miel d'eucalyptus 500 g", FINISHED, "Pot", None, 3200, 730),
	("PF-MIEL-MULTIFLEUR-500", "Miel toutes fleurs 500 g", FINISHED, "Pot", None, 2700, 730),
]

ITEMS = [
	{
		"code": code,
		"name": name,
		"group": group,
		"uom": uom,
		"buying": buying,
		"selling": selling,
		"batch": group != PACKAGING,
		"expiry": group != PACKAGING,
		"shelf_life": shelf_life,
	}
	for code, name, group, uom, buying, selling, shelf_life in _ITEMS
]
BUYING = {code: buying for code, _n, _g, _u, buying, _s, _l in _ITEMS if buying}
NAMES = {code: name for code, name, *_rest in _ITEMS}

# ---------------------------------------------------------------- recipes (per batch)


def _jam(fruit, size):
	if size == 250:
		return (
			120,
			[
				(fruit, 16.5),
				("MP-SUCRE", 14),
				("MP-PECTINE", 0.2),
				("EMB-POT-250", 120),
				("EMB-COUVERCLE", 120),
				("EMB-ETIQUETTE", 120),
				("EMB-CARTON", 10),
			],
		)
	return (
		80,
		[
			(fruit, 20),
			("MP-SUCRE", 17),
			("MP-PECTINE", 0.25),
			("EMB-POT-450", 80),
			("EMB-COUVERCLE", 80),
			("EMB-ETIQUETTE", 80),
			("EMB-CARTON", 7),
		],
	)


BOMS = {
	"PF-CONF-FRAISE-250": _jam("MP-PULPE-FRAISE", 250),
	"PF-CONF-FRAISE-450": _jam("MP-PULPE-FRAISE", 450),
	"PF-CONF-ABRICOT-250": _jam("MP-PULPE-ABRICOT", 250),
	"PF-CONF-ABRICOT-450": _jam("MP-PULPE-ABRICOT", 450),
	"PF-CONF-FIGUE-450": _jam("MP-PULPE-FIGUE", 450),
	"PF-CONF-ORANGE-250": _jam("MP-PULPE-ORANGE", 250),
	"PF-PATE-DATTE-500": (
		100,
		[("MP-DATTE", 55), ("EMB-BARQUETTE", 100), ("EMB-ETIQUETTE", 100), ("EMB-CARTON", 5)],
	),
	"PF-MIEL-JUJUBIER-250": (
		100,
		[
			("MP-MIEL-JUJUBIER", 25),
			("EMB-POT-250", 100),
			("EMB-COUVERCLE", 100),
			("EMB-ETIQUETTE", 100),
			("EMB-CARTON", 9),
		],
	),
	"PF-MIEL-EUCALYPTUS-500": (
		60,
		[
			("MP-MIEL-EUCALYPTUS", 30),
			("EMB-POT-500", 60),
			("EMB-COUVERCLE", 60),
			("EMB-ETIQUETTE", 60),
			("EMB-CARTON", 5),
		],
	),
	"PF-MIEL-MULTIFLEUR-500": (
		60,
		[
			("MP-MIEL-MULTIFLEUR", 30),
			("EMB-POT-500", 60),
			("EMB-COUVERCLE", 60),
			("EMB-ETIQUETTE", 60),
			("EMB-CARTON", 5),
		],
	),
}

# Quince jam is no longer made: its last batch expires soon (shown in the demo)


def _figs_in_season(day):
	return day.month <= 9


PRODUCTION = {
	"PF-CONF-FRAISE-250": {"target": 180, "max_batches": 2},
	"PF-CONF-FRAISE-450": {"target": 120, "max_batches": 2},
	"PF-CONF-ABRICOT-250": {"target": 150, "max_batches": 2},
	"PF-CONF-ABRICOT-450": {"target": 100, "max_batches": 1},
	"PF-CONF-FIGUE-450": {"target": 80, "max_batches": 1, "active": _figs_in_season},
	"PF-CONF-ORANGE-250": {"target": 100, "max_batches": 1},
	"PF-PATE-DATTE-500": {"target": 120, "max_batches": 2},
	"PF-MIEL-JUJUBIER-250": {"target": 50, "max_batches": 1},
	"PF-MIEL-EUCALYPTUS-500": {"target": 60, "max_batches": 2},
	"PF-MIEL-MULTIFLEUR-500": {"target": 60, "max_batches": 2},
}

LABOUR = {
	"PF-PATE-DATTE-500": 20,
	"PF-MIEL-JUJUBIER-250": 15,
	"PF-MIEL-EUCALYPTUS-500": 15,
	"PF-MIEL-MULTIFLEUR-500": 15,
}


def labour_rate(product):
	"""Direct labour per unit (DA), added to the cost of each finished batch."""
	return LABOUR.get(product, 25)


# ---------------------------------------------------------------- purchasing
# reorder level and quantity in the item's unit; lead time in working days

RAW = {
	"MP-SUCRE": {"supplier": SUGAR_CO, "lead_days": 1, "reorder_level": 300, "reorder_qty": 1000},
	"MP-PECTINE": {"supplier": INGREDIENTS_CO, "lead_days": 2, "reorder_level": 4, "reorder_qty": 10},
	"MP-PULPE-FRAISE": {"supplier": PULP_CO, "lead_days": 2, "reorder_level": 80, "reorder_qty": 250},
	"MP-PULPE-ABRICOT": {"supplier": PULP_CO, "lead_days": 2, "reorder_level": 70, "reorder_qty": 200},
	"MP-PULPE-FIGUE": {"supplier": PULP_CO, "lead_days": 2, "reorder_level": 30, "reorder_qty": 100},
	"MP-PULPE-ORANGE": {"supplier": PULP_CO, "lead_days": 2, "reorder_level": 40, "reorder_qty": 120},
	"MP-DATTE": {"supplier": DATES_CO, "lead_days": 3, "reorder_level": 120, "reorder_qty": 400},
	"MP-MIEL-JUJUBIER": {"supplier": HONEY_CO, "lead_days": 3, "reorder_level": 40, "reorder_qty": 100},
	"MP-MIEL-EUCALYPTUS": {"supplier": HONEY_CO, "lead_days": 3, "reorder_level": 90, "reorder_qty": 240},
	"MP-MIEL-MULTIFLEUR": {"supplier": HONEY_CO, "lead_days": 3, "reorder_level": 90, "reorder_qty": 240},
	# The glassworks in Sétif delivers on its round, 8 working days after the
	# order. 250 g jars are ordered by the week in small lots, so on any day
	# their stock is under its level with an order on the way (shown in the demo)
	"EMB-POT-250": {"supplier": JARS_CO, "lead_days": 8, "reorder_level": 1000, "reorder_qty": 360},
	"EMB-POT-450": {"supplier": JARS_CO, "lead_days": 8, "reorder_level": 400, "reorder_qty": 1600},
	"EMB-POT-500": {"supplier": JARS_CO, "lead_days": 8, "reorder_level": 700, "reorder_qty": 1200},
	"EMB-COUVERCLE": {"supplier": JARS_CO, "lead_days": 8, "reorder_level": 2400, "reorder_qty": 5000},
	"EMB-ETIQUETTE": {"supplier": LABELS_CO, "lead_days": 5, "reorder_level": 1500, "reorder_qty": 5000},
	"EMB-BARQUETTE": {"supplier": JARS_CO, "lead_days": 8, "reorder_level": 300, "reorder_qty": 1000},
	"EMB-CARTON": {"supplier": BOXES_CO, "lead_days": 3, "reorder_level": 120, "reorder_qty": 400},
}

# At least one of them is under its reorder level with an order on the way,
# whatever day the demo is loaded (checked by tests/test_demo.py)
SHOWN_LOW = ["EMB-POT-250", "EMB-POT-500"]

SUPPLIER_TERMS = {
	SUGAR_CO: 10,
	PULP_CO: 20,
	DATES_CO: 5,
	HONEY_CO: 5,
	JARS_CO: 30,
	LABELS_CO: 20,
	BOXES_CO: 20,
	INGREDIENTS_CO: 15,
}

# Eight weeks ago strawberry pulp went up 18 % and sugar 12 %. Stock is valued
# batch by batch (FIFO), so strawberry jam costs more from the first batch made
# with the new pulp: shown in the demo
PRICE_RISES = {"MP-PULPE-FRAISE": 1.18, "MP-SUCRE": 1.12}
RISE_DAY = _TODAY - datetime.timedelta(weeks=8)


def buying_rate(code, day):
	rate = BUYING[code]
	if code in PRICE_RISES and day >= RISE_DAY:
		rate = round(rate * PRICE_RISES[code])
	return rate


# ---------------------------------------------------------------- opening stock


def _opening():
	rows = []
	for code, rule in RAW.items():
		# enough for the first days only: new purchases (and prices) arrive early in the story
		qty = rule["reorder_level"] + rule["reorder_qty"] // 2
		batch = f"OUV-{code}" if not code.startswith("EMB") else None
		expiry = _TODAY + datetime.timedelta(days=150) if batch else None
		rows.append((code, RAW_WH, qty, BUYING[code], batch, expiry))
	for product, rule in PRODUCTION.items():
		cost = 0.6 * next(price for c, _n, _g, _u, _b, price, _l in _ITEMS if c == product)
		rows.append(
			(
				product,
				FINISHED,
				rule["target"] + 60,
				round(cost),
				f"OUV-{product}",
				_TODAY + datetime.timedelta(days=240),
			)
		)
	# The quince jam left: one batch, expiring in 25 days
	rows.append(
		(
			"PF-CONF-COING-450",
			FINISHED,
			96,
			290,
			"L250219-PF-CONF-COING-450",
			_TODAY + datetime.timedelta(days=25),
		)
	)
	return rows


OPENING = _opening()

# Month-end counts: a few breakages found
COUNTS = [
	("EMB-POT-250", RAW_WH, -6),
	("EMB-POT-450", RAW_WH, -4),
	("EMB-ETIQUETTE", RAW_WH, -35),
	("EMB-COUVERCLE", RAW_WH, -12),
]

# ---------------------------------------------------------------- customers

GROSSISTES, SUPERETTES, EPICERIES, PARTICULIERS = "Grossistes", "Superettes", "Épiceries", "Particuliers"

PAYMENT = {
	GROSSISTES: ("Virement", 30),
	SUPERETTES: ("Chèque", 15),
	EPICERIES: ("Espèces", 0),
	PARTICULIERS: ("CCP / BaridiMob", 0),
}

PRICE_LISTS_BY_GROUP = {
	GROSSISTES: "Grossiste",
	SUPERETTES: "Revendeur",
	EPICERIES: "Revendeur",
	PARTICULIERS: "Détail",
}

# (name, group, wilaya, city, phone as typed)
_CUSTOMERS = [
	("Grossiste El Wancharis", GROSSISTES, "Alger", "Semmar", "0550 41 20 11"),
	("Distribution Agro Sahel", GROSSISTES, "Oran", "Es Sénia", "+213 661 30 40 12"),
	("Comptoir Alimentaire de l'Est", GROSSISTES, "Constantine", "El Khroub", "031 90 11 13"),
	("Superette Ennour", SUPERETTES, "Blida", "Blida", "0555 22 33 14"),
	("Superette Les Glycines", SUPERETTES, "Alger", "Draria", "0661 77 88 15"),
	("Supérette El Feth", SUPERETTES, "Boumerdès", "Boudouaou", "00213 770 45 67 16"),
	("Market Bab Ezzouar", SUPERETTES, "Alger", "Bab Ezzouar", "0770 12 98 17"),
	("Superette Djurdjura", SUPERETTES, "Tizi Ouzou", "Tizi Ouzou", "0662 34 56 18"),
	("Superette Ibn Khaldoun", SUPERETTES, "Tipaza", "Koléa", "0551 87 65 19"),
	("Superette Essalam", SUPERETTES, "Médéa", "Médéa", "+213 5 56 43 21 20"),
	("Superette Le Panier", SUPERETTES, "Sétif", "Sétif", "0698 11 22 21"),
	("Supérette Yasmine", SUPERETTES, "Oran", "Bir El Djir", "0771 33 44 22"),
	("Superette Béjaïa Centre", SUPERETTES, "Béjaïa", "Béjaïa", "0555 66 77 23"),
	("Superette El Baraka", SUPERETTES, "Blida", "Boufarik", "0661 99 00 24"),
	("Superette Les Oliviers", SUPERETTES, "Alger", "Chéraga", "0550 13 57 25"),
	("Épicerie Amine", EPICERIES, "Blida", "Boufarik", "0555 10 20 26"),
	("Épicerie du Marché", EPICERIES, "Blida", "Blida", "0661 20 30 27"),
	("Épicerie Hadj Moussa", EPICERIES, "Blida", "Larbaâ", "0770 30 40 28"),
	("Alimentation Générale Benali", EPICERIES, "Alger", "Kouba", "0662 40 50 29"),
	("Épicerie Fine Dar El Bahdja", EPICERIES, "Alger", "Hydra", "0551 50 60 30"),
	("Épicerie Tahar", EPICERIES, "Tipaza", "Cherchell", "0698 60 70 31"),
	("Épicerie Rahma", EPICERIES, "Boumerdès", "Boumerdès", "0771 70 80 32"),
	("Alimentation El Amel", EPICERIES, "Médéa", "Berrouaghia", "0555 80 90 33"),
	("Épicerie Belkacem", EPICERIES, "Blida", "Mouzaïa", "0661 90 10 34"),
	("Épicerie Nassim", EPICERIES, "Alger", "Baraki", "0550 21 43 35"),
	("Épicerie Lalla Khedidja", EPICERIES, "Tizi Ouzou", "Azazga", "0662 32 54 36"),
	("Alimentation Bouzid", EPICERIES, "Blida", "El Affroun", "0770 43 65 37"),
	("Épicerie du Quartier", EPICERIES, "Alger", "El Biar", "0551 54 76 38"),
	("Épicerie Sidi Yahia", EPICERIES, "Alger", "Hydra", "0698 65 87 39"),
	("Épicerie Ouled Yaïch", EPICERIES, "Blida", "Ouled Yaïch", "0771 76 98 40"),
	("Nadia Hamidi", PARTICULIERS, "Blida", "Boufarik", "0555 12 21 41"),
	("Yacine Ferhat", PARTICULIERS, "Alger", "Bab El Oued", "0661 23 32 42"),
	("Sabrina Mokrani", PARTICULIERS, "Blida", "Blida", "0770 34 43 43"),
	("Omar Belaïd", PARTICULIERS, "Tipaza", "Tipaza", "0662 45 54 44"),
	("Lina Cherif", PARTICULIERS, "Alger", "Kouba", "0551 56 65 45"),
]


def _customer(index, name, group, wilaya, city, phone):
	business = group != PARTICULIERS
	return {
		"name": name,
		"group": group,
		"phone": phone,
		"email": None,
		"address": f"{10 + index} rue principale" if business else None,
		"city": city if business else None,
		"wilaya": wilaya,
		# business customers carry their identifiers (printed on their invoices)
		**(
			{
				"nif": f"0000000000{index:05d}",
				"rc": f"00/00-00{index:05d}B26 (démo)",
				"nis": f"0000000000{index:05d}",
				"ai": f"000000{index:05d}",
			}
			if group in (GROSSISTES, SUPERETTES)
			else {"nif": None, "rc": None, "nis": None, "ai": None}
		),
	}


CUSTOMERS = [_customer(i, *row) for i, row in enumerate(_CUSTOMERS, start=1)]
GROUPS = {c["name"]: c["group"] for c in CUSTOMERS}

# This superette has stopped paying: its last invoices are overdue in the demo
BAD_PAYERS = ("Superette Essalam",)

# ---------------------------------------------------------------- prices


def _price_lists():
	retail = {code: price for code, _n, group, _u, _b, price, _l in _ITEMS if group == FINISHED}
	return {
		"Détail": retail,
		"Revendeur": {code: round(price * 0.8 / 10) * 10 for code, price in retail.items()},
		"Grossiste": {code: round(price * 0.7 / 10) * 10 for code, price in retail.items()},
	}


PRICE_LISTS = _price_lists()


def price_list_of(customer):
	return PRICE_LISTS_BY_GROUP[GROUPS[customer]]


# ---------------------------------------------------------------- the orders

_POPULAR = {
	"PF-CONF-FRAISE-250": 10,
	"PF-CONF-FRAISE-450": 6,
	"PF-CONF-ABRICOT-250": 8,
	"PF-CONF-ABRICOT-450": 5,
	"PF-CONF-FIGUE-450": 3,
	"PF-CONF-ORANGE-250": 4,
	"PF-CONF-COING-450": 0,
	"PF-PATE-DATTE-500": 7,
	"PF-MIEL-JUJUBIER-250": 2,
	"PF-MIEL-EUCALYPTUS-500": 2,
	"PF-MIEL-MULTIFLEUR-500": 3,
}

# (lines per order, units per line, step) by customer group
_BASKETS = {
	GROSSISTES: ((4, 7), (48, 144), 12),
	SUPERETTES: ((3, 5), (12, 48), 6),
	EPICERIES: ((2, 4), (6, 18), 6),
	PARTICULIERS: ((1, 2), (1, 3), 1),
}
_WEIGHTS = {GROSSISTES: 1.0, SUPERETTES: 2.2, EPICERIES: 2.0, PARTICULIERS: 1.0}


def orders(rng, day):
	"""Today's orders: [(customer, [(item, qty)])]. Fig jam stops selling after October."""
	count = rng.choice([1, 2, 2, 3, 3])
	if day.weekday() == 6:  # Sunday: the week's big orders
		count += 1
	popular = {
		code: w for code, w in _POPULAR.items() if w and (code != "PF-CONF-FIGUE-450" or day.month <= 10)
	}
	result = []
	for _ in range(count):
		customer = _pick_customer(rng)
		(low, high), (qty_low, qty_high), step = _BASKETS[GROUPS[customer]]
		products = _sample(rng, popular, rng.randint(low, high))
		lines = [(code, _round(rng.randint(qty_low, qty_high), step)) for code in products]
		if day.weekday() == 0 and rng.random() < 0.08:
			lines.append(("PF-CONF-COING-450", 6))
		result.append((customer, lines))
	return result


def _pick_customer(rng):
	weighted = [(c["name"], _WEIGHTS[c["group"]]) for c in CUSTOMERS]
	total = sum(w for _n, w in weighted)
	roll = rng.random() * total
	for name, weight in weighted:
		roll -= weight
		if roll <= 0:
			return name
	return weighted[-1][0]


def _sample(rng, weights, count):
	pool = dict(weights)
	chosen = []
	while pool and len(chosen) < count:
		total = sum(pool.values())
		roll = rng.random() * total
		for code, weight in pool.items():
			roll -= weight
			if roll <= 0:
				chosen.append(code)
				del pool[code]
				break
	return chosen


def _round(qty, step):
	return max(step, round(qty / step) * step)


# ---------------------------------------------------------------- users
# (login, first name, roles, language)

USERS = [
	(
		"gerant",
		"Karim",
		# ERPNext 16 gives some doctypes (Work Order...) to the User roles only
		[
			"Accounts Manager",
			"Accounts User",
			"Sales Manager",
			"Sales User",
			"Stock Manager",
			"Stock User",
			"Manufacturing Manager",
			"Manufacturing User",
			"Purchase Manager",
			"Purchase User",
			"Item Manager",
		],
		"fr",
	),
	("production", "Samir", ["Manufacturing User", "Stock User"], "fr"),
	("ventes", "Amina", ["Sales User", "Accounts User"], "ar"),
]

MODELS = []
