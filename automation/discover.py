#!/usr/bin/env python3
"""Discover, automatically validate, and publish embodied-AI reports.

The public index has no manual approval queue.  A report is published when a
primary source is reachable through the arXiv feed and it passes the transparent
relevance threshold.  `candidates.json` remains an audit log of every scoring
decision, rather than a list waiting for a human reviewer.
"""

from __future__ import annotations

import hashlib
import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "automation/sources.json").read_text())
OUTPUT = ROOT / "data/discovered.json"
CANDIDATES = ROOT / "automation/candidates.json"
NS = {"atom": "http://www.w3.org/2005/Atom"}


def fetch_arxiv(query: str) -> list[dict]:
    params = urllib.parse.urlencode({
        "search_query": query,
        "start": 0,
        "max_results": CONFIG.get("max_results_per_query", 100),
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    })
    request = urllib.request.Request(
        f"https://export.arxiv.org/api/query?{params}",
        headers={"User-Agent": "EmbodiedReports/0.1 (+https://github.com/)"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        root = ET.fromstring(response.read())

    entries = []
    for entry in root.findall("atom:entry", NS):
        title = " ".join((entry.findtext("atom:title", "", NS)).split())
        summary = " ".join((entry.findtext("atom:summary", "", NS)).split())
        published = entry.findtext("atom:published", "", NS)[:10]
        url = entry.findtext("atom:id", "", NS).replace("http://", "https://")
        authors = [node.findtext("atom:name", "", NS) for node in entry.findall("atom:author", NS)]
        entries.append({"title": title, "summary": summary, "date": published, "url": url, "authors": authors})
    return entries


def score(item: dict) -> tuple[int, list[str]]:
    text = f"{item['title']} {item['summary']}".lower()
    reasons: list[str] = []
    points = 0
    matched = [keyword for keyword in CONFIG["keywords"] if keyword.lower() in text]
    points += min(len(matched) * 8, 32)
    if matched:
        reasons.append("keywords: " + ", ".join(matched[:4]))
    if any(term in item["title"].lower() for term in ("technical report", "foundation model", "vision-language-action")):
        points += 28
        reasons.append("report/model title")
    if any(term in text for term in ("real-world", "real robot", "physical robot", "robot trajectories")):
        points += 18
        reasons.append("physical-robot evidence")
    if any(term in text for term in ("open-source", "open source", "release", "checkpoint")):
        points += 12
        reasons.append("release signal")
    year = int(item["date"][:4]) if item["date"] else 0
    if year >= 2025:
        points += 10
    return min(points, 100), reasons


def slug(title: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:48]
    suffix = hashlib.sha1(title.encode()).hexdigest()[:7]
    return f"{normalized or 'report'}-{suffix}"


def infer_fields(text: str) -> list[str]:
    lower = text.lower()
    fields = []
    rules = [
        ("Vision-language-action", ("vision-language-action", " vision language action", "vla")),
        ("Humanoid intelligence", ("humanoid", "whole-body", "loco-manipulation")),
        ("World models", ("world model", "video model", "video generation")),
        ("Robot manipulation", ("manipulation", "robot control", "robot action")),
        ("Dexterous manipulation", ("dexterous", "hand manipulation", "bimanual")),
        ("Tactile intelligence", ("tactile", "touch", "haptic")),
        ("Data & benchmarks", ("dataset", "benchmark", "data collection")),
        ("Robot systems", ("real-time", "robot factory", "serving system")),
    ]
    for label, needles in rules:
        if any(needle in lower for needle in needles):
            fields.append(label)
    return fields[:4] or ["Embodied AI"]


def infer_organization(item: dict) -> tuple[str, str]:
    # Do not infer an affiliation from baselines named in an abstract.  A model
    # name in the title is a much stronger no-key source for organization tags.
    lower = item["title"].lower()
    for hint, organization in CONFIG.get("organization_hints", {}).items():
        if hint.lower() in lower:
            return organization, "Company"
    return "Research team", "Research Lab"


def evidence_metrics(summary: str) -> list[dict]:
    sentences = re.split(r"(?<=[.!?])\s+", summary)
    numeric = [sentence for sentence in sentences if re.search(r"\d+(?:\.\d+)?\s?(?:%|hz|hours?|tasks?|frames?|trajectories|b|m)\b", sentence, re.I)]
    if numeric:
        return [{"label": "Reported evidence", "value": " ".join(numeric[:2])[:360], "note": "Automatically extracted verbatim from the primary-source abstract."}]
    return [{"label": "Reported evidence", "value": "Open the primary report", "note": "No numerical claim is displayed unless it can be reliably extracted from the source abstract."}]


def to_report(item: dict, points: int) -> dict:
    summary = item["summary"][:240].rsplit(" ", 1)[0] + "…"
    original_summary = item["summary"]
    fields = infer_fields(item["title"] + " " + original_summary)
    organization, organization_kind = infer_organization(item)
    title_lower = item["title"].lower()
    open_source = any(term in original_summary.lower() for term in ("open-source", "open source", "github.com", "code and model checkpoints"))
    return {
        "id": slug(item["title"]),
        "title": item["title"],
        "organization": organization,
        "organizationKind": organization_kind,
        "date": item["date"],
        "year": int(item["date"][:4]),
        "summary": summary,
        "tags": fields,
        "fields": fields,
        "featured": points >= 82,
        "openSource": open_source,
        "verification": "Automated",
        "details": {
            "keyPoints": [summary, f"Automated relevance score: {points}/100. Primary source: arXiv."],
            "capabilities": fields,
            "metrics": evidence_metrics(original_summary),
        },
        "links": [{"label": "Report", "url": item["url"]}],
    }


def main() -> None:
    seen: dict[str, dict] = {}
    for query in CONFIG["arxiv_queries"]:
        try:
            for item in fetch_arxiv(query):
                if item["date"] >= "2025-01-01":
                    seen[item["url"]] = item
        except Exception as exc:
            print(f"warning: query failed: {query}: {exc}")

    evaluated = []
    published = []
    for item in seen.values():
        points, reasons = score(item)
        evaluated.append({**item, "score": points, "reasons": reasons})
        # No human review step: source presence, date, and transparent relevance
        # scoring are the inclusion gate. The audit log retains all candidates.
        if points >= CONFIG.get("auto_publish_score", 42) and item["url"].startswith("https://arxiv.org/"):
            published.append(to_report(item, points))

    evaluated.sort(key=lambda item: (item["score"], item["date"]), reverse=True)
    published.sort(key=lambda item: (item["date"], item["title"]), reverse=True)
    published = published[:CONFIG.get("max_public_reports", 80)]
    CANDIDATES.write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "candidates": evaluated,
    }, ensure_ascii=False, indent=2) + "\n")
    OUTPUT.write_text(json.dumps(published, ensure_ascii=False, indent=2) + "\n")
    print(f"evaluated={len(evaluated)} published={len(published)}")


if __name__ == "__main__":
    main()
