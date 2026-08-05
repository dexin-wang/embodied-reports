#!/usr/bin/env python3
"""Use web search to find official embodied-robotics project releases.

This source is intentionally separate from arXiv so projects without a paper or
PDF can enter the candidate queue.  Candidates are not published here; the
strict verifier performs the organization and social-impact checks afterwards.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = ROOT / "automation" / "candidates.json"
API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = os.getenv("OPENAI_VERIFIER_MODEL", "gpt-5.6")
API_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")

TOPICS = [
    "vision-language-action and generalist robot foundation models",
    "humanoid intelligence, whole-body control and locomotion-manipulation",
    "robot world models, video-action models and simulation-to-real systems",
    "dexterous manipulation, hand intelligence, tactile and force-aware robots",
    "robot manipulation data engines, large datasets and benchmarks",
    "robot deployment systems, real-time inference and physical-agent platforms",
]

ITEM = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "title": {"type": "string"}, "url": {"type": "string"}, "date": {"type": "string"},
        "summary": {"type": "string"}, "organization_hint": {"type": "string"},
    },
    "required": ["title", "url", "date", "summary", "organization_hint"],
}
SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {"candidates": {"type": "array", "items": ITEM, "minItems": 0, "maxItems": 20}},
    "required": ["candidates"],
}


def response_text(result: dict) -> str:
    """Read text from both direct OpenAI and proxy-compatible Responses payloads."""
    direct = result.get("output_text")
    if isinstance(direct, str) and direct.strip():
        return direct

    parts = []
    for output in result.get("output", []):
        for content in output.get("content", []):
            if content.get("type") == "output_text" and isinstance(content.get("text"), str):
                parts.append(content["text"])
    if parts:
        return "\n".join(parts)

    summary = json.dumps(
        {key: result.get(key) for key in ("status", "error", "incomplete_details", "output")},
        ensure_ascii=False,
    )[:1600]
    raise RuntimeError(f"Responses API returned no output text: {summary}")


def call(topic: str) -> list[dict]:
    prompt = f"""Search the web for up to 20 influential embodied-robotics project releases since 2025 in this area: {topic}.
Return only candidates that have a dedicated official project page, official company announcement, or official university/research-lab project page. Do not return an arXiv abstract as the URL. A paper/PDF and open source are optional.
The candidate may later be rejected, so do not guess any value. Use a precise YYYY-MM-DD date only when the official page gives one; otherwise return the first day of the known release month. Include a short factual English summary and the named organization shown by the official source.
Exclude generic autonomous-driving, normal computer-vision, and purely academic conference-paper pages with no project release."""
    payload = {
        "model": MODEL, "reasoning": {"effort": "low"},
        "tools": [{"type": "web_search", "search_context_size": "medium"}],
        "input": [{"role": "user", "content": [{"type": "input_text", "text": prompt}]}],
        "text": {"format": {"type": "json_schema", "name": "official_project_leads", "strict": True, "schema": SCHEMA}},
    }
    request = urllib.request.Request(
        f"{API_BASE_URL}/responses", data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            result = json.loads(response.read())
        return json.loads(response_text(result))["candidates"]
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "ignore")[:1200]
        raise RuntimeError(f"sub2api request rejected ({exc.code}): {detail}") from exc


def main() -> None:
    if not API_KEY:
        raise SystemExit("OPENAI_API_KEY is required for official project discovery")
    payload = json.loads(CANDIDATES.read_text()) if CANDIDATES.exists() else {"candidates": []}
    by_url = {item["url"]: item for item in payload.get("candidates", []) if item.get("url")}
    added = 0
    for topic in TOPICS:
        for item in call(topic):
            if item["url"].startswith("https://arxiv.org/") or not item["url"].startswith("https://"):
                continue
            if item["date"] < "2025-01-01":
                continue
            by_url[item["url"]] = {**item, "authors": [], "score": 100, "reasons": ["official web-project discovery"]}
            added += 1
    merged = sorted(by_url.values(), key=lambda item: (item.get("date", ""), item.get("title", "")), reverse=True)
    CANDIDATES.write_text(json.dumps({"generated_at": datetime.now(timezone.utc).isoformat(), "candidates": merged}, ensure_ascii=False, indent=2) + "\n")
    print(f"official_project_leads_added={added} candidates_total={len(merged)}")


if __name__ == "__main__":
    main()
