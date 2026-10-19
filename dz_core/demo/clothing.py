"""Clothing demo: "Atelier Nour Confection", a fictional garment workshop in
Sétif on the IFU (no TVA), selling wholesale to El Eulma wholesalers, to
boutiques, and work clothes to companies.

PLACEHOLDER FIGURES: fabric use, prices and volumes are plausible estimates,
not a real workshop's. Replace them with the figures in `data requested/C-demo`
(Required Data doc, item C2) when they arrive; nothing else needs to change.
All names are invented.

One model = one template item with its size and colour variants and ONE recipe
(fabric and trims per piece): ERPNext uses the model's recipe for every
variant. Each variant is made in batches of a dozen or two; direct labour per
piece is added to the cost of each batch.
"""

import datetime

from dz_core.dz_core.doctype.dz_core_settings.dz_core_settings import IFU
from dz_core.setup.sectors import CLOTHING

COMPANY = "Atelier Nour Confection"
ABBR = "ANC"
SECTOR = CLOTHING
TAX_REGIME = IFU

LEGAL = {
	"dz_legal_form": "Personne physique",
	"dz_activity": "Confection de vêtements et de tenues de travail",
	"dz_rc": "19/00-0000002A26 (démo)",
	"dz_nif": "000000000000002",
	"dz_nis": "000000000000002",
	"dz_ai": "19000000002",
}
ADDRESS = {"line": "Cité des 500 logements, local 3", "city": "Sétif", "wilaya": "Sétif"}

_TODAY = datetime.date.today()

FABRIC, TRIMS, PACKAGING, FINISHED = "Tissus", "Fournitures", "Emballages", "Produits finis"
RAW_WH = "Matières premières"

# ---------------------------------------------------------------- suppliers

FABRIC_CO = "Tissus El Eulma (démo)"
OUEST_CO = "Tissages de l'Ouest, Oran (démo)"
TRIMS_CO = "Mercerie Industrielle de Sétif (démo)"
LABELS_CO = "Étiquettes Tissées BBA (démo)"
PACK_CO = "Emballages Hauts Plateaux (démo)"

SUPPLIERS = [
	{
		"name": FABRIC_CO,
		"phone": "036 87 10 01",
		"address": "Marché des tissus",
		"city": "El Eulma",
		"nif": "000000000000201",
	},
	{
		"name": OUEST_CO,
		"phone": "+213 550 20 30 02",
		"address": "Zone industrielle",
		"city": "Oran",
		"nif": "000000000000202",
	},
	{
		"name": TRIMS_CO,
		"phone": "0661 40 50 03",
		"address": "Rue de Constantine",
		"city": "Sétif",
		"nif": "000000000000203",
	},
	{
		"name": LABELS_CO,
		"phone": "0770 60 70 04",
		"address": "Zone d'activités",
		"city": "Bordj Bou Arréridj",
		"nif": "000000000000204",
	},
	{
		"name": PACK_CO,
		"phone": "0555 80 90 05",
		"address": "Route de Batna",
		"city": "Sétif",
		"nif": "000000000000205",
	},
]

# ---------------------------------------------------------------- materials
# (code, name, group, unit, buying price)

_MATERIALS = [
	("TIS-JERSEY", "Jersey coton 180 g", FABRIC, "Meter", 650),
	("TIS-MOLLETON", "Molleton gratté 320 g", FABRIC, "Meter", 900),
	("TIS-DENIM", "Denim 12 oz", FABRIC, "Meter", 1100),
	("TIS-POPELINE", "Popeline coton", FABRIC, "Meter", 700),
	("FOU-FIL", "Fil polyester (cône 5000 m)", TRIMS, "Cône", 350),
	("FOU-BOUTON", "Bouton 4 trous", TRIMS, "Nos", 8),
	("FOU-ZIP", "Fermeture éclair 18 cm", TRIMS, "Nos", 45),
	("FOU-ELASTIQUE", "Élastique 30 mm", TRIMS, "Meter", 60),
	("FOU-RIVET", "Rivet jean", TRIMS, "Nos", 6),
	("FOU-ETIQ-MARQUE", "Étiquette tissée Nour", TRIMS, "Nos", 12),
	("FOU-ETIQ-TAILLE", "Étiquette de taille", TRIMS, "Nos", 4),
	("EMB-SACHET", "Sachet individuel", PACKAGING, "Nos", 10),
]

ITEMS = [
	{
		"code": code,
		"name": name,
		"group": group,
		"uom": uom,
		"buying": price,
		"selling": None,
		"batch": False,
		"expiry": False,
	}
	for code, name, group, uom, price in _MATERIALS
]
BUYING = {code: price for code, _n, _g, _u, price in _MATERIALS}

# ---------------------------------------------------------------- models
# (code, name, sizes, colours, retail price, labour per piece, recipe per piece)

_LABELS = [("FOU-ETIQ-MARQUE", 1), ("FOU-ETIQ-TAILLE", 1), ("EMB-SACHET", 1)]
_MODELS = [
	(
		"MOD-TSHIRT",
		"T-shirt col rond",
		["S", "M", "L", "XL"],
		["Blanc", "Noir"],
		1200,
		150,
		[("TIS-JERSEY", 0.75), ("FOU-FIL", 0.02), *_LABELS],
	),
	(
		"MOD-SWEAT",
		"Sweat à capuche",
		["S", "M", "L", "XL"],
		["Noir", "Gris"],
		3500,
		380,
		[("TIS-MOLLETON", 1.6), ("FOU-FIL", 0.04), *_LABELS],
	),
	(
		"MOD-JOGGING",
		"Pantalon jogging",
		["S", "M", "L", "XL"],
		["Noir", "Gris"],
		2600,
		300,
		[("TIS-MOLLETON", 1.3), ("FOU-ELASTIQUE", 0.9), ("FOU-FIL", 0.03), *_LABELS],
	),
	(
		"MOD-JEAN",
		"Jean coupe droite",
		["38", "40", "42", "44"],
		["Bleu"],
		4200,
		550,
		[
			("TIS-DENIM", 1.4),
			("FOU-ZIP", 1),
			("FOU-BOUTON", 1),
			("FOU-RIVET", 6),
			("FOU-FIL", 0.05),
			*_LABELS,
		],
	),
	(
		"MOD-CHEMISE",
		"Chemise manches longues",
		["S", "M", "L", "XL"],
		["Blanc", "Bleu"],
		2900,
		450,
		[("TIS-POPELINE", 1.8), ("FOU-BOUTON", 9), ("FOU-FIL", 0.04), *_LABELS],
	),
	(
		"MOD-BLOUSE",
		"Blouse de travail",
		["S", "M", "L", "XL"],
		["Blanc", "Bleu"],
		2200,
		320,
		[("TIS-POPELINE", 2.0), ("FOU-BOUTON", 6), ("FOU-FIL", 0.04), *_LABELS],
	),
]

MODELS = [
	{
		"code": code,
		"name": name,
		"group": FINISHED,
		"uom": "Pièce",
		"sizes": sizes,
		"colours": colours,
		"selling": price,
	}
	for code, name, sizes, colours, price, _labour, _recipe in _MODELS
]

# ERPNext names a variant <model>-<size abbr>-<colour abbr> (attribute order:
# Taille, then Couleur). Abbreviations come from the sector template, and a new
# size such as "38" is its own abbreviation.
COLOUR_ABBR = {
	"Noir": "NOI",
	"Blanc": "BLA",
	"Gris": "GRI",
	"Bleu": "BLE",
	"Rouge": "ROU",
	"Vert": "VER",
	"Beige": "BEI",
}


def variant_code(model, size, colour):
	return f"{model}-{size}-{COLOUR_ABBR[colour]}"


VARIANTS = {
	variant_code(code, size, colour): (code, size, colour)
	for code, _n, sizes, colours, _p, _l, _r in _MODELS
	for size in sizes
	for colour in colours
}
VARIANT_CODES = list(VARIANTS)
MODEL_OF = {variant: model for variant, (model, _s, _c) in VARIANTS.items()}
RETAIL = {code: price for code, _n, _s, _c, price, _l, _r in _MODELS}
LABOUR = {code: labour for code, _n, _s, _c, _p, labour, _r in _MODELS}

# Recipes per piece, one per model (what the workbook imports)
BOMS = {code: (1, recipe) for code, _n, _s, _c, _p, _l, recipe in _MODELS}

# Middle sizes sell most: they are cut in batches of 36, the others of 24
POPULAR_SIZES = {"M", "L", "40", "42"}


def _batch(variant):
	return 36 if VARIANTS[variant][1] in POPULAR_SIZES else 24


PLAN_BOMS = {
	variant: (_batch(variant), [(component, qty * _batch(variant)) for component, qty in BOMS[model][1]])
	for variant, model in MODEL_OF.items()
}

PRODUCTION = {variant: {"target": 2 * _batch(variant), "max_batches": 1} for variant in VARIANTS}


def labour_rate(variant):
	"""Cutting, sewing and finishing per piece (DA), added to each batch's cost."""
	return LABOUR[MODEL_OF[variant]]


# ---------------------------------------------------------------- purchasing

RAW = {
	"TIS-JERSEY": {"supplier": FABRIC_CO, "lead_days": 2, "reorder_level": 80, "reorder_qty": 150},
	# The mill in Oran delivers 12 working days after the order; fleece and denim
	# are ordered a few rolls at a time, so on any day one of them is under its
	# level with an order on the way (shown in the demo)
	"TIS-MOLLETON": {"supplier": OUEST_CO, "lead_days": 12, "reorder_level": 550, "reorder_qty": 150},
	"TIS-DENIM": {"supplier": OUEST_CO, "lead_days": 12, "reorder_level": 200, "reorder_qty": 50},
	"TIS-POPELINE": {"supplier": FABRIC_CO, "lead_days": 2, "reorder_level": 200, "reorder_qty": 600},
	"FOU-FIL": {"supplier": TRIMS_CO, "lead_days": 1, "reorder_level": 6, "reorder_qty": 20},
	"FOU-BOUTON": {"supplier": TRIMS_CO, "lead_days": 1, "reorder_level": 800, "reorder_qty": 3000},
	"FOU-ZIP": {"supplier": TRIMS_CO, "lead_days": 1, "reorder_level": 60, "reorder_qty": 200},
	"FOU-ELASTIQUE": {"supplier": TRIMS_CO, "lead_days": 1, "reorder_level": 60, "reorder_qty": 200},
	"FOU-RIVET": {"supplier": TRIMS_CO, "lead_days": 1, "reorder_level": 300, "reorder_qty": 1200},
	"FOU-ETIQ-MARQUE": {"supplier": LABELS_CO, "lead_days": 5, "reorder_level": 500, "reorder_qty": 2000},
	"FOU-ETIQ-TAILLE": {"supplier": LABELS_CO, "lead_days": 5, "reorder_level": 500, "reorder_qty": 2000},
	"EMB-SACHET": {"supplier": PACK_CO, "lead_days": 2, "reorder_level": 500, "reorder_qty": 2000},
}

# At least one of them is under its reorder level with an order on the way,
# whatever day the demo is loaded (checked by tests/test_demo.py)
SHOWN_LOW = ["TIS-MOLLETON", "TIS-DENIM"]

SUPPLIER_TERMS = {FABRIC_CO: 15, OUEST_CO: 30, TRIMS_CO: 0, LABELS_CO: 20, PACK_CO: 10}

# Nine weeks ago jersey went up 15 %: the T-shirt cost follows once the old
# rolls are used (FIFO), shown in the demo
JERSEY_RISE = 1.15
RISE_DAY = _TODAY - datetime.timedelta(weeks=9)


def buying_rate(code, day):
	rate = BUYING[code]
	if code == "TIS-JERSEY" and day >= RISE_DAY:
		rate = round(rate * JERSEY_RISE)
	return rate


# ---------------------------------------------------------------- opening stock


def _opening():
	# raw materials for the first days only: new purchases (and prices) arrive early in the story
	rows = [
		(code, RAW_WH, rule["reorder_level"] + rule["reorder_qty"] // 2, BUYING[code], None, None)
		for code, rule in RAW.items()
	]
	for variant, rule in PRODUCTION.items():
		cost = round(RETAIL[MODEL_OF[variant]] * 0.45)
		rows.append((variant, FINISHED, rule["target"] + 6, cost, None, None))
	return rows


OPENING = _opening()

COUNTS = [
	("FOU-BOUTON", RAW_WH, -40),
	("FOU-ETIQ-TAILLE", RAW_WH, -25),
	("EMB-SACHET", RAW_WH, -15),
]

# ---------------------------------------------------------------- customers

GROSSISTES, BOUTIQUES, ENTREPRISES = "Grossistes", "Boutiques", "Entreprises"

PAYMENT = {
	GROSSISTES: ("Espèces", 0),
	BOUTIQUES: ("Chèque", 15),
	ENTREPRISES: ("Virement", 30),
}
PRICE_LISTS_BY_GROUP = {GROSSISTES: "Gros", BOUTIQUES: "Boutique", ENTREPRISES: "Entreprise"}

_CUSTOMERS = [
	("Grossiste Textile El Eulma", GROSSISTES, "Sétif", "El Eulma", "0661 11 22 01"),
	("Comptoir de l'Habillement Semmar", GROSSISTES, "Alger", "Semmar", "+213 550 33 44 02"),
	("Dépôt Confection Bab El Kantara", GROSSISTES, "Constantine", "Constantine", "031 92 55 03"),
	("Boutique Élégance", BOUTIQUES, "Sétif", "Sétif", "0770 10 20 04"),
	("Boutique Jeans Center", BOUTIQUES, "Bordj Bou Arréridj", "Bordj Bou Arréridj", "0555 30 40 05"),
	("Mode Homme Ain Oulmene", BOUTIQUES, "Sétif", "Aïn Oulmene", "0662 50 60 06"),
	("Boutique Le Dressing", BOUTIQUES, "Batna", "Batna", "0698 70 80 07"),
	("Prêt-à-porter Cirta", BOUTIQUES, "Constantine", "Constantine", "0771 90 10 08"),
	("Boutique Sport Plus", BOUTIQUES, "Béjaïa", "Béjaïa", "0550 12 34 09"),
	("Boutique Nouveau Style", BOUTIQUES, "M'Sila", "M'Sila", "0661 56 78 10"),
	("Boutique Atlas", BOUTIQUES, "Sétif", "El Eulma", "0770 90 12 11"),
	("Boutique Jeunesse", BOUTIQUES, "Mila", "Mila", "0555 34 56 12"),
	("Boutique Les Hauts Plateaux", BOUTIQUES, "Bordj Bou Arréridj", "Ras El Oued", "0662 78 90 13"),
	("Boutique Casual", BOUTIQUES, "Jijel", "Jijel", "0698 12 34 14"),
	("Clinique El Chifa (blouses)", ENTREPRISES, "Sétif", "Sétif", "036 82 11 15"),
	("Laboratoire d'Analyses El Amel", ENTREPRISES, "Sétif", "El Eulma", "036 87 22 16"),
	("Boulangerie Industrielle Sétif", ENTREPRISES, "Sétif", "Sétif", "036 83 33 17"),
	(
		"Entreprise de Nettoyage Propre Plus",
		ENTREPRISES,
		"Bordj Bou Arréridj",
		"Bordj Bou Arréridj",
		"035 68 44 18",
	),
]


def _customer(index, name, group, wilaya, city, phone):
	return {
		"name": name,
		"group": group,
		"phone": phone,
		"email": None,
		"address": f"{index} rue du commerce",
		"city": city,
		"wilaya": wilaya,
		"nif": f"1900000000{index:05d}",
		"rc": f"19/00-01{index:05d}A26 (démo)" if group != BOUTIQUES or index % 2 else None,
		"nis": f"1900000000{index:05d}",
		"ai": f"190000{index:05d}",
	}


CUSTOMERS = [_customer(i, *row) for i, row in enumerate(_CUSTOMERS, start=1)]
GROUPS = {c["name"]: c["group"] for c in CUSTOMERS}

# A boutique that pays late: two invoices overdue in the demo
BAD_PAYERS = ("Boutique Le Dressing",)


def _price_lists():
	retail = {variant: RETAIL[model] for variant, model in MODEL_OF.items()}
	return {
		"Gros": {code: round(price * 0.55 / 10) * 10 for code, price in retail.items()},
		"Boutique": {code: round(price * 0.7 / 10) * 10 for code, price in retail.items()},
		"Entreprise": {code: round(price * 0.75 / 10) * 10 for code, price in retail.items()},
	}


PRICE_LISTS = _price_lists()


def price_list_of(customer):
	return PRICE_LISTS_BY_GROUP[GROUPS[customer]]


# ---------------------------------------------------------------- the orders

_POPULAR_MODELS = {"MOD-TSHIRT": 5, "MOD-SWEAT": 4, "MOD-JOGGING": 4, "MOD-JEAN": 3, "MOD-CHEMISE": 2}
_COMPANY_MODELS = {"MOD-BLOUSE": 1}
_WEIGHTS = {GROSSISTES: 1.2, BOUTIQUES: 2.5, ENTREPRISES: 0.6}


def orders(rng, day):
	"""Today's orders, by the size run: [(customer, [(variant, qty)])]."""
	count = rng.choice([0, 1, 1, 2])
	if day.weekday() == 6:
		count += 1
	result = []
	for _ in range(count):
		customer = _pick(rng, {c["name"]: _WEIGHTS[c["group"]] for c in CUSTOMERS})
		group = GROUPS[customer]
		lines = []
		if group == ENTREPRISES:
			model = "MOD-BLOUSE"
			colour = rng.choice(["Blanc", "Bleu"])
			for size in ("S", "M", "L", "XL"):
				lines.append((variant_code(model, size, colour), rng.choice([4, 6, 8, 10])))
		else:
			per_size = (6, 12) if group == GROSSISTES else (2, 4)
			for model in _sample(
				rng, _POPULAR_MODELS, rng.randint(2, 3) if group == GROSSISTES else rng.randint(1, 3)
			):
				colours = sorted(
					{colour for _m, _s, colour in (VARIANTS[v] for v in VARIANTS if MODEL_OF[v] == model)}
				)
				colour = rng.choice(colours)
				sizes = [size for v, (m, size, c) in VARIANTS.items() if m == model and c == colour]
				for size in sizes:
					lines.append((variant_code(model, size, colour), rng.randint(*per_size)))
		result.append((customer, lines))
	return result


def _pick(rng, weights):
	total = sum(weights.values())
	roll = rng.random() * total
	for name, weight in weights.items():
		roll -= weight
		if roll <= 0:
			return name
	return name


def _sample(rng, weights, count):
	pool = dict(weights)
	chosen = []
	while pool and len(chosen) < count:
		chosen.append(_pick(rng, pool))
		del pool[chosen[-1]]
	return chosen


# ---------------------------------------------------------------- users

USERS = [
	(
		"gerant",
		"Nour",
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
	("atelier", "Rachid", ["Manufacturing User", "Stock User"], "fr"),
	("ventes", "Meriem", ["Sales User", "Accounts User"], "ar"),
]
