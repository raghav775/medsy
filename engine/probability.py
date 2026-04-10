"""
MEDSY — Probability Engine
Ranks pharmacies by likelihood of fulfilling a medicine list.

Scoring factors (weighted sum, normalised to 0-100):
  coverage      40% — what fraction of medicines the pharmacy stocks
  availability  20% — average stock level of those medicines
  distance      20% — exponential decay (closer = better)
  reliability   12% — historical fill-rate score per pharmacy
  hours          5% — bonus for 24h operation
  category       3% — specialty match (neuro, cardiac, diabetic, etc.)
"""

import math
from typing import Optional

# ─── Pharmacy database ────────────────────────────────────────────────────────
# Replace / extend with real data or a SQLite DB.
# inventory keys are lowercase medicine name fragments.
# stock values: 1.0 = fully stocked  |  0.0 = out of stock
PHARMACIES = [
    {
        "id": "p1", "name": "MedPlus — Lajpat Nagar",
        "lat": 28.5672, "lng": 77.2360,
        "reliability": 0.93, "is_24h": True, "phone": "+91-11-2983-1111",
        "specialties": ["general","neurology","cardiology"],
        "inventory": {
            "levetiracetam":0.9,"clonazepam":0.7,"pregabalin":0.4,
            "folic acid":1.0,"vitamin d3":1.0,"vitamin d":1.0,
            "paracetamol":1.0,"ibuprofen":1.0,"amoxicillin":0.9,
            "metformin":0.8,"atorvastatin":0.9,"omeprazole":1.0,
            "cetirizine":1.0,"azithromycin":0.85,"pantoprazole":0.95,
            "amlodipine":0.9,"metoprolol":0.8,"ramipril":0.75,
            "sertraline":0.7,"escitalopram":0.65,"aspirin":1.0,
        }
    },
    {
        "id": "p2", "name": "Apollo Pharmacy — GK1",
        "lat": 28.5494, "lng": 77.2341,
        "reliability": 0.91, "is_24h": True, "phone": "+91-11-2643-2222",
        "specialties": ["general","oncology","diabetes","cardiac"],
        "inventory": {
            "levetiracetam":0.6,"clonazepam":0.5,"pregabalin":0.8,
            "folic acid":0.9,"vitamin d3":0.95,"vitamin d":0.95,
            "paracetamol":1.0,"ibuprofen":0.95,"amoxicillin":1.0,
            "metformin":0.95,"glimepiride":0.9,"insulin":0.85,
            "atorvastatin":0.95,"clopidogrel":0.85,"aspirin":1.0,
            "omeprazole":0.9,"cetirizine":0.9,"azithromycin":0.9,
            "levothyroxine":0.9,"dexamethasone":0.7,"sitagliptin":0.8,
        }
    },
    {
        "id": "p3", "name": "1mg Store — Saket",
        "lat": 28.5245, "lng": 77.2066,
        "reliability": 0.88, "is_24h": False, "phone": "+91-11-4100-3333",
        "specialties": ["general","wellness","vitamins"],
        "inventory": {
            "folic acid":1.0,"vitamin d3":1.0,"vitamin d":1.0,
            "vitamin b12":1.0,"calcium":1.0,"zinc":1.0,"magnesium":0.9,
            "paracetamol":1.0,"ibuprofen":1.0,"cetirizine":1.0,
            "omeprazole":0.85,"pantoprazole":0.9,
            "metformin":0.75,"atorvastatin":0.8,
            "levetiracetam":0.3,"clonazepam":0.2,"pregabalin":0.6,
            "azithromycin":0.7,"amoxicillin":0.75,"multivitamin":1.0,
        }
    },
    {
        "id": "p4", "name": "Jan Aushadhi — Nehru Place",
        "lat": 28.5491, "lng": 77.2523,
        "reliability": 0.82, "is_24h": False, "phone": "+91-11-2646-4444",
        "specialties": ["general","generic"],
        "inventory": {
            "paracetamol":1.0,"amoxicillin":0.9,"metformin":0.95,
            "atorvastatin":0.7,"omeprazole":0.9,"ibuprofen":0.95,
            "cetirizine":0.85,"folic acid":0.8,"vitamin d":0.7,
            "aspirin":1.0,"ramipril":0.6,"metoprolol":0.65,
            "levothyroxine":0.75,"doxycycline":0.8,
        }
    },
    {
        "id": "p5", "name": "Wellness Forever — South Ex",
        "lat": 28.5732, "lng": 77.2208,
        "reliability": 0.87, "is_24h": False, "phone": "+91-11-2462-5555",
        "specialties": ["general","neurology","psychiatry"],
        "inventory": {
            "levetiracetam":0.85,"clonazepam":0.9,"pregabalin":0.9,
            "sertraline":0.9,"escitalopram":0.85,"alprazolam":0.7,
            "quetiapine":0.65,"risperidone":0.6,"olanzapine":0.55,
            "paracetamol":1.0,"ibuprofen":0.9,"cetirizine":0.9,
            "omeprazole":0.85,"folic acid":0.9,"vitamin d":0.85,
        }
    },
    {
        "id": "p6", "name": "Guardian Pharmacy — Hauz Khas",
        "lat": 28.5494, "lng": 77.2001,
        "reliability": 0.89, "is_24h": True, "phone": "+91-11-2686-6666",
        "specialties": ["general","cardiac","diabetes","respiratory"],
        "inventory": {
            "metformin":1.0,"glimepiride":0.95,"sitagliptin":0.8,
            "empagliflozin":0.7,"dapagliflozin":0.65,
            "atorvastatin":0.95,"amlodipine":0.9,"losartan":0.85,
            "salbutamol":0.9,"montelukast":0.85,"budesonide":0.7,
            "paracetamol":1.0,"ibuprofen":0.95,"azithromycin":0.9,
            "cetirizine":0.9,"folic acid":0.85,"vitamin d":0.8,
            "omeprazole":0.9,"pantoprazole":0.85,"clopidogrel":0.8,
        }
    },
]

WEIGHTS = {
    "coverage":     0.40,
    "availability": 0.20,
    "distance":     0.20,
    "reliability":  0.12,
    "hours":        0.05,
    "category":     0.03,
}

NEURO    = {"levetiracetam","clonazepam","pregabalin","gabapentin","phenytoin","valproate","carbamazepine","lamotrigine","topiramate"}
CARDIAC  = {"atorvastatin","amlodipine","metoprolol","clopidogrel","losartan","ramipril","digoxin","warfarin","furosemide"}
DIABETES = {"metformin","glimepiride","insulin","sitagliptin","empagliflozin","dapagliflozin","glipizide"}
PSYCH    = {"sertraline","escitalopram","alprazolam","quetiapine","risperidone","olanzapine","clonazepam","diazepam"}
RESP     = {"salbutamol","montelukast","budesonide","fluticasone","ipratropium"}
CATEGORY_MAP = {
    "neurology": NEURO, "cardiac": CARDIAC, "cardiology": CARDIAC,
    "diabetes": DIABETES, "psychiatry": PSYCH, "respiratory": RESP,
}


def _haversine(lat1, lng1, lat2, lng2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng/2)**2
    return R * 2 * math.asin(math.sqrt(a))


def _dist_score(km):
    """Exponential decay: ~1.0 at 0km, ~0.5 at 2km, ~0.03 at 10km."""
    return math.exp(-0.35 * km)


def _stock_label(v):
    if v >= 0.7:  return "high"
    if v >= 0.3:  return "medium"
    if v  > 0.0:  return "low"
    return "unavailable"


def _coverage(pharmacy, medicines):
    inv, details, supplied = pharmacy.get("inventory", {}), [], 0
    for med in medicines:
        ml = med.lower()
        stock = inv.get(ml)
        if stock is None:
            stock = next((v for k, v in inv.items() if k in ml or ml in k), 0.0)
        avail = stock > 0.0
        if avail:
            supplied += 1
        details.append({"medicine": med, "stock_level": round(stock, 2),
                         "available": avail, "stock_label": _stock_label(stock)})
    ratio = supplied / len(medicines) if medicines else 0
    return ratio, details


def _category_bonus(pharmacy, medicines):
    meds_lower = {m.lower() for m in medicines}
    for spec, med_set in CATEGORY_MAP.items():
        if spec in pharmacy.get("specialties", []) and meds_lower & med_set:
            return 1.0
    return 0.0


def rank_pharmacies(medicines, user_lat, user_lng, max_results=6, max_km=None):
    results = []
    for ph in PHARMACIES:
        km = _haversine(user_lat, user_lng, ph["lat"], ph["lng"])
        if max_km and km > max_km:
            continue

        cov_ratio, med_details = _coverage(ph, medicines)
        avg_stock = (sum(d["stock_level"] for d in med_details if d["available"]) / len(med_details)
                     if med_details else 0)

        score = (
            WEIGHTS["coverage"]     * cov_ratio +
            WEIGHTS["availability"] * avg_stock +
            WEIGHTS["distance"]     * _dist_score(km) +
            WEIGHTS["reliability"]  * ph["reliability"] +
            WEIGHTS["hours"]        * (1.0 if ph["is_24h"] else 0.0) +
            WEIGHTS["category"]     * _category_bonus(ph, medicines)
        )

        results.append({
            "id": ph["id"], "name": ph["name"],
            "lat": ph["lat"], "lng": ph["lng"],
            "phone": ph.get("phone", ""), "is_24h": ph["is_24h"],
            "distance_km": round(km, 2),
            "score": round(score * 100, 1),
            "coverage_pct": round(cov_ratio * 100, 1),
            "medicines": med_details,
            "factor_scores": {
                "coverage":     round(cov_ratio * 100, 1),
                "availability": round(avg_stock * 100, 1),
                "distance":     round(_dist_score(km) * 100, 1),
                "reliability":  round(ph["reliability"] * 100, 1),
                "hours":        "24h" if ph["is_24h"] else "Limited",
            }
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:max_results]
