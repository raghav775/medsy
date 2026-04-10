"""
MEDSY — OCR Engine
Supports: PDF (text + scanned), PNG, JPG/JPEG, TXT, DOCX, DOC
All libraries are 100% free/open-source.
"""

import os
import re

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


def _ocr_image(filepath):
    try:
        import pytesseract
        from PIL import Image, ImageFilter, ImageEnhance
    except ImportError:
        raise RuntimeError(
            "Missing pytesseract/Pillow. Run:  pip install pytesseract pillow\n"
            "Then install the Tesseract binary: https://github.com/UB-Mannheim/tesseract/wiki"
        )

    _configure_tesseract()

    try:
        img = Image.open(filepath).convert('L')
        img = ImageEnhance.Contrast(img).enhance(2.0)
        img = img.filter(ImageFilter.SHARPEN)
        return pytesseract.image_to_string(img, config='--psm 6 --oem 3')
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


def extract_lines_from_text(text):
    """Return all non-trivial lines from OCR output for the user to pick from."""
    seen = set()
    lines = []
    for raw in text.split('\n'):
        line = raw.strip()
        # skip blank, too short, or purely numeric/punctuation lines
        if len(line) < 3:
            continue
        if re.match(r'^[\d\s\.\-\:\,\/\(\)]+$', line):
            continue
        key = line.lower()
        if key in seen:
            continue
        seen.add(key)
        lines.append(line)
    return lines


def extract_medicines_from_file(filepath):
    raw_text = extract_text_from_file(filepath)
    medicines = parse_medicines_from_text(raw_text)
    lines = extract_lines_from_text(raw_text)
    return medicines, lines, raw_text
