#!/usr/bin/env python3
"""Keep published report metadata inside the index's controlled vocabulary."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FILES = (ROOT / "data" / "verified.json", ROOT / "data" / "dossiers.json")
ALLOWED_FIELDS = {
    "Vision-language-action", "Large language models", "Humanoid intelligence",
    "Whole-body control", "World models", "Robot manipulation",
    "Dexterous manipulation", "Tactile intelligence", "Data & benchmarks",
    "Robot systems", "Embodied AI",
}


def field_values(values: object) -> list[str]:
    if not isinstance(values, list):
        return []
    return list(dict.fromkeys(value for value in values if isinstance(value, str) and value in ALLOWED_FIELDS))


def list_items(values: object) -> list[str]:
    if isinstance(values, str):
        values = values.splitlines()
    if not isinstance(values, list):
        return []
    return [value.strip().lstrip("-• ") for value in values if isinstance(value, str) and value.strip()]


def clean_record(record: dict) -> None:
    fields = field_values(record.get("fields", record.get("tags", [])))
    record["fields"] = fields
    record["tags"] = fields
    details = record.get("details")
    if isinstance(details, dict):
        details["keyPoints"] = list_items(details.get("keyPoints"))
        details["capabilities"] = list_items(details.get("capabilities"))


def main() -> None:
    for path in FILES:
        if not path.exists():
            continue
        rows = json.loads(path.read_text())
        for row in rows:
            if isinstance(row, dict):
                clean_record(row)
        path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n")
        print(f"cleaned={path.relative_to(ROOT)} rows={len(rows)}")


if __name__ == "__main__":
    main()
