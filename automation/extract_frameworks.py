#!/usr/bin/env python3
"""Extract the first method figure from public technical-report PDFs.

This job intentionally stores a rasterized crop from the source PDF rather than
recreating a method diagram.  Figure 1 is normally the overview/method figure
in technical reports.  The generated manifest records its source and page so
the website can attribute every displayed image.
"""

from __future__ import annotations

import json
import re
import sys
import urllib.request
import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError as exc:
    raise SystemExit("PyMuPDF is required. Run: pip install PyMuPDF") from exc


ROOT = Path(__file__).resolve().parents[1]
DISCOVERED = ROOT / "data" / "discovered.json"
STATIC = ROOT / "automation" / "framework_sources.json"
OUT_DIR = ROOT / "public" / "frameworks"
MANIFEST = OUT_DIR / "manifest.json"
MAX_REPORTS = 80


def arxiv_pdf(url: str) -> str:
    match = re.search(r"arxiv\.org/(?:abs|pdf)/([^?#]+)", url)
    return f"https://arxiv.org/pdf/{match.group(1).replace('.pdf', '')}.pdf" if match else url


def fetch_pdf(url: str) -> bytes | None:
    request = urllib.request.Request(url, headers={"User-Agent": "EmbodiedReports/0.2 (+https://github.com/dexin-wang/embodied-reports)"})
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            body = response.read()
            return body if body.startswith(b"%PDF") else None
    except Exception as exc:
        print(f"warning: fetch failed for {url}: {exc}")
        return None


def find_method_figure(document: fitz.Document) -> tuple[int, fitz.Rect, bool]:
    """Locate an early caption that most likely describes a method/framework."""
    best: tuple[int, int, fitz.Rect] | None = None
    method_terms = ("framework", "architecture", "method", "pipeline", "approach", "model overview", "system overview")
    for page_number in range(min(6, len(document))):
        page = document[page_number]
        for block in page.get_text("blocks"):
            text = " ".join(block[4].split())
            match = re.match(r"^(?:Figure|Fig\.)\s*(\d+)(?:\s|[.:—–-])", text, re.I)
            if not match:
                continue
            figure_number = int(match.group(1))
            lower = text.lower()
            score = 1 if figure_number == 1 else 0
            score += sum(8 for term in method_terms if term in lower)
            _, y0, _, y1, *_ = block
            crop = fitz.Rect(18, max(18, y0 - page.rect.height * 0.58), page.rect.width - 18, min(page.rect.height - 18, y1 + 42))
            candidate = (score, page_number, crop)
            if best is None or candidate[0] > best[0]:
                best = candidate
    if best:
        return best[1], best[2], True
    page = document[0]
    return 0, fitz.Rect(18, 18, page.rect.width - 18, page.rect.height - 18), False


def extract(report_id: str, source_url: str, refresh: bool = False) -> dict | None:
    target = OUT_DIR / f"{report_id}.jpg"
    if target.exists() and not refresh:
        return {"id": report_id, "asset": f"frameworks/{report_id}.jpg", "source_url": source_url, "page": None, "caption_detected": False, "cached": True}
    body = fetch_pdf(arxiv_pdf(source_url))
    if body is None:
        return None
    document = fitz.open(stream=body, filetype="pdf")
    try:
        selected_page, selected_crop, found_caption = find_method_figure(document)
        pixmap = document[selected_page].get_pixmap(matrix=fitz.Matrix(1.35, 1.35), clip=selected_crop, alpha=False)
        pixmap.save(target, jpg_quality=86)
        return {
            "id": report_id,
            "asset": f"frameworks/{report_id}.jpg",
            "source_url": source_url,
            "page": selected_page + 1,
            "caption_detected": found_caption,
        }
    except Exception as exc:
        print(f"warning: extraction failed for {report_id}: {exc}")
        return None
    finally:
        document.close()


def sources() -> list[dict]:
    static = json.loads(STATIC.read_text()) if STATIC.exists() else []
    discovered = json.loads(DISCOVERED.read_text()) if DISCOVERED.exists() else []
    dynamic = []
    for report in discovered[:MAX_REPORTS]:
        primary = next((link["url"] for link in report.get("links", []) if link.get("label") == "Report"), None)
        if primary:
            dynamic.append({"id": report["id"], "source_url": primary})
    all_sources = {item["id"]: item for item in [*static, *dynamic]}
    return list(all_sources.values())[:MAX_REPORTS]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cached-only", action="store_true", help="write a manifest for previously extracted figures without fetching PDFs")
    parser.add_argument("--refresh", action="store_true", help="re-fetch and replace previously extracted crops")
    parser.add_argument("--limit", type=int, default=None, help="only process the first N stable source entries")
    args = parser.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    source_items = sources()
    if args.limit is not None:
        source_items = source_items[:args.limit]
    if args.cached_only:
        results = [
            {"id": item["id"], "asset": f"frameworks/{item['id']}.jpg", "source_url": item["source_url"], "page": None, "caption_detected": False, "cached": True}
            for item in source_items
            if (OUT_DIR / f"{item['id']}.jpg").exists()
        ]
    else:
        with ThreadPoolExecutor(max_workers=6) as pool:
            results = list(pool.map(lambda item: extract(item["id"], item["source_url"], args.refresh), source_items))
    entries = [result for result in results if result]
    MANIFEST.write_text(json.dumps({"figures": entries}, ensure_ascii=False, indent=2) + "\n")
    print(f"extracted={len(entries)} sources={len(source_items)}")


if __name__ == "__main__":
    main()
