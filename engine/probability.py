"""
MEDSY probability engine.

Ranks pharmacies by likelihood of fulfilling a medicine list.
"""

import math


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
        "operating_hours": "9:00 AM - 10:00 PM",
        "specialties": ["general", "neurology", "cardiology"],
        "inventory": {
            "levetiracetam": 0.9,
            "clonazepam": 0.7,
            "pregabalin": 0.4,
            "folic acid": 1.0,
            "vitamin d3": 1.0,
            "vitamin d": 1.0,
            "paracetamol": 1.0,
            "ibuprofen": 1.0,
            "amoxicillin": 0.9,
            "metformin": 0.8,
            "atorvastatin": 0.9,
            "omeprazole": 1.0,
            "cetirizine": 1.0,
            "azithromycin": 0.85,
            "pantoprazole": 0.95,
            "amlodipine": 0.9,
            "metoprolol": 0.8,
            "ramipril": 0.75,
            "sertraline": 0.7,
            "escitalopram": 0.65,
            "aspirin": 1.0,
        },
    },
    {
        "id": "p2",
        "name": "Apollo Pharmacy - GK1",
        "address": "M-44, Greater Kailash I, New Delhi",
        "lat": 28.5494,
        "lng": 77.2341,
        "reliability": 0.91,
        "is_24h": True,
        "phone": "1860-500-0101",
        "operating_hours": "Open 24/7",
        "specialties": ["general", "oncology", "diabetes", "cardiac"],
        "inventory": {
            "levetiracetam": 0.6,
            "clonazepam": 0.5,
            "pregabalin": 0.8,
            "folic acid": 0.9,
            "vitamin d3": 0.95,
            "vitamin d": 0.95,
            "paracetamol": 1.0,
            "ibuprofen": 0.95,
            "amoxicillin": 1.0,
            "metformin": 0.95,
            "glimepiride": 0.9,
            "insulin": 0.85,
            "atorvastatin": 0.95,
            "clopidogrel": 0.85,
            "aspirin": 1.0,
            "omeprazole": 0.9,
            "cetirizine": 0.9,
            "azithromycin": 0.9,
            "levothyroxine": 0.9,
            "dexamethasone": 0.7,
            "sitagliptin": 0.8,
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
        "operating_hours": "8:00 AM - 10:00 PM",
        "specialties": ["general", "wellness", "vitamins"],
        "inventory": {
            "folic acid": 1.0,
            "vitamin d3": 1.0,
            "vitamin d": 1.0,
            "vitamin b12": 1.0,
            "calcium": 1.0,
            "zinc": 1.0,
            "magnesium": 0.9,
            "paracetamol": 1.0,
            "ibuprofen": 1.0,
            "cetirizine": 1.0,
            "omeprazole": 0.85,
            "pantoprazole": 0.9,
            "metformin": 0.75,
            "atorvastatin": 0.8,
            "levetiracetam": 0.3,
            "clonazepam": 0.2,
            "pregabalin": 0.6,
            "azithromycin": 0.7,
            "amoxicillin": 0.75,
            "multivitamin": 1.0,
        },
    },
    {
        "id": "p4",
        "name": "Jan Aushadhi - Nehru Place",
        "address": "Pocket 5, Nehru Place, New Delhi",
        "lat": 28.5491,
        "lng": 77.2523,
        "reliability": 0.82,
        "is_24h": False,
        "phone": "1800-180-8080",
        "operating_hours": "10:00 AM - 8:00 PM",
        "specialties": ["general", "generic"],
        "inventory": {
            "paracetamol": 1.0,
            "amoxicillin": 0.9,
            "metformin": 0.95,
            "atorvastatin": 0.7,
            "omeprazole": 0.9,
            "ibuprofen": 0.95,
            "cetirizine": 0.85,
            "folic acid": 0.8,
            "vitamin d": 0.7,
            "aspirin": 1.0,
            "ramipril": 0.6,
            "metoprolol": 0.65,
            "levothyroxine": 0.75,
            "doxycycline": 0.8,
        },
    },
    {
        "id": "p5",
        "name": "Wellness Forever - South Ex",
        "address": "A-14, South Extension I, New Delhi",
        "lat": 28.5732,
        "lng": 77.2208,
        "reliability": 0.87,
        "is_24h": True,
        "phone": "1800-209-4400",
        "operating_hours": "Open 24/7",
        "specialties": ["general", "neurology", "psychiatry"],
        "inventory": {
            "levetiracetam": 0.85,
            "clonazepam": 0.9,
            "pregabalin": 0.9,
            "sertraline": 0.9,
            "escitalopram": 0.85,
            "alprazolam": 0.7,
            "quetiapine": 0.65,
            "risperidone": 0.6,
            "olanzapine": 0.55,
            "paracetamol": 1.0,
            "ibuprofen": 0.9,
            "cetirizine": 0.9,
            "omeprazole": 0.85,
            "folic acid": 0.9,
            "vitamin d": 0.85,
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
        "operating_hours": "08:00 AM - 10:00 PM",
        "specialties": ["general", "cardiac", "diabetes", "respiratory"],
        "inventory": {
            "metformin": 1.0,
            "glimepiride": 0.95,
            "sitagliptin": 0.8,
            "empagliflozin": 0.7,
            "dapagliflozin": 0.65,
            "atorvastatin": 0.95,
            "amlodipine": 0.9,
            "losartan": 0.85,
            "salbutamol": 0.9,
            "montelukast": 0.85,
            "budesonide": 0.7,
            "paracetamol": 1.0,
            "ibuprofen": 0.95,
            "azithromycin": 0.9,
            "cetirizine": 0.9,
            "folic acid": 0.85,
            "vitamin d": 0.8,
            "omeprazole": 0.9,
            "pantoprazole": 0.85,
            "clopidogrel": 0.8,
        },
    },
]

WEIGHTS = {
    "coverage": 0.35,
    "availability": 0.15,
    "distance": 0.40,
    "reliability": 0.05,
    "hours": 0.03,
    "category": 0.02,
}

NEURO = {
    "levetiracetam",
    "clonazepam",
    "pregabalin",
    "gabapentin",
    "phenytoin",
    "valproate",
    "carbamazepine",
    "lamotrigine",
    "topiramate",
}
CARDIAC = {
    "atorvastatin",
    "amlodipine",
    "metoprolol",
    "clopidogrel",
    "losartan",
    "ramipril",
    "digoxin",
    "warfarin",
    "furosemide",
}
DIABETES = {
    "metformin",
    "glimepiride",
    "insulin",
    "sitagliptin",
    "empagliflozin",
    "dapagliflozin",
    "glipizide",
}
PSYCH = {
    "sertraline",
    "escitalopram",
    "alprazolam",
    "quetiapine",
    "risperidone",
    "olanzapine",
    "clonazepam",
    "diazepam",
}
RESP = {"salbutamol", "montelukast", "budesonide", "fluticasone", "ipratropium"}

CATEGORY_MAP = {
    "neurology": NEURO,
    "cardiac": CARDIAC,
    "cardiology": CARDIAC,
    "diabetes": DIABETES,
    "psychiatry": PSYCH,
    "respiratory": RESP,
}

COMMON_MEDS = {
    "paracetamol", "ibuprofen", "aspirin", "cetirizine", "omeprazole",
    "vitamin d", "vitamin d3", "calcium", "zinc", "magnesium", "folic acid",
    "pantoprazole", "amoxicillin", "azithromycin", "multivitamin", "vitamin b12",
    "dexamethasone", "salbutamol"
}


def _haversine(lat1, lng1, lat2, lng2):
    radius_km = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlng / 2) ** 2
    )
    return radius_km * 2 * math.asin(math.sqrt(a))


def _dist_score(km):
    return math.exp(-0.15 * km)


def _stock_label(value):
    if value >= 0.7:
        return "high"
    if value >= 0.3:
        return "medium"
    if value > 0.0:
        return "low"
    return "unavailable"


def _coverage(pharmacy, medicines):
    inventory = pharmacy.get("inventory", {})
    details = []
    supplied = 0

    for med in medicines:
        med_lower = med.lower()
        stock = inventory.get(med_lower)
        if stock is None:
            stock = next((value for key, value in inventory.items() if key in med_lower or med_lower in key), 0.0)
        available = stock > 0.0
        if available:
            supplied += 1

        details.append(
            {
                "medicine": med,
                "stock_level": round(stock, 2),
                "available": available,
                "stock_label": _stock_label(stock),
            }
        )

    ratio = supplied / len(medicines) if medicines else 0
    return ratio, details


def _category_bonus(pharmacy, medicines):
    meds_lower = {med.lower() for med in medicines}
    for specialty, med_set in CATEGORY_MAP.items():
        if specialty in pharmacy.get("specialties", []) and meds_lower & med_set:
            return 1.0
    return 0.0


def rank_pharmacies(medicines, user_lat, user_lng, max_results=6, max_km=None):
    results = []

    for pharmacy in PHARMACIES:
        km = _haversine(user_lat, user_lng, pharmacy["lat"], pharmacy["lng"])
        if max_km and km > max_km:
            continue

        coverage_ratio, medicine_details = _coverage(pharmacy, medicines)
        available_levels = [item["stock_level"] for item in medicine_details if item["available"]]
        average_stock = sum(available_levels) / len(available_levels) if available_levels else 0.0

        common_medicines_count = sum(1 for m in medicines if m.lower() in COMMON_MEDS)
        common_ratio = common_medicines_count / len(medicines) if medicines else 0

        # Base engine calculation
        raw_score = (
            WEIGHTS["coverage"] * coverage_ratio
            + WEIGHTS["availability"] * average_stock
            + WEIGHTS["distance"] * _dist_score(km)
            + WEIGHTS["reliability"] * pharmacy["reliability"]
            + WEIGHTS["hours"] * (1.0 if pharmacy["is_24h"] else 0.0)
            + WEIGHTS["category"] * _category_bonus(pharmacy, medicines)
        )

        # Dynamic common medicine boost logic (to override distance penalization for easily found items)
        if common_ratio > 0.5 and coverage_ratio >= 0.9:
            # If the script is predominantly common and the pharmacy stocks it all, 
            # push the score automatically up to realistic 90-100% bracket based loosely on proximity.
            score = 0.90 + (0.09 * _dist_score(km))
        else:
            score = raw_score

        results.append(
            {
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
                    "coverage": round(coverage_ratio * 100, 1),
                    "availability": round(average_stock * 100, 1),
                    "distance": round(_dist_score(km) * 100, 1),
                    "reliability": round(pharmacy["reliability"] * 100, 1),
                    "hours": pharmacy.get("operating_hours", "Open 24/7" if pharmacy.get("is_24h") else "Limited hours"),
                },
            }
        )

    results.sort(key=lambda item: item["score"], reverse=True)
    return results[:max_results]
