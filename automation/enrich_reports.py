#!/usr/bin/env python3
"""Create source-grounded report dossiers with the OpenAI Responses API.

The input is primary-source text extracted from a report PDF (or an official
webpage when no PDF is available).  The model must return structured JSON and
is explicitly forbidden from using facts outside that source text.
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.request
from pathlib import Path

import fitz  # PyMuPDF

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data" / "catalog.json"
ENRICHED = ROOT / "data" / "enriched.json"
MODEL = os.getenv("OPENAI_MODEL", "gpt-5-mini")
API_KEY = os.getenv("OPENAI_API_KEY")
MAX_SOURCE_CHARS = 42_000

SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "organization_en": {"type": "string"},
        "organization_zh": {"type": "string"},
        "organization_kind": {"type": "string", "enum": ["Company", "University", "Research Lab", "Community"]},
        "fields": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 4},
        "summary_zh": {"type": "string"},
        "key_points": {"type": "array", "items": {"type": "string"}, "minItems": 3, "maxItems": 5},
        "capabilities": {"type": "array", "items": {"type": "string"}, "minItems": 2, "maxItems": 4},
        "metrics": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {"label": {"type": "string"}, "value": {"type": "string"}, "note": {"type": "string"}},
                "required": ["label", "value", "note"],
            },
            "minItems": 1,
            "maxItems": 4,
        },
    },
    "required": ["organization_en", "organization_zh", "organization_kind", "fields", "summary_zh", "key_points", "capabilities", "metrics"],
}


def pdf_url(url: str) -> str:
    match = re.search(r"arxiv\.org/(?:abs|pdf)/([^?#]+)", url)
    return f"https://arxiv.org/pdf/{match.group(1).replace('.pdf', '')}.pdf" if match else url


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "EmbodiedReports/0.3 (+https://github.com/dexin-wang/embodied-reports)"})
    with urllib.request.urlopen(request, timeout=45) as response:
        return response.read()


def source_text(report: dict) -> str:
    report_url = next((link["url"] for link in report.get("links", []) if link.get("label") == "Report"), None)
    if not report_url:
        return report["summary"]
    try:
        body = fetch(pdf_url(report_url))
        if body.startswith(b"%PDF"):
            document = fitz.open(stream=body, filetype="pdf")
            try:
                text = "\n".join(page.get_text() for page in document[:min(10, len(document))])
            finally:
                document.close()
        else:
            text = re.sub(r"<[^>]+>", " ", body.decode("utf-8", "ignore"))
        return re.sub(r"\s+", " ", text)[:MAX_SOURCE_CHARS]
    except Exception as exc:
        print(f"warning: source fetch failed for {report['id']}: {exc}")
        return report["summary"]


def call_model(report: dict, text: str) -> dict:
    prompt = f"""You are curating a factual Chinese research index for embodied robotics.
Return only source-grounded information from the PRIMARY SOURCE TEXT below.
Do not use background knowledge; do not invent affiliations, benchmark scores, model size, or implementation details.
For a Chinese company or university, provide both Chinese and English organization names when the source establishes them; otherwise leave organization_zh empty.
Use 3–5 concise Chinese key points, 2–4 concrete capabilities, and 1–4 exact reported metrics/results. If no numerical result is safely established, state that the source does not report a comparable number.
Allowed fields include Vision-language-action, Humanoid intelligence, World models, Robot manipulation, Dexterous manipulation, Tactile intelligence, Data & benchmarks, Robot systems, Embodied AI.

TITLE: {report['title']}
PRIMARY SOURCE TEXT:
{text}
"""
    payload = {
        "model": MODEL,
        "input": [{"role": "user", "content": [{"type": "input_text", "text": prompt}]}],
        "text": {"format": {"type": "json_schema", "name": "report_dossier", "strict": True, "schema": SCHEMA}},
    }
    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        result = json.loads(response.read())
    return json.loads(result["output_text"])


def enriched_record(report: dict, dossier: dict) -> dict:
    output = dict(report)
    english = dossier["organization_en"].strip() or "Research team"
    chinese = dossier["organization_zh"].strip()
    output["organization"] = f"{chinese} / {english}" if chinese else english
    output["organizationKind"] = dossier["organization_kind"]
    output["fields"] = dossier["fields"]
    output["tags"] = dossier["fields"]
    output["summary"] = dossier["summary_zh"]
    output["details"] = {"keyPoints": dossier["key_points"], "capabilities": dossier["capabilities"], "metrics": dossier["metrics"]}
    output["verification"] = "Automated"
    return output


def main() -> None:
    if not API_KEY:
        print("OPENAI_API_KEY is not set; leaving existing enriched records unchanged")
        return
    catalog = json.loads(CATALOG.read_text()) if CATALOG.exists() else []
    existing = json.loads(ENRICHED.read_text()) if ENRICHED.exists() else []
    by_id = {item["id"]: item for item in existing}
    for index, report in enumerate(catalog):
        if report["id"] in by_id:
            continue
        try:
            by_id[report["id"]] = enriched_record(report, call_model(report, source_text(report)))
            print(f"enriched={index + 1}/{len(catalog)} {report['id']}")
            ENRICHED.write_text(json.dumps(list(by_id.values()), ensure_ascii=False, indent=2) + "\n")
        except Exception as exc:
            print(f"warning: enrichment failed for {report['id']}: {exc}")
            time.sleep(2)
    ENRICHED.write_text(json.dumps(list(by_id.values()), ensure_ascii=False, indent=2) + "\n")
    print(f"enriched_total={len(by_id)}")


if __name__ == "__main__":
    main()
