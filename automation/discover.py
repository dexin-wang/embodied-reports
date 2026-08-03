#!/usr/bin/env python3
"""Discover high-confidence embodied-AI technical-report candidates.

This conservative first stage only publishes arXiv entries that pass transparent
rules. Ambiguous candidates are retained in automation/candidates.json for later
re-evaluation instead of being shown as verified reports.
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
        "max_results": 20,
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


def to_report(item: dict, points: int) -> dict:
    summary = item["summary"][:240].rsplit(" ", 1)[0] + "…"
    tags = ["VLA"] if "vision-language-action" in (item["title"] + item["summary"]).lower() else ["Embodied AI"]
    if "humanoid" in (item["title"] + item["summary"]).lower():
        tags.append("Humanoid")
    if "world model" in (item["title"] + item["summary"]).lower():
        tags.append("World Models")
    return {
        "id": slug(item["title"]),
        "title": item["title"],
        "organization": "Author team",
        "date": item["date"],
        "year": int(item["date"][:4]),
        "summary": summary,
        "tags": tags,
        "featured": points >= 90,
        "openSource": False,
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
        # Pure keyword matches are not enough to establish influence. Without
        # organization/attention enrichment, only explicitly named technical
        # reports with a very high evidence score may publish automatically.
        if points >= 82 and "technical report" in item["title"].lower():
            published.append(to_report(item, points))

    evaluated.sort(key=lambda item: (item["score"], item["date"]), reverse=True)
    published.sort(key=lambda item: item["date"], reverse=True)
    CANDIDATES.write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "candidates": evaluated,
    }, ensure_ascii=False, indent=2) + "\n")
    OUTPUT.write_text(json.dumps(published, ensure_ascii=False, indent=2) + "\n")
    print(f"evaluated={len(evaluated)} published={len(published)}")


if __name__ == "__main__":
    main()
