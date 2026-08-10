#!/usr/bin/env python3
"""Validate only deployable catalog artifacts.

The validator deliberately treats image decoding as a release gate. A manifest
entry is publishable only when the referenced local raster is readable and has a
non-trivial size; this prevents browsers from rendering broken-image icons.
"""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "data" / "verified.json"
MANIFEST = ROOT / "public" / "frameworks" / "manifest.json"


def main() -> None:
    reports = json.loads(REPORTS.read_text())
    ids = [item["id"] for item in reports]
    assert len(ids) == len(set(ids)), "duplicate report ids"

    figures = json.loads(MANIFEST.read_text()).get("figures", [])
    figure_ids = [item.get("id") for item in figures]
    assert len(figure_ids) == len(set(figure_ids)), "duplicate framework figure ids"

    for item in figures:
        asset = item.get("asset", "")
        path = ROOT / "public" / asset
        assert asset and path.is_file(), f"missing image asset: {asset}"
        try:
            with Image.open(path) as image:
                image.verify()
            with Image.open(path) as image:
                width, height = image.size
        except Exception as exc:
            raise AssertionError(f"unreadable image asset: {asset}: {exc}") from exc
        assert width >= 240 and height >= 140, f"image asset is too small: {asset} ({width}x{height})"
    print(f"validated reports={len(reports)} figures={len(figures)}")


if __name__ == "__main__":
    main()
