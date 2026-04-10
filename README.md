# Medsy

Medsy is a Flask app for quickly ranking nearby pharmacies based on a medicine list.

This version now includes:

- An overview landing page inspired by your reference layout
- Login and register UI on the same page
- A public `Pharmacy Finder` that works before login
- Two finder inputs: upload a prescription or type medicines manually
- Ranked pharmacy results based on the local probability engine

## Run locally

### 1. Create and activate a virtual environment

```powershell
cd c:\Users\Raghav Gulati\OneDrive\Desktop\medsy
python -m venv venv
.\venv\Scripts\activate
```

### 2. Install Python packages

```powershell
pip install -r requirements.txt
```

### 3. Install OCR dependencies if you want upload scanning

Windows:

- Install Tesseract: https://github.com/UB-Mannheim/tesseract/wiki
- Install Poppler: https://github.com/oschwartz10612/poppler-windows/releases
- Add both to your system `PATH`

If you only want to test the manual text entry flow first, you can still run the app without using OCR uploads.

### 4. Start the app

```powershell
python app.py
```

Then open:

```text
http://127.0.0.1:5000
```

## Current flow

### Overview

- The landing page shows the overview, login/register UI, FAQ, and contact copy.
- Header buttons jump to `Overview`, `Pharmacy Finder`, `Medication Lookup`, and `Contact`.

### Pharmacy Finder

- Public access without login
- Upload a prescription file to extract medicines with OCR
- Or type medicine names manually into the text box
- Select medicines and rank nearby pharmacies

### Login / Register

- Included on the overview page
- Stored locally in browser storage for now
- Ready to replace with real authentication later

## Main files changed

- `app.py`
- `templates/index.html`
- `static/css/style.css`
- `static/js/app.js`
- `engine/probability.py`

## Notes

- `Pharmacy Finder` replaces the previous `Prescription Finder` wording in the UI.
- OCR upload depends on your local Tesseract and Poppler installation.
- Pharmacy data is still local and sample-based inside `engine/probability.py`.
