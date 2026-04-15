"""Standalone Gemini-based guard for Medsy manual medicine text."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os

from google import genai


@dataclass
class GeminiDecision:
    allow: bool
    reason: str
    code: str


def _api_key() -> str:
    api_key = (os.getenv("GEMINI_API_KEY", "") or "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured")
    return api_key


def classify_manual_text(text: str, model: str | None = None) -> GeminiDecision:
    model_name = (model or os.getenv("ARMORIQ_GEMINI_MODEL", "gemini-2.5-flash")).strip()

    prompt = (
        "You are validating a pharmacy app manual medicine input.\n"
        "Allow only text that looks like medicine names, dosage/frequency terms, or prescription-like lists.\n"
        "Block profanity, sexual/abusive text, insults, random gibberish, and obviously non-medical phrases.\n"
        "Return STRICT JSON only with keys: allow (boolean), reason (string), code (string).\n"
        "Use code='ok' when allow=true and code='manual_llm_policy_block' when allow=false.\n"
        f"INPUT: {text[:600]}"
    )

    with genai.Client(api_key=_api_key()) as client:
        resp = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config={
                "temperature": 0,
                "top_p": 0.1,
                "max_output_tokens": 120,
                "response_mime_type": "application/json",
            },
        )

    raw = (getattr(resp, "text", "") or "").strip()
    if not raw:
        raise RuntimeError("Gemini returned empty response")

    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise RuntimeError(f"Gemini returned unparsable response: {raw[:200]}")

    data = json.loads(raw[start:end + 1])
    allow = bool(data.get("allow", True))
    reason = str(data.get("reason") or ("allowed" if allow else "blocked by policy")).strip()
    code = str(data.get("code") or ("ok" if allow else "manual_llm_policy_block")).strip()
    return GeminiDecision(allow=allow, reason=reason, code=code)


if __name__ == "__main__":
    samples = [
        "paracetamol 650 mg",
        "crocin 500mg twice daily",
        "sexy bitch",
        "asdjkl; qwepoi",
    ]
    for s in samples:
        try:
            d = classify_manual_text(s)
            print(f"INPUT: {s!r} -> allow={d.allow}, code={d.code}, reason={d.reason}")
        except Exception as exc:
            print(f"INPUT: {s!r} -> ERROR: {exc}")
