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
import urllib.request
import argparse
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from io import BytesIO
from urllib.parse import urljoin
from pathlib import Path

from PIL import Image

try:
    import fitz  # PyMuPDF
except ImportError as exc:
    raise SystemExit("PyMuPDF is required. Run: pip install PyMuPDF") from exc


ROOT = Path(__file__).resolve().parents[1]
VERIFIED = ROOT / "data" / "verified.json"
STATIC = ROOT / "automation" / "framework_sources.json"
OUT_DIR = ROOT / "public" / "frameworks"
MANIFEST = OUT_DIR / "manifest.json"
MAX_REPORTS = 80


class ProjectImageParser(HTMLParser):
    """Collect explicitly described method figures from an official page.

    Project sites frequently publish WebP/AVIF assets and put the useful signal
    in an image ``alt`` attribute rather than in its file name.  Method diagrams
    receive the highest score; where none exists, an early large image labelled
    as a dataset, benchmark, result, or model visual is retained as an honest
    project-page overview rather than leaving the card blank.
    """

    METHOD_TERMS = ("framework", "architecture", "method", "pipeline", "overview", "system", "diagram")
    RELATED_TERMS = ("model", "dataset", "data", "benchmark", "result", "evaluation", "teaser", "hero", "figure")
    EXCLUDED_TERMS = ("logo", "icon", "avatar", "profile", "author", "favicon", "github-mark")

    def __init__(self) -> None:
        super().__init__()
        self.candidates: list[tuple[int, int, str]] = []
        self.order = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "img":
            return
        self.order += 1
        values = {key.lower(): value or "" for key, value in attrs}
        source = values.get("src") or values.get("data-src") or values.get("data-original")
        if not source and values.get("srcset"):
            source = values["srcset"].split(",", 1)[0].strip().split(" ", 1)[0]
        if not source:
            return
        text = " ".join(values.get(key, "") for key in ("alt", "title", "class", "id", "src", "data-src", "srcset")).lower()
        if source.startswith("data:") or any(term in text for term in self.EXCLUDED_TERMS):
            return
        method_score = sum(1 for term in self.METHOD_TERMS if term in text)
        related_score = sum(1 for term in self.RELATED_TERMS if term in text)
        # Keep non-decorative images as a final fallback in document order. The
        # size check below prevents icons and tiny UI thumbnails from winning.
        score = method_score * 100 + related_score * 10 + 1
        self.candidates.append((score, self.order, source))


def save_web_image(image: bytes, target: Path) -> tuple[int, int]:
    """Convert a real project-page asset (including WebP/AVIF) to JPEG."""
    with Image.open(BytesIO(image)) as opened:
        image_rgb = opened.convert("RGB")
        if image_rgb.width < 240 or image_rgb.height < 140:
            raise ValueError("candidate project image is too small to be a framework figure")
        image_rgb.save(target, format="JPEG", quality=86, optimize=True)
        return image_rgb.width, image_rgb.height


def extract_web_figure(report_id: str, source_url: str, target: Path) -> dict | None:
    """Save an explicitly labelled method image from an official project page."""
    request = urllib.request.Request(source_url, headers={"User-Agent": "EmbodiedReports/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            html = response.read().decode("utf-8", "ignore")
        parser = ProjectImageParser()
        parser.feed(html)
        if not parser.candidates:
            return None
        # First prefer an explicitly labelled framework. If unavailable, retain
        # the first sizeable method-related / dataset / results visual from the
        # official project page.  No synthetic or code-rendered diagram is used.
        ordered = sorted(parser.candidates, key=lambda item: (-item[0], item[1]))[:16]
        for score, _, image_ref in ordered:
            image_url = urljoin(source_url, image_ref)
            try:
                with urllib.request.urlopen(
                    urllib.request.Request(image_url, headers={"User-Agent": "EmbodiedReports/1.0"}),
                    timeout=30,
                ) as response:
                    image = response.read()
                width, height = save_web_image(image, target)
                return {
                    "id": report_id,
                    "asset": f"frameworks/{report_id}.jpg",
                    "source_url": source_url,
                    "page": None,
                    "caption_detected": score >= 100,
                    "source_kind": "official_project_page",
                    "selection": "method_figure" if score >= 100 else "official_project_visual",
                    "image_url": image_url,
                    "width": width,
                    "height": height,
                }
            except Exception as exc:
                print(f"warning: candidate image failed for {image_url}: {exc}")
        return None
    except Exception as exc:
        print(f"warning: web framework extraction failed for {source_url}: {exc}")
        return None


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


def extract(report_id: str, source_url: str, official_url: str | None = None, refresh: bool = False) -> dict | None:
    target = OUT_DIR / f"{report_id}.jpg"
    if target.exists() and not refresh:
        return {"id": report_id, "asset": f"frameworks/{report_id}.jpg", "source_url": source_url, "page": None, "caption_detected": False, "cached": True}
    body = fetch_pdf(arxiv_pdf(source_url))
    if body is None:
        # A non-PDF report link can be an announcement or an arXiv lead.  In
        # that case, look for an explicitly labelled diagram on the dedicated
        # official project page instead of treating the report URL as the only
        # possible web source.
        return extract_web_figure(report_id, official_url or source_url, target)
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
    verified = json.loads(VERIFIED.read_text()) if VERIFIED.exists() else []
    dynamic = []
    for report in verified[:MAX_REPORTS]:
        links = report.get("links", [])
        primary = next((link["url"] for link in links if link.get("label") == "Report"), None)
        official = next((link["url"] for link in links if link.get("label") == "Project"), None)
        if primary or official:
            dynamic.append({"id": report["id"], "source_url": primary or official, "official_url": official})
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
            results = list(pool.map(lambda item: extract(item["id"], item["source_url"], item.get("official_url"), args.refresh), source_items))
    entries = [result for result in results if result]
    MANIFEST.write_text(json.dumps({"figures": entries}, ensure_ascii=False, indent=2) + "\n")
    print(f"extracted={len(entries)} sources={len(source_items)}")


if __name__ == "__main__":
    main()
