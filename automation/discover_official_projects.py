#!/usr/bin/env python3
"""Use web search to find official embodied-robotics project releases.

This source is intentionally separate from arXiv so projects without a paper or
PDF can enter the candidate queue.  Candidates are not published here; the
strict verifier performs the organization and social-impact checks afterwards.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = ROOT / "automation" / "candidates.json"
COMPANY_ROSTER = ROOT / "automation" / "company_roster.json"
API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = os.getenv("OPENAI_VERIFIER_MODEL", "gpt-5.6")
API_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
RETRY_ATTEMPTS = 3

TOPICS = [
    "generalist vision-language-action, robot foundation-model and embodied-agent software releases",
    "robot manipulation policies, cross-embodiment transfer, action representations and real-robot generalist software",
    "dexterous manipulation software, tactile intelligence, force-aware learning and contact-rich control algorithms",
    "robot world models, video-action models, simulation-to-real software and physical prediction systems",
    "embodied navigation, mobile manipulation, spatial planning and robot-control software",
    "robot data engines, large-scale robot datasets, demonstration collection and embodied benchmarks",
    "real-time VLA inference, action chunking, robot policy serving and physical-agent software stacks",
    "robot-learning releases focused on imitation learning, reinforcement learning, policy post-training and evaluation",
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


def response_json(result: dict) -> dict:
    text = response_text(result).lstrip()
    start = text.find("{")
    if start < 0:
        raise RuntimeError(f"Responses API output did not contain JSON: {text[:800]}")
    value, _ = json.JSONDecoder().raw_decode(text[start:])
    if not isinstance(value, dict):
        raise RuntimeError("Responses API JSON output was not an object")
    return value


def call(topic: str) -> list[dict]:
    prompt = f"""Search the web for up to 20 influential embodied-robotics project releases since 2025 in this area: {topic}.
Return only software candidates that have a dedicated official project page, official company announcement, or official university/research-lab project page. Do not return an arXiv abstract as the URL. A paper/PDF and open source are optional.
Include VLA/foundation models, world/action models, policies, data engines/datasets, simulators, control/planning stacks, benchmarks, or embodied-agent frameworks. Exclude all hardware-only robot/product announcements: robot bodies, humanoids, quadrupeds, hands, sensors, motors, teleoperation devices, and product specifications are not technical reports for this index.
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
    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                result = json.loads(response.read())
            return response_json(result)["candidates"]
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "ignore")[:1200]
            if 400 <= exc.code < 500 and exc.code != 429:
                raise RuntimeError(f"sub2api request rejected ({exc.code}): {detail}") from exc
            error = f"HTTP {exc.code}: {detail}"
        except (urllib.error.URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError) as exc:
            error = f"{type(exc).__name__}: {exc}"
        if attempt < RETRY_ATTEMPTS:
            delay = 4 * attempt
            print(f"warning: discovery request timed out/failed (attempt {attempt}/{RETRY_ATTEMPTS}); retrying in {delay}s: {error}")
            time.sleep(delay)
        else:
            print(f"warning: skipping one discovery topic after {RETRY_ATTEMPTS} attempts: {error}")
    return []


def discovery_topics() -> list[str]:
    """Search the named company roster in small, auditable groups."""
    roster = json.loads(COMPANY_ROSTER.read_text()) if COMPANY_ROSTER.exists() else []
    names = [item["name"] for item in roster if isinstance(item, dict) and item.get("name")]
    groups = [names[index:index + 6] for index in range(0, len(names), 6)]
    company_topics = [
        "Official dedicated pages for embodied-robotics SOFTWARE releases from these organizations: "
        + ", ".join(group)
        for group in groups
    ]
    return [*TOPICS, *company_topics]


def main() -> None:
    if not API_KEY:
        raise SystemExit("OPENAI_API_KEY is required for official project discovery")
    payload = json.loads(CANDIDATES.read_text()) if CANDIDATES.exists() else {"candidates": []}
    by_url = {item["url"]: item for item in payload.get("candidates", []) if item.get("url")}
    added = 0
    for topic in discovery_topics():
        for item in call(topic):
            if item["url"].startswith("https://arxiv.org/") or not item["url"].startswith("https://"):
                continue
            if item["date"] < "2025-01-01":
                continue
            by_url[item["url"]] = {**item, "authors": [], "score": 100, "reasons": ["official web-project discovery"]}
            added += 1
    merged = sorted(by_url.values(), key=lambda item: (item.get("date", ""), item.get("title", "")), reverse=True)
    CANDIDATES.write_text(json.dumps({"generated_at": datetime.now(timezone.utc).isoformat(), "candidates": merged}, ensure_ascii=False, indent=2) + "
")
    print(f"official_project_leads_added={added} candidates_total={len(merged)}")


if __name__ == "__main__":
    main()
