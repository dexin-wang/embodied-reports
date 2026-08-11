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
SCHEMA_VERSION = 2
SCAN_STATUSES = {"pending", "found", "no_qualifying_release", "failed"}
DIRECT_STRATEGY = "per-organization-direct-v1"


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
        "strategy": DIRECT_STRATEGY,
        "attempt_count": 0,
        "last_attempt_at": None,
        "last_batch": None,
        "candidate_count": 0,
        "candidate_urls": [],
        "source_urls": [],
        "scanned_urls": [],
        "last_error": None,
    }


def _preserved_scan(old: dict[str, Any], previous_schema: int) -> dict[str, Any]:
    """Do not carry forward the old batched 'completed with zero candidates' state."""
    scan = old.get("official_scan") if isinstance(old.get("official_scan"), dict) else {}
    if previous_schema != SCHEMA_VERSION or scan.get("strategy") != DIRECT_STRATEGY:
        return default_scan()
    return {**default_scan(), **scan}


def ensure_coverage(
    roster_path: Path = ROSTER,
    coverage_path: Path = COVERAGE,
    timestamp: str | None = None,
) -> dict[str, Any]:
    entries = roster_entries(roster_path)
    existing = read_json(coverage_path, {})
    previous_schema = existing.get("schema_version") if isinstance(existing, dict) else None
    previous = {
        item.get("id"): item
        for item in existing.get("organizations", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    } if isinstance(existing, dict) else {}

    organizations = []
    for entry in entries:
        old = previous.get(entry["id"], {})
        organizations.append({
            **entry,
            "official_scan": _preserved_scan(old, previous_schema),
        })

    coverage = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": timestamp or utc_now(),
        "organizations": organizations,
    }
    write_json(coverage_path, coverage)
    return coverage


def _valid_urls(values: list[str]) -> list[str]:
    return sorted({value for value in values if isinstance(value, str) and value.startswith("https://")})[:40]


def record_official_result(
    name: str,
    candidates: list[dict[str, Any]],
    *,
    status: str,
    batch: str,
    source_urls: list[str],
    scanned_urls: list[str],
    error: str | None = None,
    roster_path: Path = ROSTER,
    coverage_path: Path = COVERAGE,
    timestamp: str | None = None,
) -> dict[str, Any]:
    """Record one real website crawl, never a multi-organization model batch."""
    if status not in SCAN_STATUSES - {"pending"}:
        raise ValueError(f"invalid completed scan status: {status}")
    candidate_urls = _valid_urls([
        item.get("url", "") for item in candidates if isinstance(item, dict)
    ])
    source_urls, scanned_urls = _valid_urls(source_urls), _valid_urls(scanned_urls)
    if status == "found" and not candidate_urls:
        raise ValueError("found status requires at least one candidate URL")
    if status == "no_qualifying_release" and not scanned_urls:
        raise ValueError("no_qualifying_release requires an accessible scanned URL")
    if status == "failed" and not error:
        raise ValueError("failed status requires an error message")

    coverage = ensure_coverage(roster_path, coverage_path, timestamp)
    attempted_at = timestamp or utc_now()
    matched = False
    for organization in coverage["organizations"]:
        if organization["name"] != name:
            continue
        matched = True
        scan = organization["official_scan"]
        scan.update({
            "status": status,
            "strategy": DIRECT_STRATEGY,
            "attempt_count": int(scan.get("attempt_count", 0)) + 1,
            "last_attempt_at": attempted_at,
            "last_batch": batch,
            "candidate_count": len(candidate_urls),
            "candidate_urls": candidate_urls[:8],
            "source_urls": source_urls[:12],
            "scanned_urls": scanned_urls[:40],
            "last_error": error,
        })
        break
    if not matched:
        raise ValueError(f"organization is not in canonical roster: {name}")
    coverage["generated_at"] = attempted_at
    write_json(coverage_path, coverage)
    return coverage


def coverage_summary(coverage: dict[str, Any]) -> dict[str, int]:
    organizations = coverage.get("organizations", [])
    scans = [item.get("official_scan", {}) for item in organizations if isinstance(item, dict)]
    return {
        "organizations": len(organizations),
        "pending": sum(scan.get("status") == "pending" for scan in scans),
        "found": sum(scan.get("status") == "found" for scan in scans),
        "no_qualifying_release": sum(scan.get("status") == "no_qualifying_release" for scan in scans),
        "failed": sum(scan.get("status") == "failed" for scan in scans),
        "with_candidates": sum(int(scan.get("candidate_count", 0)) > 0 for scan in scans),
    }


def validate_coverage(
    coverage: dict[str, Any], roster_path: Path = ROSTER,
) -> None:
    if coverage.get("schema_version") != SCHEMA_VERSION:
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
        if scan.get("strategy") != DIRECT_STRATEGY:
            raise ValueError(f"non-direct scan record for {item.get('name')}")
        for key in ("candidate_urls", "source_urls", "scanned_urls"):
            if not isinstance(scan.get(key), list) or any(
                not isinstance(url, str) or not url.startswith("https://")
                for url in scan[key]
            ):
                raise ValueError(f"invalid {key} for {item.get('name')}")
        if scan["status"] == "found" and not scan["candidate_urls"]:
            raise ValueError(f"found without candidates for {item.get('name')}")
        if scan["status"] == "no_qualifying_release" and not scan["scanned_urls"]:
            raise ValueError(f"empty completed crawl for {item.get('name')}")


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
