"""
MEDSY — OCR Engine
Supports: PDF (text + scanned), PNG, JPG/JPEG, TXT, DOCX, DOC
All libraries are 100% free/open-source.
"""

import os
import re
import difflib

MEDICINE_DB = {
    # Antibiotics
    "amoxicillin":"Amoxicillin","amoxycillin":"Amoxicillin",
    "azithromycin":"Azithromycin","zithromax":"Azithromycin",
    "ciprofloxacin":"Ciprofloxacin","cipro":"Ciprofloxacin",
    "metronidazole":"Metronidazole","flagyl":"Metronidazole",
    "doxycycline":"Doxycycline","cephalexin":"Cephalexin",
    "clarithromycin":"Clarithromycin","levofloxacin":"Levofloxacin",
    "clindamycin":"Clindamycin","trimethoprim":"Trimethoprim",
    "augmentin":"Amoxicillin+Clavulanate (Augmentin)",
    # Pain/Fever
    "paracetamol":"Paracetamol","acetaminophen":"Paracetamol",
    "dolo":"Paracetamol (Dolo)","crocin":"Paracetamol (Crocin)",
    "ibuprofen":"Ibuprofen","brufen":"Ibuprofen (Brufen)",
    "combiflam":"Ibuprofen+Paracetamol (Combiflam)",
    "diclofenac":"Diclofenac","voveran":"Diclofenac (Voveran)",
    "naproxen":"Naproxen","tramadol":"Tramadol",
    "ketorolac":"Ketorolac","meloxicam":"Meloxicam",
    "celecoxib":"Celecoxib","aspirin":"Aspirin","ecosprin":"Aspirin (Ecosprin)",
    # Neurological
    "levetiracetam":"Levetiracetam","keppra":"Levetiracetam (Keppra)",
    "clonazepam":"Clonazepam","rivotril":"Clonazepam (Rivotril)",
    "pregabalin":"Pregabalin","lyrica":"Pregabalin (Lyrica)",
    "gabapentin":"Gabapentin","phenytoin":"Phenytoin",
    "eptoin":"Phenytoin (Eptoin)","valproate":"Valproate",
    "valproic acid":"Valproate","carbamazepine":"Carbamazepine",
    "tegretol":"Carbamazepine (Tegretol)","lamotrigine":"Lamotrigine",
    "topiramate":"Topiramate","oxcarbazepine":"Oxcarbazepine",
    # Cardiovascular
    "atorvastatin":"Atorvastatin","lipitor":"Atorvastatin (Lipitor)",
    "rosuvastatin":"Rosuvastatin","rosuvas":"Rosuvastatin",
    "amlodipine":"Amlodipine","amlong":"Amlodipine (Amlong)",
    "metoprolol":"Metoprolol","betaloc":"Metoprolol (Betaloc)",
    "atenolol":"Atenolol","lisinopril":"Lisinopril",
    "ramipril":"Ramipril","cardace":"Ramipril (Cardace)",
    "losartan":"Losartan","losar":"Losartan",
    "telmisartan":"Telmisartan","telma":"Telmisartan (Telma)",
    "clopidogrel":"Clopidogrel","plavix":"Clopidogrel (Plavix)",
    "clopilet":"Clopidogrel (Clopilet)","warfarin":"Warfarin",
    "digoxin":"Digoxin","lasix":"Furosemide (Lasix)",
    "furosemide":"Furosemide","spironolactone":"Spironolactone",
    "aldactone":"Spironolactone (Aldactone)",
    # Diabetes
    "metformin":"Metformin","glycomet":"Metformin (Glycomet)",
    "glucophage":"Metformin (Glucophage)","glimepiride":"Glimepiride",
    "amaryl":"Glimepiride (Amaryl)","glipizide":"Glipizide",
    "sitagliptin":"Sitagliptin","januvia":"Sitagliptin (Januvia)",
    "empagliflozin":"Empagliflozin","jardiance":"Empagliflozin (Jardiance)",
    "dapagliflozin":"Dapagliflozin","insulin":"Insulin",
    "glargine":"Insulin Glargine","lantus":"Insulin Glargine (Lantus)",
    # GI
    "omeprazole":"Omeprazole","pantoprazole":"Pantoprazole",
    "rabeprazole":"Rabeprazole","razo":"Rabeprazole (Razo)",
    "ranitidine":"Ranitidine","ondansetron":"Ondansetron",
    "zofran":"Ondansetron (Zofran)","domperidone":"Domperidone",
    "domstal":"Domperidone (Domstal)","metoclopramide":"Metoclopramide",
    "perinorm":"Metoclopramide (Perinorm)","loperamide":"Loperamide",
    "imodium":"Loperamide (Imodium)","lactulose":"Lactulose",
    # Respiratory
    "salbutamol":"Salbutamol","ventolin":"Salbutamol (Ventolin)",
    "albuterol":"Salbutamol","montelukast":"Montelukast",
    "montair":"Montelukast (Montair)","fluticasone":"Fluticasone",
    "budesonide":"Budesonide","ipratropium":"Ipratropium",
    "cetirizine":"Cetirizine","zyrtec":"Cetirizine (Zyrtec)",
    "alerid":"Cetirizine (Alerid)","loratadine":"Loratadine",
    "claritin":"Loratadine (Claritin)","fexofenadine":"Fexofenadine",
    "allegra":"Fexofenadine (Allegra)",
    # Vitamins
    "folic acid":"Folic Acid","folate":"Folic Acid",
    "vitamin d3":"Vitamin D3","vitamin d":"Vitamin D3",
    "calcirol":"Vitamin D3 (Calcirol)","vitamin b12":"Vitamin B12",
    "cobalamin":"Vitamin B12","calcium":"Calcium",
    "shelcal":"Calcium+D3 (Shelcal)","iron":"Iron (Ferrous Sulfate)",
    "ferrous sulfate":"Iron (Ferrous Sulfate)","zinc":"Zinc",
    "magnesium":"Magnesium","multivitamin":"Multivitamin",
    # Thyroid
    "levothyroxine":"Levothyroxine","thyronorm":"Levothyroxine (Thyronorm)",
    "eltroxin":"Levothyroxine (Eltroxin)","methimazole":"Methimazole",
    # Psychiatric
    "sertraline":"Sertraline","zoloft":"Sertraline (Zoloft)",
    "escitalopram":"Escitalopram","lexapro":"Escitalopram (Lexapro)",
    "stalopam":"Escitalopram (Stalopam)","fluoxetine":"Fluoxetine",
    "prozac":"Fluoxetine (Prozac)","alprazolam":"Alprazolam",
    "xanax":"Alprazolam (Xanax)","diazepam":"Diazepam",
    "valium":"Diazepam (Valium)","quetiapine":"Quetiapine",
    "seroquel":"Quetiapine (Seroquel)","risperidone":"Risperidone",
    "olanzapine":"Olanzapine","zyprexa":"Olanzapine (Zyprexa)",
    # Steroids
    "prednisolone":"Prednisolone","prednisone":"Prednisone",
    "dexamethasone":"Dexamethasone","decadron":"Dexamethasone",
    "hydrocortisone":"Hydrocortisone","methylprednisolone":"Methylprednisolone",
    "medrol":"Methylprednisolone (Medrol)",
}

# Flat list of all known medicine keywords for fuzzy matching
_ALL_MED_KEYS = sorted(MEDICINE_DB.keys(), key=len, reverse=True)

DOSAGE_RE = re.compile(
    r'(\d+\.?\d*)\s*(mg|mcg|µg|iu|ml|g\b|gm|gram|tablet|tab|cap|capsule|sachet|drops?|puff|unit)',
    re.I
)
FREQUENCY_RE = re.compile(
    r'(\d)\s*[xX×]\s*(daily|day|od|bd|tds|qid|weekly)|'
    r'(once|twice|thrice)\s*(a\s*)?(day|daily|weekly)|'
    r'\b(od|bd|tds|qid|hs|prn|sos)\b',
    re.I
)


def _configure_tesseract():
    """Point Tesseract at the local tessdata folder and the installed binary."""
    import sys
    import pytesseract

    # Use the eng.traineddata bundled in this project (works without admin rights)
    project_tessdata = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tessdata")
    if os.path.isdir(project_tessdata):
        os.environ["TESSDATA_PREFIX"] = project_tessdata

    if sys.platform != "win32":
        return

    # Auto-detect the Tesseract binary on Windows
    if pytesseract.pytesseract.tesseract_cmd in ("tesseract", "tesseract.exe"):
        win_candidates = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            os.path.expanduser(r"~\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"),
        ]
        for path in win_candidates:
            if os.path.exists(path):
                pytesseract.pytesseract.tesseract_cmd = path
                break


def _preprocess_variants(filepath):
    """
    Generate multiple preprocessed versions of the image to maximise
    OCR accuracy on messy handwriting.  Returns a list of PIL Image objects.
    """
    try:
        from PIL import Image, ImageFilter, ImageEnhance, ImageOps
    except ImportError:
        return []

    base = Image.open(filepath).convert('L')
    variants = []

    # 1. High-contrast + sharpen (good for faded ink)
    v1 = ImageEnhance.Contrast(base).enhance(2.5)
    v1 = v1.filter(ImageFilter.SHARPEN)
    variants.append(v1)

    # 2. Otsu-style binarisation via auto-contrast → threshold
    v2 = ImageOps.autocontrast(base, cutoff=5)
    v2 = v2.point(lambda p: 255 if p > 140 else 0)
    variants.append(v2)

    # 3. Aggressive threshold (catches very light handwriting)
    v3 = ImageEnhance.Contrast(base).enhance(3.5)
    v3 = v3.point(lambda p: 255 if p > 100 else 0)
    v3 = v3.filter(ImageFilter.MedianFilter(3))
    variants.append(v3)

    # 4. Inverted (white-on-black Rx pads)
    v4 = ImageOps.invert(ImageOps.autocontrast(base))
    v4 = v4.point(lambda p: 255 if p > 128 else 0)
    variants.append(v4)

    # 5. Scaled-up 2× (helps with small handwriting)
    w, h = base.size
    v5 = base.resize((w * 2, h * 2), Image.LANCZOS)
    v5 = ImageEnhance.Contrast(v5).enhance(2.0)
    v5 = v5.filter(ImageFilter.SHARPEN)
    variants.append(v5)

    return variants


def _ocr_image_easyocr(filepath) -> str | None:
    """
    Use EasyOCR (free, local) to extract text — handles handwriting and
    mixed fonts much better than Tesseract.
    Returns extracted text or None if EasyOCR is not installed.
    """
    try:
        import easyocr
    except ImportError:
        return None
    try:
        reader = easyocr.Reader(["en"], gpu=False, verbose=False)
        # Run on original file
        results = reader.readtext(filepath, detail=0, paragraph=True)
        return "\n".join(results)
    except Exception:
        return None


def _ocr_image_tesseract(filepath) -> str:
    try:
        import pytesseract
        from PIL import Image, ImageFilter, ImageEnhance
    except ImportError:
        raise RuntimeError(
            "Missing pytesseract/Pillow. Run:  pip install pytesseract pillow\n"
            "Then install the Tesseract binary: https://github.com/UB-Mannheim/tesseract/wiki"
        )

    _configure_tesseract()

    # Multiple PSM modes catch different handwriting layouts
    psm_modes = [6, 4, 3, 11]
    all_texts = []

    variants = _preprocess_variants(filepath)
    if not variants:
        # Fallback: just open normally
        variants = [Image.open(filepath).convert('L')]

    for img in variants:
        for psm in psm_modes:
            try:
                text = pytesseract.image_to_string(img, config=f'--psm {psm} --oem 3')
                if text and text.strip():
                    all_texts.append(text)
            except Exception:
                continue

    if not all_texts:
        # Last resort: raw default
        try:
            img = Image.open(filepath).convert('L')
            return pytesseract.image_to_string(img)
        except Exception as exc:
            msg = str(exc).lower()
            if "tesseract" in msg and ("not found" in msg or "not installed" in msg or "cannot find" in msg):
                raise RuntimeError(
                    "Tesseract OCR is not installed or not found on this machine.\n"
                    "Windows: download the installer from "
                    "https://github.com/UB-Mannheim/tesseract/wiki and install it, "
                    "then restart the server.\n"
                    "Linux: sudo apt install tesseract-ocr\n"
                    "macOS: brew install tesseract"
                )
            raise RuntimeError(f"Image OCR failed: {exc}")

    # Merge all texts (union of all lines for maximum medicine coverage)
    return "\n".join(all_texts)


def _ocr_image(filepath) -> str:
    """Try EasyOCR first (handles handwriting), fall back to multi-pass Tesseract.
    Merge results from both for maximum coverage."""
    texts = []
    easy_text = _ocr_image_easyocr(filepath)
    if easy_text and easy_text.strip():
        texts.append(easy_text)
    try:
        tess_text = _ocr_image_tesseract(filepath)
        if tess_text and tess_text.strip():
            texts.append(tess_text)
    except RuntimeError:
        if not texts:
            raise  # Only re-raise if we have nothing at all
    return "\n".join(texts) if texts else ""


def _extract_pdf(filepath):
    text = ""
    try:
        import pdfplumber
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text += t + "\n"
    except ImportError:
        pass

    if not text.strip():
        try:
            from pdf2image import convert_from_path
            import pytesseract
        except ImportError:
            raise RuntimeError(
                "Scanned PDF requires additional packages.\n"
                "Run: pip install pdf2image pytesseract\n"
                "Linux: sudo apt install poppler-utils tesseract-ocr\n"
                "Windows: install Tesseract from https://github.com/UB-Mannheim/tesseract/wiki "
                "and Poppler from https://github.com/oschwartz10612/poppler-windows/releases"
            )
        _configure_tesseract()
        try:
            for img in convert_from_path(filepath, dpi=300):
                text += pytesseract.image_to_string(img, config='--psm 6 --oem 3') + "\n"
        except Exception as exc:
            msg = str(exc).lower()
            if "tesseract" in msg and ("not found" in msg or "not installed" in msg or "cannot find" in msg):
                raise RuntimeError(
                    "Tesseract OCR is not installed or not found.\n"
                    "Windows: https://github.com/UB-Mannheim/tesseract/wiki\n"
                    "Linux: sudo apt install tesseract-ocr"
                )
            raise RuntimeError(f"Scanned PDF OCR failed: {exc}")
    return text


def _extract_docx(filepath):
    try:
        from docx import Document
        return "\n".join(p.text for p in Document(filepath).paragraphs)
    except ImportError:
        raise RuntimeError("pip install python-docx")


def _extract_doc(filepath):
    import subprocess, tempfile
    try:
        r = subprocess.run(['antiword', filepath], capture_output=True, text=True)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout
    except FileNotFoundError:
        pass
    try:
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(
                ['libreoffice', '--headless', '--convert-to', 'txt:Text',
                 '--outdir', tmp, filepath],
                capture_output=True, timeout=30
            )
            out = os.path.join(tmp, os.path.basename(filepath).rsplit('.', 1)[0] + '.txt')
            if os.path.exists(out):
                return open(out, errors='ignore').read()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    raise RuntimeError(
        "Cannot read .doc\n"
        "  sudo apt install antiword   OR install LibreOffice"
    )


def extract_text_from_file(filepath):
    ext = filepath.rsplit('.', 1)[-1].lower()
    return {
        'jpg': _ocr_image, 'jpeg': _ocr_image, 'png': _ocr_image,
        'pdf': _extract_pdf, 'docx': _extract_docx, 'doc': _extract_doc,
        'txt': lambda p: open(p, errors='ignore').read(),
    }.get(ext, lambda p: (_ for _ in ()).throw(ValueError(f"Unsupported: .{ext}")))(filepath)


def parse_medicines_from_text(text):
    found, lines, tl = {}, text.split('\n'), text.lower()
    for keyword, canonical in MEDICINE_DB.items():
        if keyword not in tl:
            continue
        raw_line = next((l.strip() for l in lines if keyword in l.lower()), "")
        dm = DOSAGE_RE.search(raw_line)
        fm = FREQUENCY_RE.search(raw_line)
        dose = f"{dm.group(1)} {dm.group(2)}" if dm else "See prescription"
        freq = fm.group(0).strip() if fm else "As directed"
        conf = 0.95 if len(keyword) > 7 else 0.80
        if canonical not in found:
            found[canonical] = {
                "name": canonical, "dose": dose,
                "frequency": freq, "raw_line": raw_line, "confidence": conf
            }
    return list(found.values())


# Common handwriting OCR misreads: map garbled chars → likely correct ones
_HANDWRITING_SUBS = {
    '0': 'o', '1': 'l', '3': 'e', '5': 's', '8': 'b',
    '|': 'l', '!': 'l', '@': 'a', '$': 's', '(': 'c',
    ')': 'j', '{': 'c', '}': 'j', '[': 'l', ']': 'l',
}


def _clean_ocr_token(token: str) -> str:
    """Apply handwriting-specific character corrections."""
    cleaned = token.lower().strip()
    # Remove stray punctuation that handwriting OCR injects
    cleaned = re.sub(r"[^a-z0-9 ]", "", cleaned)
    # Apply character substitution corrections
    result = ""
    for ch in cleaned:
        result += _HANDWRITING_SUBS.get(ch, ch)
    return result.strip()


def find_medicines_in_ocr(text: str) -> list:
    """
    Aggressively fuzzy-match words from OCR text against the medicine database.
    Designed to handle doctor handwriting where characters are frequently
    misread by OCR engines.
    Returns a list of dicts: [{name, dose, frequency, raw_line, confidence}, ...]
    """
    # First try the existing exact-match parser
    exact = parse_medicines_from_text(text)
    found = {m["name"]: m for m in exact}

    # Extract candidate tokens: words (min 3 chars for handwriting fragments)
    words = re.findall(r'[a-zA-Z]{3,}', text.lower())
    # Also try bigrams and trigrams for multi-word medicines
    bigrams = [words[i] + " " + words[i+1] for i in range(len(words)-1)]
    trigrams = [words[i] + " " + words[i+1] + " " + words[i+2] for i in range(len(words)-2)]
    candidates = words + bigrams + trigrams

    # Also create cleaned versions of each candidate
    cleaned_candidates = []
    for token in candidates:
        cleaned = _clean_ocr_token(token)
        if cleaned and cleaned != token:
            cleaned_candidates.append((cleaned, token))  # (cleaned, original)

    # --- Pass 1: Standard fuzzy match (relaxed cutoff for handwriting) ---
    for token in candidates:
        if any(token in k.lower() or k.lower() in token for k in found):
            continue
        matches = difflib.get_close_matches(token, _ALL_MED_KEYS, n=1, cutoff=0.62)
        if not matches:
            continue
        keyword = matches[0]
        canonical = MEDICINE_DB[keyword]
        if canonical in found:
            continue
        raw_line = next((l.strip() for l in text.split('\n') if keyword in l.lower() or token in l.lower()), token)
        dm = DOSAGE_RE.search(raw_line)
        fm = FREQUENCY_RE.search(raw_line)
        found[canonical] = {
            "name": canonical,
            "dose": f"{dm.group(1)} {dm.group(2)}" if dm else "See prescription",
            "frequency": fm.group(0).strip() if fm else "As directed",
            "raw_line": raw_line,
            "confidence": 0.75,
        }

    # --- Pass 2: Cleaned (character-corrected) fuzzy match ---
    for cleaned, original in cleaned_candidates:
        if any(cleaned in k.lower() or k.lower() in cleaned for k in found):
            continue
        matches = difflib.get_close_matches(cleaned, _ALL_MED_KEYS, n=1, cutoff=0.62)
        if not matches:
            continue
        keyword = matches[0]
        canonical = MEDICINE_DB[keyword]
        if canonical in found:
            continue
        raw_line = next((l.strip() for l in text.split('\n') if original in l.lower()), original)
        dm = DOSAGE_RE.search(raw_line)
        fm = FREQUENCY_RE.search(raw_line)
        found[canonical] = {
            "name": canonical,
            "dose": f"{dm.group(1)} {dm.group(2)}" if dm else "See prescription",
            "frequency": fm.group(0).strip() if fm else "As directed",
            "raw_line": raw_line,
            "confidence": 0.65,
        }

    # --- Pass 3: Substring containment (catches partial reads like "metacet" → "paracetamol") ---
    text_lower = text.lower()
    for keyword, canonical in MEDICINE_DB.items():
        if canonical in found:
            continue
        # Check if the medicine keyword is embedded inside any OCR word
        if len(keyword) >= 5:
            for word in words:
                if len(word) >= 5 and (keyword[:5] in word or word[:5] in keyword):
                    # Verify with a loose ratio check
                    ratio = difflib.SequenceMatcher(None, word, keyword).ratio()
                    if ratio >= 0.55:
                        raw_line = next((l.strip() for l in text.split('\n') if word in l.lower()), word)
                        dm = DOSAGE_RE.search(raw_line)
                        fm = FREQUENCY_RE.search(raw_line)
                        found[canonical] = {
                            "name": canonical,
                            "dose": f"{dm.group(1)} {dm.group(2)}" if dm else "See prescription",
                            "frequency": fm.group(0).strip() if fm else "As directed",
                            "raw_line": raw_line,
                            "confidence": 0.60,
                        }
                        break

    return list(found.values())


def extract_medicines_from_file(filepath):
    raw_text = extract_text_from_file(filepath)
    medicines = find_medicines_in_ocr(raw_text)
    return medicines, raw_text
