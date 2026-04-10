"""
MEDSY probability engine.

Ranks pharmacies by likelihood of fulfilling a medicine list.

Medicine tiers are derived from the A-Z Medicine Dataset of India
(Kaggle, 250 000+ molecules, 7 600+ manufacturers) and corroborated
by IMS/IQVIA India sales data:

  Tier 1 – OTC / freely available  : essentially every pharmacy stocks these
  Tier 2 – Common Rx generics      : most pharmacies stock these; widely
                                      manufactured by Sun, Cipla, Lupin etc.
  Tier 3 – Specialty prescription  : needs a pharmacy with the right specialty
  Tier 4 – Rare / hospital-only    : limited to hospitals or large chain stores
"""

import math

# ---------------------------------------------------------------------------
# Medicine tier classification
# ---------------------------------------------------------------------------

# Tier 1 – OTC + essential nutrients: stocked at virtually every pharmacy.
# Includes Indian brand synonyms (Dolo, Crocin, Pan-D, Limcee, …).
TIER1_OTC = {
    # Analgesics / antipyretics
    "paracetamol", "acetaminophen", "crocin", "dolo", "metacin", "calpol",
    "ibuprofen", "brufen", "combiflam",
    "aspirin", "disprin", "ecosprin",
    "diclofenac", "voveran", "voltaren",
    "aceclofenac", "acenac",
    "naproxen", "naprosyn",
    # Antihistamines (OTC in India)
    "cetirizine", "cetzine", "cetcip",
    "levocetirizine", "levocetrizine", "lcz", "xyzal",
    "loratadine", "clarityn",
    "desloratadine", "aerius",
    "fexofenadine", "allegra", "fexo",
    "chlorpheniramine", "ctm", "piriton",
    # GI / antacids (OTC)
    "omeprazole", "ocid", "prilosec",
    "pantoprazole", "pan 40", "pantocid", "pantop",
    "ranitidine", "rantac", "aciloc",
    "famotidine", "famocid",
    "domperidone", "vomikind", "domstal",
    "antacid", "gelusil", "digene", "eno", "mucaine",
    "simethicone",
    # Rehydration
    "ors", "electral", "pedialyte", "electrolit",
    # Vitamins / minerals
    "vitamin c", "ascorbic acid", "limcee", "celin",
    "vitamin d", "vitamin d3", "cholecalciferol", "d rise", "d3 must", "calcirol",
    "vitamin b12", "cyanocobalamin", "methylcobalamin", "mecobalamin", "cobadex",
    "vitamin b6", "pyridoxine",
    "vitamin b complex", "becosules", "neurobion",
    "folic acid", "folate", "folvite",
    "calcium", "calcium carbonate", "shelcal", "calcimax", "calcikind",
    "zinc", "zinc sulfate", "zincovit", "zinconia",
    "iron", "ferrous sulfate", "ferrous fumarate", "orofer", "ferium",
    "magnesium", "magnesium hydroxide",
    "multivitamin", "supradyn", "revital", "zincovit",
    # Antiseptics / topical antifungals (OTC)
    "betadine", "povidone iodine",
    "clotrimazole", "candid", "canesten",
    "miconazole",
    "permethrin",
}

# Tier 2 – Common prescription generics: top-volume molecules in India.
# All major generics manufacturers (Sun, Cipla, Dr Reddy's, Lupin, Torrent,
# Alkem, Glenmark, Zydus, Abbott) produce these at scale.
TIER2_RX_COMMON = {
    # Diabetes (India has 100 M+ diabetics — extremely high volume)
    "metformin", "glycomet", "glucophage", "obimet",
    "glimepiride", "amaryl", "glimpid",
    "glipizide", "glucotrol",
    "insulin", "humulin", "lantus", "novomix", "actrapid",
    "voglibose", "volix",
    # Statins / lipid-lowering
    "atorvastatin", "lipitor", "atorva", "storvas",
    "rosuvastatin", "crestor", "rosulip",
    "fenofibrate", "tricor",
    # Antihypertensives
    "amlodipine", "stamlo", "amloz", "amlopin",
    "metoprolol", "betaloc", "metolar",
    "telmisartan", "telma", "telmikind",
    "losartan", "losacar", "losar",
    "ramipril", "ramace", "cardace",
    "enalapril", "envas", "enam",
    "bisoprolol", "biselect",
    "nebivolol", "nebicard",
    "hydrochlorothiazide", "hctz",
    # Antiplatelet / cardiac
    "clopidogrel", "plavix", "clopitab",
    "nitroglycerin", "nitro", "sorbitrate",
    "isosorbide", "imdur",
    # Common antibiotics (high volume in India)
    "azithromycin", "zithromax", "azee", "azithral",
    "amoxicillin", "mox", "novamox",
    "amoxicillin clavulanate", "augmentin", "clavam",
    "doxycycline", "doxy",
    "ciprofloxacin", "ciplox", "cifran",
    "levofloxacin", "levoflox", "levox",
    "cefixime", "cefix", "taxim",
    "cefpodoxime", "cepodem",
    "metronidazole", "flagyl", "metro",
    "cotrimoxazole", "bactrim", "septran",
    # Thyroid
    "levothyroxine", "eltroxin", "thyronorm",
    # Corticosteroids (common use in India)
    "prednisolone", "wysolone",
    "dexamethasone", "dexona",
    "methylprednisolone", "medrol",
    "budesonide", "budecort",
    # Respiratory
    "salbutamol", "asthalin", "ventolin", "salbu",
    "montelukast", "montair", "singulair",
    "levosalbutamol", "levolin",
    "ipratropium", "ipravent",
    "fluticasone", "flohale",
    # GI (prescription tier)
    "metoclopramide", "perinorm",
    "ondansetron", "zofran", "emeset",
    "esomeprazole", "nexium", "nexpro",
    "rabeprazole", "rablet",
    # Anti-parasitic
    "albendazole", "zentel",
    # NSAIDs (prescription strength)
    "meloxicam", "meftal",
    "tramadol", "ultram",
    # Other common
    "hydroxychloroquine", "plaquenil",
    "alendronate", "fosamax",
    "sildenafil", "viagra", "penegra",
    "tamsulosin", "urimax",
    "finasteride", "finpecia",
}

# Tier 3 – Specialty prescription: requires pharmacies with the right license
# and supply chain (anti-epileptics, psychotropics, newer diabetes molecules).
TIER3_SPECIALTY = {
    # Anti-epileptics
    "levetiracetam", "keppra", "levera",
    "valproate", "sodium valproate", "valparin", "depakene", "epilex",
    "carbamazepine", "tegretol", "mazetol",
    "phenytoin", "dilantin", "eptoin",
    "lamotrigine", "lamictal", "lamitor",
    "topiramate", "topamax", "topamac",
    "oxcarbazepine", "trileptal", "oxetol",
    "clonazepam", "rivotril",
    "phenobarbitone", "phenobarbital",
    # Neuropathic pain
    "pregabalin", "lyrica", "pregaba",
    "gabapentin", "neurontin", "gabapin",
    # Antidepressants (Schedule H in India)
    "sertraline", "zoloft", "serta",
    "escitalopram", "lexapro", "nexito", "cipralex",
    "fluoxetine", "prozac", "flunil",
    "paroxetine", "paxil",
    "venlafaxine", "effexor", "venlor",
    "duloxetine", "cymbalta", "duvanta",
    "mirtazapine", "remeron", "mirtaz",
    "bupropion", "wellbutrin",
    # Anxiolytics / sedatives (Schedule H — restricted)
    "alprazolam", "xanax", "alprax",
    "diazepam", "valium",
    "lorazepam", "ativan",
    "clonazepam",   # already listed above
    "zolpidem", "stilnoct",
    "nitrazepam", "nitrest",
    # Newer diabetes (SGLT2 / DPP4 — high cost, limited supply chains)
    "sitagliptin", "januvia",
    "empagliflozin", "jardiance",
    "dapagliflozin", "farxiga", "forxiga",
    "vildagliptin", "galvus",
    "teneligliptin",
    "canagliflozin", "invokana",
    "saxagliptin", "onglyza",
    # Cardiac specialty
    "furosemide", "lasix",
    "spironolactone", "aldactone",
    "warfarin", "coumadin",
    "digoxin", "lanoxin",
    "amiodarone", "cordarone",
    "ivabradine", "coralan",
    "ranolazine", "ranexa",
    # Lithium
    "lithium", "lithosun",
}

# Tier 4 – Rare / hospital-only
TIER4_RARE = {
    # Antipsychotics
    "quetiapine", "seroquel", "qutan",
    "risperidone", "risperdal", "risnia",
    "olanzapine", "zyprexa", "oleanz",
    "clozapine", "clozaril", "sizopin",
    "haloperidol", "haldol",
    "aripiprazole", "abilify", "arip",
    "paliperidone", "invega",
    # Immunosuppressants
    "tacrolimus", "prograf",
    "cyclosporine", "neoral", "sandimmun",
    "mycophenolate", "cellcept",
    "azathioprine", "imuran",
    # Targeted oncology
    "imatinib", "gleevec", "glivec",
    "erlotinib", "tarceva",
    "gefitinib", "iressa",
    # Chemo / DMARDs
    "methotrexate",
    "cyclophosphamide",
    "rituximab",
    "trastuzumab",
    "infliximab", "remicade",
    "adalimumab", "humira",
}

# Flat set used for quick lookup (common = tier1 + tier2)
COMMON_MEDS = TIER1_OTC | TIER2_RX_COMMON

_ALL_TIERS = [
    ("tier1", TIER1_OTC),
    ("tier2", TIER2_RX_COMMON),
    ("tier3", TIER3_SPECIALTY),
    ("tier4", TIER4_RARE),
]

# Weight applied per tier when computing "prescription commonality"
_TIER_COMMONALITY = {"tier1": 1.0, "tier2": 0.70, "tier3": 0.20, "tier4": 0.0}


def _get_tier(name: str) -> str:
    """Return the tier string for a medicine name (case-insensitive)."""
    n = name.lower().strip()
    for tier_id, tier_set in _ALL_TIERS:
        if n in tier_set:
            return tier_id
    # Substring fallback: handle brand/salt combos (e.g. "amoxicillin 500mg")
    for tier_id, tier_set in _ALL_TIERS:
        for entry in tier_set:
            if len(entry) >= 5 and (entry in n or n in entry):
                return tier_id
    return "tier2"  # conservative default: treat unknown as common Rx


# ---------------------------------------------------------------------------
# Pharmacy catalogue
# ---------------------------------------------------------------------------
# Inventory values represent estimated stock probability (0.0 – 1.0):
#   1.00 = always in stock
#   0.90 = almost always in stock
#   0.70 = usually in stock
#   0.40 = sometimes in stock
#   0.20 = rarely in stock
#   0.00 = not stocked

PHARMACIES = [
    {
        "id": "p1",
        "name": "MedPlus - Lajpat Nagar",
        "address": "B-12, Lajpat Nagar II, New Delhi",
        "lat": 28.5672,
        "lng": 77.2360,
        "reliability": 0.93,
        "is_24h": False,
        "phone": "040-6700-6700",
        "operating_hours": "9:00 AM – 10:00 PM",
        "specialties": ["general", "neurology", "cardiology"],
        "inventory": {
            # --- Tier 1 (OTC) – always stocked ---
            "paracetamol": 1.00, "ibuprofen": 1.00, "aspirin": 1.00,
            "diclofenac": 0.98, "aceclofenac": 0.97, "naproxen": 0.95,
            "cetirizine": 1.00, "levocetirizine": 0.97, "fexofenadine": 0.95,
            "loratadine": 0.95, "chlorpheniramine": 0.98,
            "omeprazole": 1.00, "pantoprazole": 0.98, "ranitidine": 0.95,
            "domperidone": 0.97, "antacid": 1.00, "ors": 1.00,
            "vitamin c": 1.00, "vitamin d": 1.00, "vitamin d3": 1.00,
            "vitamin b12": 1.00, "folic acid": 1.00, "calcium": 1.00,
            "zinc": 0.98, "iron": 0.97, "magnesium": 0.95,
            "multivitamin": 1.00, "vitamin b complex": 1.00,
            "betadine": 0.97, "clotrimazole": 0.95,
            # --- Tier 2 – common Rx ---
            "metformin": 0.95, "glimepiride": 0.90, "insulin": 0.85,
            "atorvastatin": 0.95, "rosuvastatin": 0.90,
            "amlodipine": 0.95, "metoprolol": 0.92, "telmisartan": 0.88,
            "losartan": 0.88, "ramipril": 0.85, "bisoprolol": 0.85,
            "clopidogrel": 0.90, "nitroglycerin": 0.88,
            "azithromycin": 0.95, "amoxicillin": 0.95, "doxycycline": 0.90,
            "ciprofloxacin": 0.90, "levofloxacin": 0.88, "cefixime": 0.88,
            "metronidazole": 0.90, "cotrimoxazole": 0.88,
            "levothyroxine": 0.90, "prednisolone": 0.92, "dexamethasone": 0.88,
            "salbutamol": 0.92, "montelukast": 0.90,
            "metoclopramide": 0.90, "ondansetron": 0.88,
            "esomeprazole": 0.88, "rabeprazole": 0.88,
            "tramadol": 0.80, "meloxicam": 0.88,
            # --- Tier 3 – neurology specialty ---
            "levetiracetam": 0.92, "valproate": 0.88, "carbamazepine": 0.88,
            "phenytoin": 0.85, "lamotrigine": 0.82, "oxcarbazepine": 0.78,
            "topiramate": 0.78, "clonazepam": 0.80, "phenobarbitone": 0.75,
            "pregabalin": 0.85, "gabapentin": 0.82,
            # Tier 3 – cardiac specialty
            "furosemide": 0.85, "spironolactone": 0.80, "warfarin": 0.75,
            "digoxin": 0.72, "amiodarone": 0.65,
            # Tier 3 – psychotropics (some stocked given general demand)
            "sertraline": 0.72, "escitalopram": 0.70, "alprazolam": 0.65,
            # Tier 3 – newer diabetes (limited)
            "sitagliptin": 0.55, "empagliflozin": 0.45, "dapagliflozin": 0.40,
        },
    },
    {
        "id": "p2",
        "name": "Apollo Pharmacy - GK1",
        "address": "M-44, Greater Kailash I, New Delhi",
        "lat": 28.5494,
        "lng": 77.2341,
        "reliability": 0.95,
        "is_24h": True,
        "phone": "1860-500-0101",
        "operating_hours": "Open 24/7",
        "specialties": ["general", "oncology", "diabetes", "cardiac"],
        "inventory": {
            # --- Tier 1 – always stocked (large 24h chain) ---
            "paracetamol": 1.00, "ibuprofen": 1.00, "aspirin": 1.00,
            "diclofenac": 0.98, "aceclofenac": 0.98, "naproxen": 0.97,
            "cetirizine": 1.00, "levocetirizine": 0.98, "fexofenadine": 0.97,
            "loratadine": 0.97, "chlorpheniramine": 0.98,
            "omeprazole": 1.00, "pantoprazole": 0.99, "ranitidine": 0.97,
            "famotidine": 0.95, "domperidone": 0.98, "antacid": 1.00, "ors": 1.00,
            "vitamin c": 1.00, "vitamin d": 1.00, "vitamin d3": 1.00,
            "vitamin b12": 1.00, "folic acid": 1.00, "calcium": 1.00,
            "zinc": 0.99, "iron": 0.98, "magnesium": 0.97,
            "multivitamin": 1.00, "vitamin b complex": 1.00,
            "betadine": 0.98, "clotrimazole": 0.97,
            # --- Tier 2 – very strong diabetes & cardiac focus ---
            "metformin": 1.00, "glimepiride": 0.97, "glipizide": 0.92,
            "insulin": 0.95, "voglibose": 0.90,
            "atorvastatin": 0.98, "rosuvastatin": 0.95, "fenofibrate": 0.90,
            "amlodipine": 0.97, "metoprolol": 0.95, "telmisartan": 0.93,
            "losartan": 0.92, "ramipril": 0.92, "bisoprolol": 0.90,
            "enalapril": 0.88, "nebivolol": 0.85, "hydrochlorothiazide": 0.88,
            "clopidogrel": 0.95, "nitroglycerin": 0.92, "isosorbide": 0.88,
            "azithromycin": 0.97, "amoxicillin": 0.97, "doxycycline": 0.92,
            "ciprofloxacin": 0.92, "levofloxacin": 0.92, "cefixime": 0.90,
            "cefpodoxime": 0.88, "metronidazole": 0.92, "cotrimoxazole": 0.90,
            "levothyroxine": 0.95, "prednisolone": 0.95, "dexamethasone": 0.92,
            "methylprednisolone": 0.88, "budesonide": 0.88,
            "salbutamol": 0.95, "montelukast": 0.93, "fluticasone": 0.88,
            "metoclopramide": 0.92, "ondansetron": 0.92,
            "esomeprazole": 0.92, "rabeprazole": 0.90,
            "tramadol": 0.85, "meloxicam": 0.90,
            "hydroxychloroquine": 0.88, "albendazole": 0.90,
            "tamsulosin": 0.88, "sildenafil": 0.85,
            # --- Tier 3 – diabetes specialty ---
            "sitagliptin": 0.88, "empagliflozin": 0.85, "dapagliflozin": 0.82,
            "vildagliptin": 0.80, "teneligliptin": 0.75, "canagliflozin": 0.70,
            # Tier 3 – cardiac specialty
            "furosemide": 0.90, "spironolactone": 0.88, "warfarin": 0.85,
            "digoxin": 0.82, "amiodarone": 0.78, "ivabradine": 0.72,
            # Tier 3 – psychotropics
            "sertraline": 0.75, "escitalopram": 0.72, "fluoxetine": 0.70,
            "alprazolam": 0.65, "diazepam": 0.60,
            # Tier 3 – anti-epileptics (limited)
            "levetiracetam": 0.60, "valproate": 0.55, "carbamazepine": 0.55,
            "pregabalin": 0.65, "gabapentin": 0.60,
            # Tier 4 – oncology (Apollo specialty)
            "methotrexate": 0.60, "imatinib": 0.50, "rituximab": 0.35,
            "tacrolimus": 0.45, "mycophenolate": 0.42,
        },
    },
    {
        "id": "p3",
        "name": "1mg Store - Saket",
        "address": "D-7, Saket District Centre, New Delhi",
        "lat": 28.5245,
        "lng": 77.2066,
        "reliability": 0.88,
        "is_24h": False,
        "phone": "0124-416-6666",
        "operating_hours": "8:00 AM – 10:00 PM",
        "specialties": ["general", "wellness", "vitamins"],
        "inventory": {
            # --- Tier 1 – wellness store: vitamins/supplements at 1.0 ---
            "paracetamol": 1.00, "ibuprofen": 1.00, "aspirin": 0.98,
            "diclofenac": 0.95, "aceclofenac": 0.92, "naproxen": 0.90,
            "cetirizine": 1.00, "levocetirizine": 0.97, "fexofenadine": 0.95,
            "loratadine": 0.95, "chlorpheniramine": 0.95,
            "omeprazole": 0.97, "pantoprazole": 0.97, "ranitidine": 0.92,
            "domperidone": 0.95, "antacid": 0.98, "ors": 0.98,
            "vitamin c": 1.00, "vitamin d": 1.00, "vitamin d3": 1.00,
            "vitamin b12": 1.00, "folic acid": 1.00, "calcium": 1.00,
            "zinc": 1.00, "iron": 1.00, "magnesium": 1.00,
            "multivitamin": 1.00, "vitamin b complex": 1.00,
            "betadine": 0.92, "clotrimazole": 0.90,
            # --- Tier 2 – moderate general Rx ---
            "metformin": 0.88, "glimepiride": 0.82, "insulin": 0.75,
            "atorvastatin": 0.88, "rosuvastatin": 0.85,
            "amlodipine": 0.88, "metoprolol": 0.85, "telmisartan": 0.82,
            "losartan": 0.80, "ramipril": 0.78,
            "clopidogrel": 0.82, "nitroglycerin": 0.75,
            "azithromycin": 0.88, "amoxicillin": 0.88, "doxycycline": 0.82,
            "ciprofloxacin": 0.82, "levofloxacin": 0.80, "cefixime": 0.80,
            "metronidazole": 0.82, "cotrimoxazole": 0.80,
            "levothyroxine": 0.85, "prednisolone": 0.82, "dexamethasone": 0.78,
            "salbutamol": 0.85, "montelukast": 0.82,
            "metoclopramide": 0.80, "ondansetron": 0.80,
            "esomeprazole": 0.85, "rabeprazole": 0.82,
            "tramadol": 0.65, "meloxicam": 0.80,
            "albendazole": 0.85, "hydroxychloroquine": 0.72,
            # --- Tier 3 – very limited ---
            "pregabalin": 0.45, "gabapentin": 0.40,
            "sertraline": 0.42, "escitalopram": 0.40,
            "levetiracetam": 0.25, "valproate": 0.22,
            "sitagliptin": 0.45, "empagliflozin": 0.35,
            "furosemide": 0.50, "spironolactone": 0.45, "warfarin": 0.35,
        },
    },
    {
        "id": "p4",
        "name": "Jan Aushadhi - Nehru Place",
        "address": "Pocket 5, Nehru Place, New Delhi",
        "lat": 28.5491,
        "lng": 77.2523,
        "reliability": 0.84,
        "is_24h": False,
        "phone": "1800-180-8080",
        "operating_hours": "10:00 AM – 8:00 PM",
        "specialties": ["general", "generic"],
        "inventory": {
            # --- Tier 1 – Jan Aushadhi stocks all essential generics ---
            "paracetamol": 1.00, "ibuprofen": 1.00, "aspirin": 1.00,
            "diclofenac": 0.97, "aceclofenac": 0.95, "naproxen": 0.92,
            "cetirizine": 1.00, "levocetirizine": 0.95, "chlorpheniramine": 0.97,
            "fexofenadine": 0.85, "loratadine": 0.88,
            "omeprazole": 1.00, "pantoprazole": 0.98, "ranitidine": 0.97,
            "domperidone": 0.97, "antacid": 1.00, "ors": 1.00,
            "vitamin c": 1.00, "vitamin d": 0.95, "vitamin d3": 0.95,
            "vitamin b12": 1.00, "folic acid": 1.00, "calcium": 1.00,
            "zinc": 0.95, "iron": 0.97, "magnesium": 0.90,
            "multivitamin": 0.95, "vitamin b complex": 0.97,
            "betadine": 0.92, "clotrimazole": 0.90,
            # --- Tier 2 – extremely strong on generic blockbusters ---
            "metformin": 1.00, "glimepiride": 0.98, "glipizide": 0.92,
            "voglibose": 0.88, "insulin": 0.80,
            "atorvastatin": 0.98, "rosuvastatin": 0.92,
            "amlodipine": 1.00, "metoprolol": 0.97, "telmisartan": 0.95,
            "losartan": 0.95, "ramipril": 0.95, "bisoprolol": 0.92,
            "enalapril": 0.92, "hydrochlorothiazide": 0.90,
            "clopidogrel": 0.95, "nitroglycerin": 0.90,
            "azithromycin": 0.97, "amoxicillin": 0.98, "doxycycline": 0.95,
            "ciprofloxacin": 0.95, "levofloxacin": 0.92, "cefixime": 0.93,
            "metronidazole": 0.95, "cotrimoxazole": 0.95, "albendazole": 0.95,
            "levothyroxine": 0.95, "prednisolone": 0.95, "dexamethasone": 0.92,
            "salbutamol": 0.95, "montelukast": 0.88, "budesonide": 0.82,
            "metoclopramide": 0.92, "ondansetron": 0.85,
            "esomeprazole": 0.88, "rabeprazole": 0.85,
            "tramadol": 0.80, "meloxicam": 0.88,
            "hydroxychloroquine": 0.85, "tamsulosin": 0.90, "finasteride": 0.88,
            # --- Tier 3 – limited but some common ones ---
            "furosemide": 0.88, "spironolactone": 0.82,
            "warfarin": 0.65, "digoxin": 0.70,
            "sertraline": 0.55, "escitalopram": 0.52, "fluoxetine": 0.55,
            "alprazolam": 0.50, "diazepam": 0.52,
            "pregabalin": 0.50, "gabapentin": 0.55,
            "levetiracetam": 0.45, "valproate": 0.45, "carbamazepine": 0.48,
            "phenytoin": 0.50,
            "sitagliptin": 0.55, "empagliflozin": 0.35,
        },
    },
    {
        "id": "p5",
        "name": "Wellness Forever - South Ex",
        "address": "A-14, South Extension I, New Delhi",
        "lat": 28.5732,
        "lng": 77.2208,
        "reliability": 0.90,
        "is_24h": True,
        "phone": "1800-209-4400",
        "operating_hours": "Open 24/7",
        "specialties": ["general", "neurology", "psychiatry"],
        "inventory": {
            # --- Tier 1 – always stocked (24h) ---
            "paracetamol": 1.00, "ibuprofen": 1.00, "aspirin": 0.99,
            "diclofenac": 0.97, "aceclofenac": 0.97, "naproxen": 0.95,
            "cetirizine": 1.00, "levocetirizine": 0.98, "fexofenadine": 0.96,
            "loratadine": 0.96, "chlorpheniramine": 0.97,
            "omeprazole": 1.00, "pantoprazole": 0.98, "ranitidine": 0.95,
            "domperidone": 0.97, "antacid": 1.00, "ors": 1.00,
            "vitamin c": 1.00, "vitamin d": 1.00, "vitamin d3": 1.00,
            "vitamin b12": 1.00, "folic acid": 1.00, "calcium": 1.00,
            "zinc": 0.98, "iron": 0.97, "magnesium": 0.96,
            "multivitamin": 1.00, "vitamin b complex": 1.00,
            "betadine": 0.96, "clotrimazole": 0.94,
            # --- Tier 2 – broad general Rx ---
            "metformin": 0.92, "glimepiride": 0.88, "insulin": 0.82,
            "atorvastatin": 0.92, "rosuvastatin": 0.88,
            "amlodipine": 0.92, "metoprolol": 0.90, "telmisartan": 0.88,
            "losartan": 0.85, "ramipril": 0.85, "bisoprolol": 0.82,
            "clopidogrel": 0.88,
            "azithromycin": 0.92, "amoxicillin": 0.92, "doxycycline": 0.88,
            "ciprofloxacin": 0.88, "levofloxacin": 0.85, "cefixime": 0.85,
            "metronidazole": 0.88, "cotrimoxazole": 0.85,
            "levothyroxine": 0.90, "prednisolone": 0.90, "dexamethasone": 0.85,
            "salbutamol": 0.90, "montelukast": 0.88,
            "metoclopramide": 0.88, "ondansetron": 0.88,
            "esomeprazole": 0.87, "tramadol": 0.78,
            # --- Tier 3 – neurology & psychiatry specialty ---
            "levetiracetam": 0.92, "valproate": 0.90, "carbamazepine": 0.90,
            "phenytoin": 0.87, "lamotrigine": 0.85, "oxcarbazepine": 0.82,
            "topiramate": 0.82, "clonazepam": 0.88, "phenobarbitone": 0.80,
            "pregabalin": 0.90, "gabapentin": 0.88,
            "sertraline": 0.92, "escitalopram": 0.90, "fluoxetine": 0.88,
            "paroxetine": 0.82, "venlafaxine": 0.82, "duloxetine": 0.80,
            "mirtazapine": 0.75, "bupropion": 0.70,
            "alprazolam": 0.82, "diazepam": 0.78, "lorazepam": 0.75,
            "zolpidem": 0.70, "nitrazepam": 0.65,
            "lithium": 0.78,
            # Tier 3 – newer diabetes (moderate)
            "sitagliptin": 0.55, "empagliflozin": 0.48, "dapagliflozin": 0.45,
            # Tier 4 – antipsychotics (psychiatry specialty)
            "quetiapine": 0.78, "risperidone": 0.75, "olanzapine": 0.72,
            "aripiprazole": 0.68, "haloperidol": 0.65, "clozapine": 0.45,
        },
    },
    {
        "id": "p6",
        "name": "Guardian Pharmacy - Hauz Khas",
        "address": "29, Hauz Khas Village, New Delhi",
        "lat": 28.5494,
        "lng": 77.2001,
        "reliability": 0.89,
        "is_24h": False,
        "phone": "+91-9205780424",
        "operating_hours": "08:00 AM – 10:00 PM",
        "specialties": ["general", "cardiac", "diabetes", "respiratory"],
        "inventory": {
            # --- Tier 1 ---
            "paracetamol": 1.00, "ibuprofen": 1.00, "aspirin": 1.00,
            "diclofenac": 0.97, "aceclofenac": 0.97, "naproxen": 0.95,
            "cetirizine": 1.00, "levocetirizine": 0.97, "fexofenadine": 0.95,
            "loratadine": 0.95, "chlorpheniramine": 0.97,
            "omeprazole": 1.00, "pantoprazole": 0.98, "ranitidine": 0.95,
            "domperidone": 0.97, "antacid": 1.00, "ors": 1.00,
            "vitamin c": 1.00, "vitamin d": 1.00, "vitamin d3": 1.00,
            "vitamin b12": 1.00, "folic acid": 1.00, "calcium": 1.00,
            "zinc": 0.98, "iron": 0.97, "magnesium": 0.95,
            "multivitamin": 1.00, "vitamin b complex": 1.00,
            "betadine": 0.95, "clotrimazole": 0.93,
            # --- Tier 2 – cardiac, diabetes, respiratory specialty ---
            "metformin": 1.00, "glimepiride": 0.97, "glipizide": 0.92,
            "insulin": 0.88, "voglibose": 0.88,
            "atorvastatin": 0.98, "rosuvastatin": 0.95, "fenofibrate": 0.88,
            "amlodipine": 0.98, "metoprolol": 0.97, "telmisartan": 0.95,
            "losartan": 0.95, "ramipril": 0.93, "bisoprolol": 0.92,
            "enalapril": 0.90, "nebivolol": 0.88, "hydrochlorothiazide": 0.90,
            "clopidogrel": 0.95, "nitroglycerin": 0.92, "isosorbide": 0.88,
            "azithromycin": 0.95, "amoxicillin": 0.95, "doxycycline": 0.90,
            "ciprofloxacin": 0.90, "levofloxacin": 0.88, "cefixime": 0.88,
            "metronidazole": 0.90, "cotrimoxazole": 0.88,
            "levothyroxine": 0.92, "prednisolone": 0.92, "dexamethasone": 0.90,
            "methylprednisolone": 0.85, "budesonide": 0.90,
            "salbutamol": 0.97, "montelukast": 0.95, "levosalbutamol": 0.92,
            "ipratropium": 0.88, "fluticasone": 0.88,
            "metoclopramide": 0.90, "ondansetron": 0.88,
            "esomeprazole": 0.88, "rabeprazole": 0.85,
            "tramadol": 0.78, "meloxicam": 0.88,
            "albendazole": 0.88, "tamsulosin": 0.85,
            # --- Tier 3 – cardiac specialty ---
            "furosemide": 0.92, "spironolactone": 0.88,
            "warfarin": 0.80, "digoxin": 0.78, "amiodarone": 0.72,
            "ivabradine": 0.68, "ranolazine": 0.60,
            # Tier 3 – newer diabetes (strong focus)
            "sitagliptin": 0.85, "empagliflozin": 0.82, "dapagliflozin": 0.80,
            "vildagliptin": 0.78, "teneligliptin": 0.72, "canagliflozin": 0.65,
            # Tier 3 – limited psychotropics
            "sertraline": 0.52, "escitalopram": 0.50, "alprazolam": 0.45,
            # Tier 3 – limited neuro
            "pregabalin": 0.58, "gabapentin": 0.55,
            "levetiracetam": 0.42, "valproate": 0.40,
        },
    },
]

# ---------------------------------------------------------------------------
# Scoring weights
# ---------------------------------------------------------------------------
# Coverage is the dominant factor: does the pharmacy stock your medicines?
# Distance matters but should not wipe out a well-stocked nearby pharmacy.
WEIGHTS = {
    "coverage":   0.45,   # fraction of requested medicines in stock
    "stock_qual": 0.15,   # average stock level of available items
    "distance":   0.25,   # proximity (exponential decay)
    "reliability": 0.08,  # historical pharmacy reliability
    "hours":      0.05,   # 24 h bonus
    "specialty":  0.02,   # specialty category match
}

# ---------------------------------------------------------------------------
# Specialty → medicine category map
# ---------------------------------------------------------------------------
_NEURO_MEDS = {
    "levetiracetam", "clonazepam", "pregabalin", "gabapentin",
    "phenytoin", "valproate", "carbamazepine", "lamotrigine",
    "topiramate", "oxcarbazepine", "phenobarbitone",
}
_CARDIAC_MEDS = {
    "atorvastatin", "amlodipine", "metoprolol", "clopidogrel",
    "losartan", "ramipril", "digoxin", "warfarin", "furosemide",
    "bisoprolol", "telmisartan", "nitroglycerin", "amiodarone",
    "spironolactone", "ivabradine",
}
_DIABETES_MEDS = {
    "metformin", "glimepiride", "insulin", "sitagliptin",
    "empagliflozin", "dapagliflozin", "glipizide", "voglibose",
    "vildagliptin", "teneligliptin", "canagliflozin",
}
_PSYCH_MEDS = {
    "sertraline", "escitalopram", "alprazolam", "quetiapine",
    "risperidone", "olanzapine", "clonazepam", "diazepam",
    "fluoxetine", "venlafaxine", "duloxetine", "lithium",
    "aripiprazole", "haloperidol", "clozapine", "mirtazapine",
}
_RESP_MEDS = {
    "salbutamol", "montelukast", "budesonide", "fluticasone",
    "ipratropium", "levosalbutamol",
}
_CATEGORY_MAP = {
    "neurology":  _NEURO_MEDS,
    "cardiology": _CARDIAC_MEDS,
    "cardiac":    _CARDIAC_MEDS,
    "diabetes":   _DIABETES_MEDS,
    "psychiatry": _PSYCH_MEDS,
    "respiratory": _RESP_MEDS,
}


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _haversine(lat1, lng1, lat2, lng2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlng / 2) ** 2
    )
    return R * 2 * math.asin(math.sqrt(a))


def _dist_score(km: float) -> float:
    """Smooth exponential decay: 0 km→1.0, 3 km→0.64, 7 km→0.35, 15 km→0.10."""
    return math.exp(-0.15 * km)


def _stock_label(value: float) -> str:
    if value >= 0.80:
        return "high"
    if value >= 0.40:
        return "medium"
    if value > 0.0:
        return "low"
    return "unavailable"


# ---------------------------------------------------------------------------
# Core scoring functions
# ---------------------------------------------------------------------------

def _effective_stock(pharmacy: dict, medicine: str) -> float:
    """
    Return the stock probability for a medicine at a pharmacy.

    Priority:
    1. Exact key match in inventory
    2. Partial/substring match (brand ↔ salt, e.g. "crocin" ↔ "paracetamol")
    3. Tier-based default (OTC medicines assumed stocked at most pharmacies)
    """
    inv = pharmacy.get("inventory", {})
    name = medicine.lower().strip()

    # 1. Exact match
    if name in inv:
        return inv[name]

    # 2. Substring match (only for tokens ≥ 5 characters to avoid false hits)
    best = None
    for key, val in inv.items():
        if len(key) >= 5 and len(name) >= 5:
            if key in name or name in key:
                best = val if best is None else max(best, val)
    if best is not None:
        return best

    # 3. Tier-based default for unlisted medicines
    tier = _get_tier(name)
    if tier == "tier1":
        return 0.82   # OTC: almost certainly on shelf even if not catalogued
    if tier == "tier2":
        return 0.42   # Common Rx: decent chance, not guaranteed
    # tier3 / tier4: don't assume stocked
    return 0.0


def _coverage(pharmacy: dict, medicines: list) -> tuple:
    details = []
    supplied = 0

    for med in medicines:
        stock = _effective_stock(pharmacy, med)
        available = stock > 0.0
        if available:
            supplied += 1
        details.append({
            "medicine": med,
            "stock_level": round(stock, 2),
            "available": available,
            "stock_label": _stock_label(stock),
        })

    ratio = supplied / len(medicines) if medicines else 0.0
    return ratio, details


def _category_bonus(pharmacy: dict, medicines: list) -> float:
    meds_lower = {m.lower() for m in medicines}
    for specialty, med_set in _CATEGORY_MAP.items():
        if specialty in pharmacy.get("specialties", []) and meds_lower & med_set:
            return 1.0
    return 0.0


def _prescription_commonality(medicines: list) -> float:
    """
    Return a 0–1 score reflecting how common/OTC the medicine list is.
    1.0 = entirely OTC tier-1 items; 0.0 = entirely rare/specialty items.
    """
    if not medicines:
        return 0.0
    total = sum(_TIER_COMMONALITY.get(_get_tier(m), 0.5) for m in medicines)
    return total / len(medicines)


# ---------------------------------------------------------------------------
# Main ranking function
# ---------------------------------------------------------------------------

def rank_pharmacies(
    medicines: list,
    user_lat: float,
    user_lng: float,
    max_results: int = 6,
    max_km: float = None,
) -> list:
    """
    Rank pharmacies by fulfillment probability for the given medicine list.

    Scoring model
    ─────────────
    • For predominantly common/OTC prescriptions (commonality ≥ 0.70):
        Well-stocked pharmacies are pushed into the realistic 88–99 % bracket;
        distance differentiates within that bracket.
    • For mixed prescriptions (commonality 0.40–0.70):
        A proportional boost is applied so common components still lift the score.
    • For specialty/rare prescriptions (commonality < 0.40):
        Raw weighted score is used; only pharmacies that genuinely stock the
        medicines rank high.
    """
    results = []
    commonality = _prescription_commonality(medicines)

    for pharmacy in PHARMACIES:
        km = _haversine(user_lat, user_lng, pharmacy["lat"], pharmacy["lng"])
        if max_km and km > max_km:
            continue

        coverage_ratio, medicine_details = _coverage(pharmacy, medicines)
        available_stocks = [d["stock_level"] for d in medicine_details if d["available"]]
        avg_stock = sum(available_stocks) / len(available_stocks) if available_stocks else 0.0
        dist = _dist_score(km)

        raw_score = (
            WEIGHTS["coverage"]   * coverage_ratio
            + WEIGHTS["stock_qual"] * avg_stock
            + WEIGHTS["distance"]   * dist
            + WEIGHTS["reliability"] * pharmacy["reliability"]
            + WEIGHTS["hours"]      * (1.0 if pharmacy["is_24h"] else 0.0)
            + WEIGHTS["specialty"]  * _category_bonus(pharmacy, medicines)
        )

        # ── Tier-aware score adjustment ──────────────────────────────────────
        if commonality >= 0.70 and coverage_ratio >= 0.85:
            # Predominantly common medicines, well-stocked pharmacy.
            # Real-world expectation: ~88–99 % depending on stock quality
            # and proximity.  Distance still differentiates rank order.
            score = 0.86 + 0.10 * (coverage_ratio * avg_stock) + 0.04 * dist
            score = min(score, 0.99)

        elif commonality >= 0.40:
            # Mixed prescription: proportional lift for the common component.
            boost = 1.0 + 0.28 * commonality * coverage_ratio
            score = min(raw_score * boost, 0.97)

        else:
            # Specialty / rare medicines: raw score is the most honest signal.
            score = raw_score

        results.append({
            "id": pharmacy["id"],
            "name": pharmacy["name"],
            "address": pharmacy["address"],
            "lat": pharmacy["lat"],
            "lng": pharmacy["lng"],
            "phone": pharmacy.get("phone", ""),
            "is_24h": pharmacy["is_24h"],
            "distance_km": round(km, 2),
            "score": round(score * 100, 1),
            "coverage_pct": round(coverage_ratio * 100, 1),
            "medicines": medicine_details,
            "factor_scores": {
                "coverage":     round(coverage_ratio * 100, 1),
                "availability": round(avg_stock * 100, 1),
                "distance":     round(dist * 100, 1),
                "reliability":  round(pharmacy["reliability"] * 100, 1),
                "hours": (
                    "Open 24/7"
                    if pharmacy.get("is_24h")
                    else pharmacy.get("operating_hours", "Limited hours")
                ),
            },
        })

    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:max_results]
