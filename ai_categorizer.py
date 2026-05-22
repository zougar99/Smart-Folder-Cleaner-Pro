# -*- coding: utf-8 -*-
"""
AI-powered categorization: suggest folder names from file names (e.g. "invoices", "vacation").
Uses DeepSeek API (OpenAI-compatible).
"""
import json
import re
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL

def _normalize(name: str) -> str:
    # One word, lowercase, safe for folder name
    name = re.sub(r"[^\w\s-]", "", name.lower())
    return re.sub(r"[\s_]+", "_", name).strip("_") or "other"

def categorize_with_ai(file_names: list[str], max_names: int = 30) -> dict[str, str]:
    """
    For each file name (or batch), get a short category label.
    Returns dict: file_name -> folder_name (e.g. "facture_2024.pdf" -> "invoices")
    """
    if not DEEPSEEK_API_KEY or not file_names:
        return {}
    names_sample = file_names[:max_names]
    try:
        from openai import OpenAI
        client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
        prompt = """You are a file organizer. Given a list of file names, suggest ONE short folder name per file (in English or French).
Reply ONLY with a JSON object: keys = exact file names, values = suggested folder name (one or two words, no spaces use underscore).
Example: {"report.pdf": "reports", "vacation_2024.jpg": "vacation_photos"}
File names (one per line):
"""
        prompt += "\n".join(names_sample)
        resp = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        text = (resp.choices[0].message.content or "").strip()
        # Extract JSON from response (handle markdown code blocks)
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        data = json.loads(text)
        return {k: _normalize(str(v)) for k, v in data.items() if isinstance(v, str)}
    except Exception:
        return {}

def suggest_category_for_name(file_name: str) -> str:
    """Single file: get one AI-suggested category."""
    result = categorize_with_ai([file_name], max_names=1)
    return result.get(file_name, "other")
