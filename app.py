import os
import re

from flask import Flask, jsonify, render_template, request, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
import requests

from engine.ocr import extract_medicines_from_file, parse_medicines_from_text
from engine.probability import rank_pharmacies


app = Flask(__name__)
CORS(app)

app.config["UPLOAD_FOLDER"] = os.path.join(app.root_path, "static", "uploads")
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024

ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "txt", "docx", "doc"}
DEFAULT_LAT = 28.5733
DEFAULT_LNG = 77.2236
DEFAULT_LOCATION_LABEL = "New Delhi"
MANUAL_SPLIT_RE = re.compile(r"[\n,;]+")

LOCATION_PRESETS = [
    (("lajpat", "lajpat nagar"), (28.5672, 77.2360), "Lajpat Nagar, New Delhi"),
    (("greater kailash", "gk", "gk1", "gk 1"), (28.5494, 77.2341), "Greater Kailash, New Delhi"),
    (("saket",), (28.5245, 77.2066), "Saket, New Delhi"),
    (("nehru place",), (28.5491, 77.2523), "Nehru Place, New Delhi"),
    (("south ex", "south extension"), (28.5732, 77.2208), "South Extension, New Delhi"),
    (("hauz khas",), (28.5494, 77.2001), "Hauz Khas, New Delhi"),
    (("gurugram", "gurgaon"), (28.4595, 77.0266), "Gurugram"),
    (("noida",), (28.5355, 77.3910), "Noida"),
    (("delhi", "new delhi"), (28.6139, 77.2090), "New Delhi"),
]

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def safe_float(value, fallback):
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def render_page(template_name, active_page, **context):
    return render_template(
        template_name,
        active_page=active_page,
        page_class=f"page-{active_page}",
        **context,
    )


def medicines_from_text(text):
    parsed = parse_medicines_from_text(text)
    medicines = []
    seen = set()

    for item in parsed:
        name = item["name"].strip()
        key = name.lower()
        if key in seen:
            continue
        medicines.append(item)
        seen.add(key)

    for chunk in MANUAL_SPLIT_RE.split(text):
        cleaned = re.sub(r"\s+", " ", chunk).strip(" -")
        if not cleaned:
            continue
        normalized = cleaned.lower()
        if normalized in seen:
            continue
        if any(normalized in existing or existing in normalized for existing in seen):
            continue
        medicines.append(
            {
                "name": cleaned,
                "dose": "As entered",
                "frequency": "Manual entry",
                "raw_line": cleaned,
                "confidence": 1.0,
            }
        )
        seen.add(normalized)

    return medicines


def resolve_search_location(address):
    cleaned = (address or "").strip()
    if not cleaned:
        return {
            "lat": DEFAULT_LAT,
            "lng": DEFAULT_LNG,
            "resolved_label": DEFAULT_LOCATION_LABEL,
            "used_default": True,
        }

    lowered = cleaned.lower()
    for keywords, coords, label in LOCATION_PRESETS:
        if any(keyword in lowered for keyword in keywords):
            return {
                "lat": coords[0],
                "lng": coords[1],
                "resolved_label": label,
                "used_default": False,
            }

    return {
        "lat": DEFAULT_LAT,
        "lng": DEFAULT_LNG,
        "resolved_label": f"{DEFAULT_LOCATION_LABEL} sample area",
        "used_default": True,
    }


TILE_DIR  = os.path.join(os.path.dirname(__file__), "static", "tiles")
BLANK_TILE = os.path.join(TILE_DIR, "blank.png")


@app.route("/tiles/<int:z>/<int:x>/<int:y>.png")
def serve_tile(z, x, y):
    tile_path = os.path.join(TILE_DIR, str(z), str(x), f"{y}.png")
    if os.path.isfile(tile_path):
        return send_file(tile_path, mimetype="image/png",
                         max_age=60 * 60 * 24 * 30)
    return send_file(BLANK_TILE, mimetype="image/png", max_age=0)


@app.route("/")
@app.route("/overview")
def overview():
    return render_page("overview.html", "overview")


@app.route("/pharmacy-finder")
def pharmacy_finder():
    known_meds = set()
    from engine.probability import PHARMACIES
    for ph in PHARMACIES:
        known_meds.update(ph.get("inventory", {}).keys())
    return render_page("pharmacy_finder.html", "finder", known_medicines=sorted(list(known_meds)))


@app.route("/medication-lookup")
def medication_lookup():
    return render_page("medication_lookup.html", "lookup")


@app.route("/contact")
def contact():
    return render_page("contact.html", "contact")


@app.route("/dashboard")
def dashboard():
    known_meds = set()
    from engine.probability import PHARMACIES
    for ph in PHARMACIES:
        known_meds.update(ph.get("inventory", {}).keys())
    return render_template("dashboard.html", known_medicines=sorted(list(known_meds)))


@app.route("/login")
def login():
    return render_page(
        "auth.html",
        "login",
        auth_mode="login",
        auth_title="Login to Medsy",
        auth_description="Use a cleaner account page for saved tools and future private medication features.",
        auth_button_label="Login",
    )


@app.route("/register")
def register():
    return render_page(
        "auth.html",
        "register",
        auth_mode="register",
        auth_title="Create your Medsy account",
        auth_description="Set up the account path separately while keeping the Pharmacy Finder public.",
        auth_button_label="Register",
    )


@app.route("/api/medicines", methods=["POST"])
def parse_manual_medicines():
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()

    if not text:
        return jsonify({"error": "Enter at least one medicine name."}), 400

    medicines = medicines_from_text(text)
    if not medicines:
        return jsonify({"error": "No medicines could be parsed from that text."}), 400

    invalid_meds = []
    valid_meds = []

    for med in medicines:
        name_lower = med["name"].lower().strip()
        
        # OpenFDA Real-World Validation
        try:
            import urllib.parse
            encoded_name = urllib.parse.quote(name_lower)
            # Query the US Government OpenFDA database
            response = requests.get(f'https://api.fda.gov/drug/label.json?search={encoded_name}&limit=1', timeout=3)
            if response.status_code == 200:
                valid_meds.append(med)
            else:
                invalid_meds.append(med["name"])
        except Exception as e:
            # If the API fails or times out unexpectedly, we cautiously allow the drug
            # to not block the user entirely during an outage
            valid_meds.append(med)

    if invalid_meds:
        return jsonify({"error": f"Outright medicine not found in global database: {', '.join(invalid_meds)}. Fake results are not allowed."}), 400

    return jsonify({"medicines": valid_meds})


@app.route("/api/ocr", methods=["POST"])
def ocr_pharmacy_finder():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded."}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "Choose a file to upload."}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Unsupported file type."}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)

    try:
        medicines, lines, raw_text = extract_medicines_from_file(filepath)
        return jsonify({"medicines": medicines, "lines": lines, "raw_text": raw_text, "filename": file.filename})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)


@app.route("/api/rank", methods=["POST"])
def rank():
    data = request.get_json(silent=True) or {}
    selected = [str(item).strip() for item in data.get("medicines", []) if str(item).strip()]
    address = (data.get("address") or "").strip()
    manual_lat = safe_float(data.get("lat"), None)
    manual_lng = safe_float(data.get("lng"), None)

    if not selected:
        return jsonify({"error": "No medicines selected."}), 400

    location = resolve_search_location(address)
    user_lat = manual_lat if manual_lat is not None else location["lat"]
    user_lng = manual_lng if manual_lng is not None else location["lng"]

    results = rank_pharmacies(selected, user_lat, user_lng)
    return jsonify(
        {
            "pharmacies": results,
            "location": {
                "query": address,
                "resolved_label": location["resolved_label"],
                "used_default": location["used_default"],
                "lat": user_lat,
                "lng": user_lng,
            },
        }
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)
