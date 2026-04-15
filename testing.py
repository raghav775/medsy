from google import genai
import os
api_key = os.getenv("GEMINI_API_KEY")  # better than hardcoding
if not api_key:
    raise RuntimeError("Set GEMINI_API_KEY first")

with genai.Client(api_key=api_key) as client:
    for model in client.models.list():
        name = getattr(model, "name", "")
        methods = getattr(model, "supported_actions", None) or getattr(model, "supported_generation_methods", []) or []
        if "generateContent" in methods or "generate_content" in str(methods):
            print(name)