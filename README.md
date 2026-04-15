# Medsy

Medsy is a Flask app for quickly ranking nearby pharmacies based on a medicine list.

## OpenClaw + ArmorClaw (No Telegram)

This project now includes route-level security checks for the three sensitive flows:

- Manual medicine parsing (`/api/medicines`)
- OCR upload parsing (`/api/ocr`)
- Pharmacy ranking (`/api/rank`)
- OCR extracted-text Gemini content validation (`/api/ocr` post-extraction)

Guard code lives in [engine/armoriq_guard.py](engine/armoriq_guard.py) and is invoked from [app.py](app.py).

### 1. Install and run OpenClaw/ArmorClaw without Telegram

If not installed yet:

```bash
curl -fsSL https://armoriq.ai/install-armorclaw.sh | bash
```

Start gateway locally:

```bash
cd ~/openclaw-armoriq
pnpm dev gateway
```

You can skip Telegram completely. The gateway can run as local security middleware even without chat channels.

### 2. Set Medsy security mode

Configure mode using environment variable:

```bash
export ARMORIQ_MODE=monitor
```

Supported values:

- `off`: bypass guard checks
- `monitor`: log deny decisions but allow requests
- `enforce`: block denied requests (HTTP 4xx/403)

Optional thresholds:

```bash
export ARMORIQ_MAX_TEXT_LENGTH=4000
export ARMORIQ_MAX_MEDICINES=25
export ARMORIQ_MAX_FILE_BYTES=20971520
```

### 2.1 Enable Gemini LLM content guard (manual text)

To block abusive or clearly non-medical text using Gemini (without semantic guard), set:

```bash
export GEMINI_API_KEY=YOUR_GEMINI_KEY
export ARMORIQ_GEMINI_ENABLED=true
export ARMORIQ_GEMINI_MODEL=gemini-2.5-flash
export ARMORIQ_GEMINI_TIMEOUT_SEC=4.0
```

Behavior:

- In `ARMORIQ_MODE=monitor`, Gemini deny signals are logged but request is allowed.
- In `ARMORIQ_MODE=enforce`, Gemini deny signals return a blocked API response with `security_blocked: true`.

### 3. Run Medsy

```bash
python app.py
```

### 4. Validate quickly

Use your existing test file to verify guard behavior:

```bash
cd engine
python3.10 test.py
```

In `monitor` mode all requests pass but include monitor deny reasons internally.
In `enforce` mode unsafe requests are blocked by API routes.

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
