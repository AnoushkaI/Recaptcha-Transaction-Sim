"""
scripts/verify_gemini.py
─────────────────────────
One-shot script -- run once to confirm the Gemini API key works.

Behaviour:
  [OK]   Prints success + first 60 chars of model response.
  [FAIL] Prints the EXACT error from the API -- never silently retries or hides failures.
  [WARN] If primary model is unavailable, automatically tries the fallback list and reports
         which model worked, so you can update config.py accordingly.

Run from the project root:
  python scripts/verify_gemini.py

Requires .env in the project root with:
  GEMINI_API_KEY=your-key-here
"""

import sys
import os
from pathlib import Path

# Load .env from the project root (one level up from scripts/)
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

api_key = os.getenv("GEMINI_API_KEY", "")
if not api_key:
    print("[FAIL] GEMINI_API_KEY is not set in .env -- add it and retry.")
    sys.exit(1)

print(f"[KEY]  Key loaded (first 6 chars): {api_key[:6]}...")

# ── Model candidates to try, in order of preference ──────────────────────────
# Primary models from config.py (investigator=flash, rule-writer=pro)
# Fallbacks in case a model name is deprecated for a given API key tier
MODELS_TO_TRY = [
    "gemini-2.5-flash",          # current investigator model
    "gemini-2.5-pro",            # current rule-writer model
    "gemini-2.0-flash",          # stable fallback
    "gemini-2.0-flash-lite",     # lightweight fallback
]

from google import genai
from google.genai import types

client = genai.Client(api_key=api_key)

working_model = None
last_error = None

for model_name in MODELS_TO_TRY:
    print(f"[SEND] Testing model: {model_name} ...")
    try:
        response = client.models.generate_content(
            model=model_name,
            contents="Reply with exactly two words: API OK",
            config=types.GenerateContentConfig(
                max_output_tokens=100,
                thinking_config=types.ThinkingConfig(thinking_budget=0),
            ),
        )

        # Extract text safely (thinking models may return None for response.text)
        text = ""
        if response.text is not None:
            text = response.text.strip()
        elif response.candidates:
            for part in response.candidates[0].content.parts:
                if hasattr(part, "text") and part.text:
                    text = part.text.strip()
                    break
        if not text:
            text = "<model responded but text was empty>"

        print(f"[OK]   Model '{model_name}' works. Response: '{text[:60]}'")
        working_model = model_name
        break  # stop at the first working model

    except Exception as exc:
        error_detail = str(exc)
        if "404" in error_detail or "NOT_FOUND" in error_detail or "deprecated" in error_detail.lower():
            print(f"[WARN] Model '{model_name}' is not available for your API key -- trying next...")
            last_error = exc
            continue
        else:
            # Unexpected error -- surface it immediately and stop
            print(f"[FAIL] Unexpected error with model '{model_name}'.")
            print(f"       Error type  : {type(exc).__name__}")
            print(f"       Error detail: {exc}")
            sys.exit(1)

print()  # blank line for readability

if working_model:
    if working_model != "gemini-2.5-flash":
        print(f"[ACTION NEEDED] Primary model 'gemini-2.5-flash' is unavailable.")
        print(f"                Update GEMINI_INVESTIGATOR_MODEL in backend/config.py to: '{working_model}'")
    else:
        print("[READY] Gemini API key is valid. config.py model names are correct. Phase 2 can start.")
else:
    print("[FAIL] None of the candidate models worked for your API key.")
    if last_error:
        print(f"       Last error: {last_error}")
    print("       Check your key is valid and has Gemini API access enabled.")
    sys.exit(1)
