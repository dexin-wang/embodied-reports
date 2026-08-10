#!/usr/bin/env python3
"""Maintain an auditable, per-organization official-discovery coverage ledger."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ROSTER = ROOT / "automation" / "company_roster.json"
COVERAGE = ROOT / "automation" / "organization_coverage.json"
SCAN_STATUSES = {"pending", "completed", "failed"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def organization_id(name: str) -> str:
    compact = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", name.lower()).strip("-")
    digest = hashlib.sha1(name.encode("utf-8")).hexdigest()[:8]
    return f"{compact[:48] or 'organization'}-{digest}"


def read_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def roster_entries(roster_path: Path = ROSTER) -> list[dict[str, str]]:
    roster = read_json(roster_path, [])
    if not isinstance(roster, list):
        raise ValueError("company roster must be a JSON array")
    entries: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in roster:
        if not isinstance(item, dict):
            raise ValueError("company roster entries must be objects")
        name, region = item.get("name"), item.get("region")
        if not isinstance(name, str) or not name.strip() or region not in {"China", "International"}:
            raise ValueError(f"invalid roster entry: {item!r}")
        identifier = organization_id(name)
        if identifier in seen:
            raise ValueError(f"duplicate canonical organization: {name}")
        seen.add(identifier)
        entries.append({"id": identifier, "name": name, "region": region})
    return entries


def default_scan() -> dict[str, Any]:
    return {
        "status": "pending",
        "attempt_count": 0,
        "last_attempt_at": None,
        "last_batch": None,
        "candidate_count": 0,
        "candidate_urls": [],
        "last_error": None,
    }


def ensure_coverage(
    roster_path: Path = ROSTER,
    coverage_path: Path = COVERAGE,
    timestamp: str | None = None,
) -> dict[str, Any]:
    entries = roster_entries(roster_path)
    existing = read_json(coverage_path, {})
    previous = {
        item.get("id"): item
        for item in existing.get("organizations", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    } if isinstance(existing, dict) else {}

    organizations = []
    for entry in entries:
        old = previous.get(entry["id"], {})
        scan = old.get("official_scan") if isinstance(old.get("official_scan"), dict) else {}
        organizations.append({
            **entry,
            "official_scan": {**default_scan(), **scan},
        })

    coverage = {
        "schema_version": 1,
        "generated_at": timestamp or utc_now(),
        "organizations": organizations,
    }
    write_json(coverage_path, coverage)
    return coverage


def aliases(name: str) -> list[str]:
    values = [part.strip().lower() for part in name.split("/")]
    values.append(name.lower())
    return [value for value in values if len(value) >= 3]


def candidate_matches(name: str, candidate: dict[str, Any]) -> bool:
    haystack = " ".join(
        str(candidate.get(key, ""))
        for key in ("organization_hint", "title", "summary")
    ).lower()
    return any(alias in haystack for alias in aliases(name))


def record_official_batch(
    names: list[str],
    candidates: list[dict[str, Any]],
    *,
    status: str,
    batch: str,
    error: str | None = None,
    roster_path: Path = ROSTER,
    coverage_path: Path = COVERAGE,
    timestamp: str | None = None,
) -> dict[str, Any]:
    if status not in {"completed", "failed"}:
        raise ValueError(f"invalid scan status: {status}")
    coverage = ensure_coverage(roster_path, coverage_path, timestamp)
    requested = set(names)
    attempted_at = timestamp or utc_now()
    for organization in coverage["organizations"]:
        if organization["name"] not in requested:
            continue
        matched = [item for item in candidates if candidate_matches(organization["name"], item)]
        urls = [item.get("url") for item in matched if isinstance(item.get("url"), str) and item["url"].startswith("https://")]
        scan = organization["official_scan"]
        scan.update({
            "status": status,
            "attempt_count": int(scan.get("attempt_count", 0)) + 1,
            "last_attempt_at": attempted_at,
            "last_batch": batch,
            "candidate_count": len(urls),
            "candidate_urls": sorted(set(urls))[:8],
            "last_error": error,
        })
    coverage["generated_at"] = attempted_at
    write_json(coverage_path, coverage)
    return coverage


def coverage_summary(coverage: dict[str, Any]) -> dict[str, int]:
    organizations = coverage.get("organizations", [])
    scans = [item.get("official_scan", {}) for item in organizations if isinstance(item, dict)]
    return {
        "organizations": len(organizations),
        "pending": sum(scan.get("status") == "pending" for scan in scans),
        "completed": sum(scan.get("status") == "completed" for scan in scans),
        "failed": sum(scan.get("status") == "failed" for scan in scans),
        "with_candidates": sum(int(scan.get("candidate_count", 0)) > 0 for scan in scans),
    }


def validate_coverage(
    coverage: dict[str, Any], roster_path: Path = ROSTER,
) -> None:
    if coverage.get("schema_version") != 1:
        raise ValueError("unsupported coverage schema")
    organizations = coverage.get("organizations")
    if not isinstance(organizations, list):
        raise ValueError("coverage organizations must be an array")
    expected = {entry["id"] for entry in roster_entries(roster_path)}
    actual = {item.get("id") for item in organizations if isinstance(item, dict)}
    if actual != expected or len(actual) != len(organizations):
        raise ValueError("coverage entries must match the canonical roster exactly")
    for item in organizations:
        scan = item.get("official_scan")
        if not isinstance(scan, dict) or scan.get("status") not in SCAN_STATUSES:
            raise ValueError(f"invalid scan record for {item.get('name')}")
        if not isinstance(scan.get("candidate_urls"), list) or any(not isinstance(url, str) or not url.startswith("https://") for url in scan["candidate_urls"]):
            raise ValueError(f"invalid candidate URLs for {item.get('name')}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--initialize", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args()
    if args.initialize:
        coverage = ensure_coverage()
    else:
        coverage = read_json(COVERAGE, {})
    if args.check:
        validate_coverage(coverage)
    if args.summary:
        print(json.dumps(coverage_summary(coverage), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
