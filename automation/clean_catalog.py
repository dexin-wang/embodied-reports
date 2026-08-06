#!/usr/bin/env python3
"""Keep published report metadata inside the index's controlled vocabulary."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FILES = (ROOT / "data" / "verified.json", ROOT / "data" / "dossiers.json")
ALLOWED_FIELDS = {
    "Vision-language-action", "LLM", "Humanoid intelligence",
    "Whole-body control", "World models", "Robot manipulation",
    "Dexterous manipulation", "Tactile intelligence", "Data & benchmarks",
    "Robot systems", "Embodied AI",
}
FIELD_ALIASES = {"Large language models": "LLM"}
ORGANIZATION_ALIASES = {
    "自变量机器人": "自变量机器人 / X² Robotics",
    "北京人形机器人创新中心": "北京人形机器人创新中心 / Beijing Humanoid Robot Innovation Center",
    "深度求索": "深度求索 / DeepSeek",
    "通义千问": "通义千问 / Qwen",
}
TITLE_ALIASES = {"embodied tien kung 3 0": "embodied tiangong 3 0"}


def field_values(values: object) -> list[str]:
    if not isinstance(values, list):
        return []
    cleaned = [FIELD_ALIASES.get(value, value) for value in values if isinstance(value, str)]
    return list(dict.fromkeys(value for value in cleaned if value in ALLOWED_FIELDS))


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
    organization = record.get("organization")
    if isinstance(organization, str):
        for chinese_name, canonical in ORGANIZATION_ALIASES.items():
            if chinese_name in organization:
                record["organization"] = canonical
                break
    if record.get("title") == "Embodied Tien Kung 3.0":
        record["title"] = "Embodied Tiangong 3.0"


def title_key(title: object) -> str:
    spaced = " ".join(re.findall(r"[a-z]+|\d+", str(title).lower()))
    canonical = TITLE_ALIASES.get(spaced, spaced)
    return "".join(char for char in canonical if char.isalnum())


def completeness(record: dict) -> tuple[int, int, int]:
    details = record.get("details") if isinstance(record.get("details"), dict) else {}
    return (len(details.get("keyPoints", [])), len(details.get("metrics", [])), len(record.get("links", [])))


def deduplicate(rows: list[dict]) -> list[dict]:
    kept: dict[str, dict] = {}
    order: list[str] = []
    for row in rows:
        key = title_key(row.get("title", row.get("id", "")))
        if key not in kept:
            kept[key] = row
            order.append(key)
        elif completeness(row) > completeness(kept[key]):
            kept[key] = row
    return [kept[key] for key in order]


def main() -> None:
    for path in FILES:
        if not path.exists():
            continue
        rows = json.loads(path.read_text())
        for row in rows:
            if isinstance(row, dict):
                clean_record(row)
        rows = deduplicate(rows)
        path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n")
        print(f"cleaned={path.relative_to(ROOT)} rows={len(rows)}")


if __name__ == "__main__":
    main()
