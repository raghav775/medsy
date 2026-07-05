"""
Medsy guard layer for OpenClaw + ArmorClaw style route verification.

This module is intentionally framework-agnostic so Flask routes can call
guard_route_action() before sensitive operations.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any

try:
    from engine.gemini_guard import classify_manual_text
except Exception:
    classify_manual_text = None


@dataclass
class GuardResult:
    allowed: bool
    reason: str
    error_code: str | None = None
    status_code: int = 200


_ALLOWED_OCR_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "txt", "docx", "doc"}
_MAX_TEXT_LENGTH = int(os.getenv("ARMORIQ_MAX_TEXT_LENGTH", "4000"))
_MAX_MEDICINES = int(os.getenv("ARMORIQ_MAX_MEDICINES", "25"))
_MAX_FILE_BYTES = int(os.getenv("ARMORIQ_MAX_FILE_BYTES", str(20 * 1024 * 1024)))
_GEMINI_ENABLED = (os.getenv("ARMORIQ_GEMINI_ENABLED", "true") or "true").strip().lower() in {"1", "true", "yes", "on"}
_LOCAL_UNSAFE_TERM_BLOCKING = (os.getenv("ARMORIQ_LOCAL_UNSAFE_TERM_BLOCKING", "true") or "true").strip().lower() in {"1", "true", "yes", "on"}
_LOCAL_UNSAFE_PATTERNS = {
    "rat poison": "Searches for poison or harmful substances are not allowed in Medsy safe search.",
    "poison": "Searches for poison or harmful substances are not allowed in Medsy safe search.",
    "drug": "Searches for illegal or unsafe drugs are not allowed in Medsy safe search.",
    "drugs": "Searches for illegal or unsafe drugs are not allowed in Medsy safe search.",
    "cocaine": "Searches for illegal or unsafe drugs are not allowed in Medsy safe search.",
    "heroin": "Searches for illegal or unsafe drugs are not allowed in Medsy safe search.",
    "meth": "Searches for illegal or unsafe drugs are not allowed in Medsy safe search.",
    "methamphetamine": "Searches for illegal or unsafe drugs are not allowed in Medsy safe search.",
    "weed": "Searches for illegal or unsafe drugs are not allowed in Medsy safe search.",
    "marijuana": "Searches for illegal or unsafe drugs are not allowed in Medsy safe search.",
    "cannabis": "Searches for illegal or unsafe drugs are not allowed in Medsy safe search.",
    "lsd": "Searches for illegal or unsafe drugs are not allowed in Medsy safe search.",
    "mdma": "Searches for illegal or unsafe drugs are not allowed in Medsy safe search.",
    "ecstasy": "Searches for illegal or unsafe drugs are not allowed in Medsy safe search.",
    "opioid": "Searches for unsafe or non-prescribed drug terms are not allowed in Medsy safe search.",
    "fentanyl": "Searches for unsafe or non-prescribed drug terms are not allowed in Medsy safe search.",
    "cyanide": "Searches for poison or harmful substances are not allowed in Medsy safe search.",
    "bleach": "Searches for poison or harmful substances are not allowed in Medsy safe search.",
    "acid": "Searches for dangerous chemicals are not allowed in Medsy safe search.",
    "drain cleaner": "Searches for dangerous chemicals are not allowed in Medsy safe search.",
    "pesticide": "Searches for toxic household or chemical agents are not allowed in Medsy safe search.",
    "insecticide": "Searches for toxic household or chemical agents are not allowed in Medsy safe search.",
    "weed killer": "Searches for toxic household or chemical agents are not allowed in Medsy safe search.",
    "kill someone": "Unsafe violent or harmful requests are blocked by Medsy safe search.",
    "how to kill": "Unsafe violent or harmful requests are blocked by Medsy safe search.",
}
_COMMON_MEDICINE_HINTS = {
    "mg", "ml", "tablet", "tablets", "capsule", "capsules", "syrup", "injection",
    "drops", "cream", "gel", "ointment", "dose", "daily", "twice", "thrice",
    "paracetamol", "acetaminophen", "ibuprofen", "aspirin", "amoxicillin",
    "azithromycin", "cetirizine", "metformin", "insulin", "omeprazole",
    "pantoprazole", "amlodipine", "atorvastatin", "crocin", "dolo", "combiflam",
}


def _mode() -> str:
    return (os.getenv("ARMORIQ_MODE", "monitor") or "monitor").strip().lower()


def _finalize(allowed: bool, reason: str, error_code: str | None = None, deny_status: int = 403) -> GuardResult:
    mode = _mode()

    if mode == "off":
        return GuardResult(True, "guard bypassed (ARMORIQ_MODE=off)", None, 200)

    if allowed:
        return GuardResult(True, reason, None, 200)

    # Always enforce the local fallback for clearly unsafe manual searches so
    # Medsy still demonstrates safe search even if external guard services are
    # unavailable or running in monitor mode.
    if error_code in {"manual_local_unsafe_term_block", "manual_gibberish_input"}:
        return GuardResult(False, reason, error_code, deny_status)

    if mode == "monitor":
        # Monitor mode records deny intent but does not block requests.
        return GuardResult(True, f"monitor-only deny: {reason}", error_code, 200)

    # Enforce mode blocks.
    return GuardResult(False, reason, error_code, deny_status)


def _check_local_manual_safety(text: str) -> tuple[bool, str, str | None]:
    normalized = " ".join(str(text or "").lower().split())

    if not normalized or not _LOCAL_UNSAFE_TERM_BLOCKING:
        return True, "local unsafe-term fallback disabled or empty input", None

    for pattern, reason in _LOCAL_UNSAFE_PATTERNS.items():
        if pattern in normalized:
            return False, reason, "manual_local_unsafe_term_block"

    return True, "local unsafe-term fallback passed", None


def _looks_like_gibberish(text: str) -> bool:
    normalized = " ".join(str(text or "").strip().lower().split())
    if not normalized:
        return False

    tokens = [token for token in normalized.replace("/", " ").replace("-", " ").split() if token]
    if not tokens:
        return False

    if any(token in _COMMON_MEDICINE_HINTS for token in tokens):
        return False

    alpha_only = ["".join(ch for ch in token if ch.isalpha()) for token in tokens]
    alpha_only = [token for token in alpha_only if token]
    if not alpha_only:
        return True

    long_alpha_tokens = [token for token in alpha_only if len(token) >= 5]
    consonant_heavy = 0
    repeated_runs = 0

    for token in alpha_only:
        vowels = sum(1 for ch in token if ch in "aeiou")
        if len(token) >= 6 and vowels <= 1:
            consonant_heavy += 1
        if any(ch * 3 in token for ch in set(token)):
            repeated_runs += 1

    if len(alpha_only) == 1 and len(alpha_only[0]) >= 7 and alpha_only[0] not in _COMMON_MEDICINE_HINTS:
        vowels = sum(1 for ch in alpha_only[0] if ch in "aeiou")
        if vowels <= 1:
            return True

    if long_alpha_tokens and consonant_heavy == len(long_alpha_tokens):
        return True

    if repeated_runs >= max(1, len(alpha_only) // 2):
        return True

    if len(alpha_only) <= 3 and all(len(token) >= 4 for token in alpha_only):
        suspicious = 0
        for token in alpha_only:
            unique_ratio = len(set(token)) / len(token)
            vowels = sum(1 for ch in token if ch in "aeiou")
            if unique_ratio > 0.8 and vowels <= 1:
                suspicious += 1
        if suspicious == len(alpha_only):
            return True

    return False


def _validate_manual(payload: dict[str, Any]) -> tuple[bool, str, str | None, int]:
    has_text = bool(payload.get("has_text"))
    text_length = int(payload.get("text_length") or 0)
    text = str(payload.get("text") or "")

    if not has_text or text_length <= 0:
        return False, "manual request has empty text", "manual_empty", 400
    if text_length > _MAX_TEXT_LENGTH:
        return False, f"manual text too large ({text_length}>{_MAX_TEXT_LENGTH})", "manual_too_large", 413

    local_allowed, local_reason, local_code = _check_local_manual_safety(text)
    if not local_allowed:
        return False, local_reason, local_code, 400

    if _looks_like_gibberish(text):
        return False, "The written text looks like gibberish and does not appear to be a medicine.", "manual_gibberish_input", 400

    llm_allowed, llm_reason, llm_code = _gemini_manual_content_check(text)
    if not llm_allowed:
        return False, llm_reason, llm_code, 400

    return True, "manual request validated", None, 200


def _gemini_manual_content_check(text: str) -> tuple[bool, str, str | None]:
    if not _GEMINI_ENABLED:
        return True, "gemini guard disabled", None

    if classify_manual_text is None:
        if _mode() == "enforce":
            return False, "gemini guard is unavailable in enforce mode", "manual_llm_unavailable"
        return True, "gemini guard unavailable", None

    if not (os.getenv("GEMINI_API_KEY", "") or "").strip():
        if _mode() == "enforce":
            return False, "gemini api key not configured for enforce mode", "manual_llm_not_configured"
        return True, "gemini api key not configured", None

    try:
        decision = classify_manual_text(text)
        if decision.allow:
            return True, "gemini content check passed", None
        return False, decision.reason, decision.code or "manual_llm_policy_block"
    except Exception as exc:
        if _mode() == "enforce":
            return False, f"gemini check exception in enforce mode: {exc}", "manual_llm_exception"
        return True, f"gemini check exception: {exc}", None


def _validate_ocr(payload: dict[str, Any]) -> tuple[bool, str, str | None, int]:
    filename = str(payload.get("filename") or "").strip()
    content_length = int(payload.get("content_length") or 0)

    if not filename:
        return False, "missing upload filename", "ocr_missing_filename", 400

    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in _ALLOWED_OCR_EXTENSIONS:
        return False, f"unsupported upload extension: {ext or 'none'}", "ocr_bad_extension", 400

    if content_length <= 0:
        return False, "upload content length missing or zero", "ocr_missing_size", 400

    if content_length > _MAX_FILE_BYTES:
        return False, "upload file exceeds configured guard limit", "ocr_too_large", 413

    return True, "ocr upload request validated", None, 200


def _validate_ocr_extracted_text(payload: dict[str, Any]) -> tuple[bool, str, str | None, int]:
    raw_text = str(payload.get("raw_text") or "")
    text_length = int(payload.get("text_length") or len(raw_text))

    if text_length <= 0:
        return True, "ocr text empty", None, 200

    llm_allowed, llm_reason, llm_code = _gemini_manual_content_check(raw_text)
    if not llm_allowed:
        code = llm_code or "ocr_llm_policy_block"
        return False, f"ocr extracted text blocked: {llm_reason}", code, 400

    return True, "ocr extracted text validated", None, 200


def _validate_rank(payload: dict[str, Any]) -> tuple[bool, str, str | None, int]:
    medicines_count = int(payload.get("medicines_count") or 0)
    address_length = int(payload.get("address_length") or 0)

    if medicines_count <= 0:
        return False, "no medicines provided for ranking", "rank_no_medicines", 400

    if medicines_count > _MAX_MEDICINES:
        return False, f"too many medicines requested ({medicines_count}>{_MAX_MEDICINES})", "rank_too_many_medicines", 400

    if address_length > 512:
        return False, "address too long", "rank_address_too_long", 400

    return True, "rank request validated", None, 200


def _validate_manual_invalid_meds(payload: dict[str, Any]) -> tuple[bool, str, str | None, int]:
    invalid_count = int(payload.get("invalid_count") or 0)
    invalid_preview = str(payload.get("invalid_preview") or "").strip()

    if invalid_count > 0:
        reason = "manual input contains medicines not found in validated database"
        if invalid_preview:
            reason = f"{reason}: {invalid_preview}"
        return False, reason, "manual_invalid_medicine", 400

    return True, "manual medicines validated against database", None, 200


def guard_route_action(action_name: str, payload: dict[str, Any] | None = None) -> GuardResult:
    payload = payload or {}

    if action_name == "validate_manual_medicines_request":
        allowed, reason, error_code, status = _validate_manual(payload)
        return _finalize(allowed, reason, error_code, status)

    if action_name == "validate_ocr_upload_request":
        allowed, reason, error_code, status = _validate_ocr(payload)
        return _finalize(allowed, reason, error_code, status)

    if action_name == "validate_rank_request":
        allowed, reason, error_code, status = _validate_rank(payload)
        return _finalize(allowed, reason, error_code, status)

    if action_name == "validate_ocr_extracted_text":
        allowed, reason, error_code, status = _validate_ocr_extracted_text(payload)
        return _finalize(allowed, reason, error_code, status)

    if action_name == "validate_manual_invalid_medicines":
        allowed, reason, error_code, status = _validate_manual_invalid_meds(payload)
        return _finalize(allowed, reason, error_code, status)

    return _finalize(False, f"unknown guard action: {action_name}", "unknown_action", 400)


def reset_armoriq_client_cache() -> None:
    """Compatibility shim for tests; no-op for this local guard module."""
    return None
