#!/usr/bin/env python3
"""Create source-grounded Chinese dossiers for the seed reports.

Only a report PDF or the official project page is used. The output contains
presentation overlays keyed by report id, so source links in the seed catalog
remain unchanged.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "dossiers.json"
API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = os.getenv("OPENAI_VERIFIER_MODEL", "gpt-5.6")
API_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
MAX_CHARS = 28000
ALLOWED_FIELDS = {
    "Vision-language-action", "Large language models", "Humanoid intelligence",
    "Whole-body control", "World models", "Robot manipulation",
    "Dexterous manipulation", "Tactile intelligence", "Data & benchmarks",
    "Robot systems", "Embodied AI",
}

SEEDS = [
    {"id": "being-h08", "title": "Being-H0.8", "url": "https://research.beingbeyond.com/being-h08"},
    {"id": "lingbot-video", "title": "LingBot-Video", "url": "https://arxiv.org/abs/2607.07675"},
    {"id": "wall-oss-05", "title": "WALL-OSS-0.5", "url": "https://arxiv.org/abs/2605.30877"},
    {"id": "pi07", "title": "π0.7", "url": "https://www.pi.website/download/pi07.pdf"},
    {"id": "helix-02", "title": "Helix 02", "url": "https://www.figure.ai/news/helix-02"},
    {"id": "gr00t-n16", "title": "GR00T N1.6", "url": "https://research.nvidia.com/labs/gear/gr00t-n1_6/"},
    {"id": "being-h0", "title": "Being-H0", "url": "https://arxiv.org/abs/2507.15597"},
    {"id": "gr00t-n15", "title": "GR00T N1.5", "url": "https://research.nvidia.com/labs/gear/gr00t-n1_5/"},
    {"id": "smolvla", "title": "SmolVLA", "url": "https://arxiv.org/abs/2506.01844"},
    {"id": "helix", "title": "Helix", "url": "https://www.figure.ai/news/helix"},
]

SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "summary": {"type": "string"},
        "fields": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 4},
        "keyPoints": {"type": "array", "items": {"type": "string"}, "minItems": 4, "maxItems": 7},
        "capabilities": {"type": "array", "items": {"type": "string"}, "minItems": 3, "maxItems": 5},
        "metrics": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "label": {"type": "string"},
                    "value": {"type": "string"},
                    "note": {"type": "string"},
                },
                "required": ["label", "value", "note"],
            },
            "minItems": 1,
            "maxItems": 5,
        },
    },
    "required": ["summary", "fields", "keyPoints", "capabilities", "metrics"],
}


def clean_fields(values: list[object]) -> list[str]:
    fields = [value for value in values if isinstance(value, str) and value in ALLOWED_FIELDS]
    return fields or ["Embodied AI"]


def fetch(url: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "EmbodiedReports/1.0 (+https://github.com/dexin-wang/embodied-reports)"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def to_pdf_url(url: str) -> str:
    match = re.search(r"arxiv\.org/(?:abs|pdf)/([^?#]+)", url)
    return f"https://arxiv.org/pdf/{match.group(1).replace('.pdf', '')}.pdf" if match else url


def source_text(item: dict) -> str:
    body = fetch(to_pdf_url(item["url"]))
    if body.startswith(b"%PDF"):
        document = fitz.open(stream=body, filetype="pdf")
        try:
            text = "\n".join(page.get_text() for page in document[: min(10, len(document))])
        finally:
            document.close()
    else:
        text = re.sub(r"<[^>]+>", " ", body.decode("utf-8", "ignore"))
    return re.sub(r"\s+", " ", text)[:MAX_CHARS]


def output_text(result: dict) -> str:
    direct = result.get("output_text")
    if isinstance(direct, str) and direct.strip():
        return direct
    parts = []
    for output in result.get("output", []):
        for content in output.get("content", []):
            if content.get("type") == "output_text" and isinstance(content.get("text"), str):
                parts.append(content["text"])
    text = "\n".join(parts).lstrip()
    start = text.find("{")
    if start < 0:
        raise RuntimeError(f"No JSON in Responses output: {text[:800]}")
    value, _ = json.JSONDecoder().raw_decode(text[start:])
    return json.dumps(value, ensure_ascii=False)


def dossier(item: dict, text: str) -> dict:
    prompt = f"""You are writing a factual Chinese technical dossier for an embodied robotics index.
Use only the source text below. Do not infer or invent methods, claims, model sizes, benchmark results, or capabilities.
Write one concise Chinese summary, 4-7 concrete technical points, 3-5 implemented functions, and 1-5 exact reported metrics/results. When a source has no quantitative metric, record the precise qualitative result and state that it is qualitative.
Allowed fields: Vision-language-action, Humanoid intelligence, Whole-body control, World models, Robot manipulation, Dexterous manipulation, Tactile intelligence, Data & benchmarks, Robot systems, Embodied AI, Large language models.

TITLE: {item["title"]}
PRIMARY SOURCE:
{text}"""
    payload = {
        "model": MODEL,
        "reasoning": {"effort": "low"},
        "input": [{"role": "user", "content": [{"type": "input_text", "text": prompt}]}],
        "text": {"format": {"type": "json_schema", "name": "embodied_report_dossier", "strict": True, "schema": SCHEMA}},
    }
    request = urllib.request.Request(
        f"{API_BASE_URL}/responses",
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        result = json.loads(response.read())
    return json.loads(output_text(result))


def main() -> None:
    if not API_KEY:
        raise SystemExit("OPENAI_API_KEY is required for dossier generation")
    existing = {item["id"]: item for item in json.loads(OUT.read_text())} if OUT.exists() else {}
    for item in SEEDS:
        if item["id"] in existing:
            continue
        try:
            result = dossier(item, source_text(item))
            existing[item["id"]] = {
                "id": item["id"],
                "summary": result["summary"],
                "fields": clean_fields(result["fields"]),
                "tags": clean_fields(result["fields"]),
                "details": {
                    "keyPoints": result["keyPoints"],
                    "capabilities": result["capabilities"],
                    "metrics": result["metrics"],
                },
                "verification": "Automated",
            }
            OUT.write_text(json.dumps(list(existing.values()), ensure_ascii=False, indent=2) + "\n")
            print(f"dossier={item['id']}")
        except (urllib.error.HTTPError, urllib.error.URLError, OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
            print(f"warning: dossier failed for {item['id']}: {exc}")
    OUT.write_text(json.dumps(list(existing.values()), ensure_ascii=False, indent=2) + "\n")
    print(f"dossiers_total={len(existing)}")


if __name__ == "__main__":
    main()
