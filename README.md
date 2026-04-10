# Medsy — Smart Pharmacy Navigator
> 100% free stack · No paid APIs · Runs fully locally

---

## Tech stack (all free)
| Layer | Tool |
|---|---|
| Maps & routing | OpenStreetMap + Leaflet.js + OSRM |
| Prescription OCR | Tesseract (pytesseract) + pdfplumber |
| Probability engine | Custom Python (engine/probability.py) |
| Storage | localStorage (browser) |
| Backend | Python Flask |

---

## Setup

### 1. Install system dependencies

**Ubuntu / Debian / WSL:**
```bash
sudo apt update
sudo apt install tesseract-ocr poppler-utils antiword -y
```

**macOS (Homebrew):**
```bash
brew install tesseract poppler
```

**Windows:**
- Tesseract: https://github.com/UB-Mannheim/tesseract/wiki
- Poppler: https://github.com/oschwartz10612/poppler-windows/releases
- Add both to your system PATH.

---

### 2. Create Python virtual environment
```bash
cd medsy
python -m venv venv

# Linux / macOS
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 3. Install Python packages
```bash
pip install -r requirements.txt
```

### 4. Run the app
```bash
python app.py
```

Open your browser at **http://127.0.0.1:5000**

---

## Features

### Dashboard
Health snapshot — records stored, prescriptions scanned, top pharmacies.

### Medical vault
Private local storage for all health records (MRI scans, lab reports, prescriptions).  
Files stored in your browser's localStorage — nothing leaves your device.

### Prescription finder
1. Upload a prescription (PDF, JPG, PNG, DOCX, DOC, or TXT)
2. Medsy uses Tesseract OCR + pdfplumber to extract medicine names
3. Tick the medicines you want
4. Hit **Run probability engine**
5. Pharmacies are ranked 0–100% by a weighted model covering:
   - Medicine coverage (40%)
   - Stock levels (20%)
   - Distance (20%)
   - Pharmacy reliability (12%)
   - 24h hours bonus (5%)
   - Specialty match (3%)
6. Click **Navigate →** on any pharmacy

### Navigate
- Real OpenStreetMap tiles (free, no API key)
- OSRM turn-by-turn routing (free, no API key)
- Clicking Navigate on a pharmacy auto-jumps here
- Full turn-by-turn step list + distance + ETA
- Falls back to straight-line if OSRM is offline

---

## Extending the pharmacy database

Edit `engine/probability.py` → the `PHARMACIES` list.  
Add as many pharmacies as you want, each with:
- Real lat/lng coordinates
- `inventory` dict with medicine names (lowercase) → stock level (0.0–1.0)
- `specialties` list for the specialty match bonus
- `reliability` score (0.0–1.0)

---

## Adding more medicines to OCR

Edit `engine/ocr.py` → the `MEDICINE_DB` dict.  
Format: `"keyword_in_lowercase": "Canonical Display Name"`

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `tesseract not found` | Install Tesseract binary (see step 1) |
| `poppler not found` | Install poppler-utils (for scanned PDFs) |
| `.doc` files not working | Install antiword: `sudo apt install antiword` |
| OSRM routing not working | Check internet connection; falls back to straight-line |
| Port 5000 in use | Run: `python app.py` and change port in app.py |
