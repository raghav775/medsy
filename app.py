import os
import re

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
from werkzeug.utils import secure_filename

from engine.ocr import extract_medicines_from_file, parse_medicines_from_text
from engine.probability import rank_pharmacies


app = Flask(__name__)
CORS(app)

app.config["UPLOAD_FOLDER"] = os.path.join(app.root_path, "static", "uploads")
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024

ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "txt", "docx", "doc"}
DEFAULT_LAT = 28.5733
DEFAULT_LNG = 77.2236
MANUAL_SPLIT_RE = re.compile(r"[\n,;]+")

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def safe_float(value, fallback):
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


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


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/medicines", methods=["POST"])
def parse_manual_medicines():
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()

    if not text:
        return jsonify({"error": "Enter at least one medicine name."}), 400

    medicines = medicines_from_text(text)
    if not medicines:
        return jsonify({"error": "No medicines could be parsed from that text."}), 400

    return jsonify({"medicines": medicines})


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
        medicines = extract_medicines_from_file(filepath)
        return jsonify({"medicines": medicines, "filename": file.filename})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)


@app.route("/api/rank", methods=["POST"])
def rank():
    data = request.get_json(silent=True) or {}
    selected = [str(item).strip() for item in data.get("medicines", []) if str(item).strip()]
    user_lat = safe_float(data.get("lat"), DEFAULT_LAT)
    user_lng = safe_float(data.get("lng"), DEFAULT_LNG)

    if not selected:
        return jsonify({"error": "No medicines selected."}), 400

    results = rank_pharmacies(selected, user_lat, user_lng)
    return jsonify({"pharmacies": results})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
