#!/usr/bin/env python3
"""Find leads for the separate official-source verification stage.

arXiv is deliberately a *candidate* feed only.  It never publishes a card: the
next stage must establish an official project page, a named institution, and
multi-platform public discussion before a candidate reaches the website.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "automation/sources.json").read_text())
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


def main() -> None:
    seen: dict[str, dict] = {}
    if not os.getenv("DISCOVERY_OFFLINE"):
        for query in CONFIG["arxiv_queries"]:
            try:
                for item in fetch_arxiv(query):
                    if item["date"] >= "2025-01-01":
                        seen[item["url"]] = item
            except Exception as exc:
                print(f"warning: query failed: {query}: {exc}")

    # Export.arXiv can be intermittently unavailable to GitHub-hosted runners.
    # Reuse the last successful feed snapshot rather than emitting an empty site.
    if len(seen) < CONFIG.get("minimum_successful_candidates", 10) and CANDIDATES.exists():
        cached = json.loads(CANDIDATES.read_text()).get("candidates", [])
        for item in cached:
            if item.get("date", "") >= "2025-01-01" and item.get("url", "").startswith("https://arxiv.org/"):
                seen[item["url"]] = item
        print(f"using cached feed snapshot: candidates={len(seen)}")

    # A temporary provider outage must never overwrite the candidate audit log.
    if len(seen) < CONFIG.get("minimum_successful_candidates", 10):
        print(f"warning: only {len(seen)} candidates; preserving existing public data")
        return

    # Keep non-arXiv leads found by the official-project discovery agent.  They
    # are candidates too, but must still pass the same strict verifier.
    previous = json.loads(CANDIDATES.read_text()).get("candidates", []) if CANDIDATES.exists() else []
    evaluated_by_url = {
        item.get("url"): item for item in previous
        if item.get("url") and not item.get("url", "").startswith("https://arxiv.org/")
    }
    evaluated = []
    for item in seen.values():
        points, reasons = score(item)
        evaluated_by_url[item["url"]] = {**item, "score": points, "reasons": reasons}

    evaluated = list(evaluated_by_url.values())
    evaluated.sort(key=lambda item: (item["score"], item["date"]), reverse=True)
    CANDIDATES.write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "candidates": evaluated,
    }, ensure_ascii=False, indent=2) + "\n")
    print(f"evaluated={len(evaluated)} candidates ready for official-source verification")


if __name__ == "__main__":
    main()
