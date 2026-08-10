#!/usr/bin/env python3
"""Extract original visuals from official project pages only.

The index never generates diagrams. It stores only decoded, rasterized assets
served by the official project page and records their provenance in the manifest.
"""

from __future__ import annotations

import json
import re
import html as html_lib
import urllib.request
import argparse
import tempfile
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
MAX_REPORTS = 120


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
        tag = tag.lower()
        values = {key.lower(): value or "" for key, value in attrs}
        if tag == "meta":
            property_name = (values.get("property") or values.get("name") or "").lower()
            source = values.get("content")
            if property_name in {"og:image", "twitter:image"} and source:
                self.order += 1
                # OpenGraph/Twitter cards are the publisher's declared project
                # visual and are used only after explicit in-page figures.
                self.candidates.append((3, self.order, source))
            return
        if tag == "link":
            rel = values.get("rel", "").lower()
            as_type = values.get("as", "").lower()
            source = values.get("href") if "preload" in rel and as_type == "image" else None
        elif tag == "video":
            source = values.get("poster") or values.get("data-poster")
        elif tag in {"img", "source"}:
            source = values.get("src") or values.get("data-src") or values.get("data-original")
        else:
            style = " ".join(values.get(key, "") for key in ("style", "data-bg", "data-background-image", "data-background"))
            match = re.search(r"""url\(\s*['"]?([^'")]+)""", style, flags=re.I)
            source = match.group(1) if match else None
        # Some responsive project pages expose only srcset; resolve it before
        # rejecting the tag so an otherwise valid official image is not lost.
        if not source and values.get("srcset"):
            source = values["srcset"].split(",", 1)[0].strip().split(" ", 1)[0]
        if not source:
            return
        self.order += 1
        text = " ".join(values.get(key, "") for key in ("alt", "title", "class", "id", "src", "data-src", "srcset", "style", "poster")).lower()
        if source.startswith("data:") or any(term in text for term in self.EXCLUDED_TERMS):
            return
        method_score = sum(1 for term in self.METHOD_TERMS if term in text)
        related_score = sum(1 for term in self.RELATED_TERMS if term in text)
        # Keep non-decorative images as a final fallback in document order. The
        # size check below prevents icons and tiny UI thumbnails from winning.
        # Prefer an actual in-page image over the social-card image.  When no
        # method diagram exists, this makes the first usable project visual the
        # deterministic fallback required for every card.
        score = method_score * 1000 + related_score * 100 + 10
        self.candidates.append((score, self.order, source))


def looks_like_svg(image: bytes) -> bool:
    """Accept SVG documents with an XML declaration, BOM, or whitespace."""
    head = image[:4096].lstrip().lower()
    return head.startswith(b"<svg") or head.startswith(b"<?xml") and b"<svg" in head


def save_web_image(image: bytes, target: Path) -> tuple[int, int]:
    """Convert a real project-page asset (including XML-prefixed SVG) to JPEG."""
    if looks_like_svg(image):
        document = fitz.open(stream=image, filetype="svg")
        try:
            pixmap = document[0].get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
            if pixmap.width < 240 or pixmap.height < 140:
                raise ValueError("candidate project image is too small to be a framework figure")
            pixmap.save(target, jpg_quality=86)
            return pixmap.width, pixmap.height
        finally:
            document.close()
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
        # Some official sites (notably Next.js release pages) serialize their
        # actual project markup inside a script as ``\\u003cimg ...\\u003e``.
        # Feed that markup to the same source-image parser. This is still an
        # original asset served by the official page; it merely is not present
        # as a browser-visible <img> in the initial document shell.
        embedded_markup = html_lib.unescape(
            html.replace("\\u003c", "<").replace("\\u003e", ">")
            .replace("\\u0026", "&").replace("\\\\\"", '"')
        )
        embedded_markup = embedded_markup.replace('\\"', '"')
        parser = ProjectImageParser()
        parser.feed(embedded_markup)
        # The decoded release markup is still nested inside its original
        # <script> node, so HTMLParser correctly treats it as text above.
        # Parse its image/source fragments once more as standalone tags.
        for tag in re.findall(r"<(?:img|source|video|link|[^>]+style=)[^>]*>", embedded_markup, flags=re.I):
            parser.feed(tag)
        # Some release sites render the hero as a CSS background rather than an
        # <img>. It remains a real asset from that official project page.
        for image_ref in re.findall(r"""(?:background(?:-image)?|data-background(?:-image)?)\s*[:=]\s*url\(\s*['"]?([^'")]+)""", embedded_markup, flags=re.I):
            parser.order += 1
            parser.candidates.append((8, parser.order, image_ref))
        if not parser.candidates:
            return None
        # First prefer an explicitly labelled framework. If unavailable, retain
        # the first sizeable method-related / dataset / results visual from the
        # official project page.  No synthetic or code-rendered diagram is used.
        ordered = sorted(parser.candidates, key=lambda item: (-item[0], item[1]))[:64]
        for score, _, image_ref in ordered:
            # Treat the page URL as a directory so project-local assets such
            # as ``assets/images/overview.jpg`` resolve to /pages/<project>/.
            image_url = urljoin(source_url.rstrip("/") + "/", image_ref)
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


def extract(
    report_id: str,
    source_url: str,
    official_url: str | None = None,
    refresh: bool = False,
    target: Path | None = None,
) -> dict | None:
    """Use only project-page media; PDFs are intentionally not a fallback."""
    target = target or OUT_DIR / f"{report_id}.jpg"
    if target.exists() and not refresh:
        return {"id": report_id, "asset": f"frameworks/{report_id}.jpg", "source_url": official_url or source_url, "page": None, "caption_detected": False, "cached": True, "source_kind": "official_project_page"}
    project_url = official_url or source_url
    if re.search(r"\.(?:svg|png|jpe?g|webp|avif)(?:[?#].*)?$", project_url, re.I):
        try:
            with urllib.request.urlopen(urllib.request.Request(project_url, headers={"User-Agent": "EmbodiedReports/1.0"}), timeout=30) as response:
                width, height = save_web_image(response.read(), target)
            return {"id": report_id, "asset": f"frameworks/{report_id}.jpg", "source_url": project_url, "image_url": project_url, "page": None, "caption_detected": True, "source_kind": "official_project_page", "selection": "official_project_visual", "width": width, "height": height}
        except Exception as exc:
            print(f"warning: direct official project image failed for {project_url}: {exc}")
            return None
    return extract_web_figure(report_id, project_url, target)

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
    # Explicit official-image sources are a deterministic priority list. They
    # remain testable even when the automatically generated catalog grows.
    by_id = {item["id"]: item for item in dynamic}
    static_ids = []
    for item in static:
        if item.get("id") and item.get("source_url"):
            by_id[item["id"]] = item
            static_ids.append(item["id"])
    ordered_ids = [*dict.fromkeys(static_ids), *(item["id"] for item in dynamic if item.get("id") not in static_ids)]
    return [by_id[item_id] for item_id in ordered_ids[:MAX_REPORTS]]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cached-only", action="store_true", help="write a manifest for previously extracted official project images without fetching")
    parser.add_argument("--refresh", action="store_true", help="re-fetch and replace previously extracted crops")
    parser.add_argument("--limit", type=int, default=None, help="only process the first N stable source entries")
    parser.add_argument(
        "--preflight-ids",
        default="",
        help="comma-separated official-image source IDs to fetch and decode without changing the catalog",
    )
    args = parser.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    source_items = sources()
    if args.limit is not None:
        source_items = source_items[:args.limit]
    required_ids = [item.strip() for item in args.preflight_ids.split(",") if item.strip()]
    if required_ids:
        by_id = {item["id"]: item for item in source_items}
        missing = [item_id for item_id in required_ids if item_id not in by_id]
        if missing:
            raise SystemExit(f"preflight sources not registered: {', '.join(missing)}")
        with tempfile.TemporaryDirectory(prefix="framework-preflight-") as temp_dir:
            temp_root = Path(temp_dir)
            failures = []
            for item_id in required_ids:
                item = by_id[item_id]
                result = extract(
                    item["id"],
                    item["source_url"],
                    item.get("official_url"),
                    refresh=True,
                    target=temp_root / f"{item_id}.jpg",
                )
                if not result:
                    failures.append(item_id)
            if failures:
                raise SystemExit(f"required official project images could not be fetched/decoded: {', '.join(failures)}")
        print(f"preflight_passed={len(required_ids)}")
        return
    previous_entries = {
        item.get("id"): item
        for item in (json.loads(MANIFEST.read_text()).get("figures", []) if MANIFEST.exists() else [])
        if isinstance(item, dict) and item.get("id")
    }
    if args.cached_only:
        results = [
            {"id": item["id"], "asset": f"frameworks/{item['id']}.jpg", "source_url": item["source_url"], "page": None, "caption_detected": False, "cached": True}
            for item in source_items
            if (OUT_DIR / f"{item['id']}.jpg").exists()
        ]
    else:
        with ThreadPoolExecutor(max_workers=6) as pool:
            results = list(pool.map(lambda item: extract(item["id"], item["source_url"], item.get("official_url"), args.refresh), source_items))
    entries = []
    for item, result in zip(source_items, results):
        if result:
            entries.append(result)
            continue
        # A temporary CDN/anti-bot failure must not blank an already extracted
        # source image on the public site. Keep it until a future refresh can
        # replace it with another verified source asset.
        previous = previous_entries.get(item["id"])
        if previous and (OUT_DIR / f"{item['id']}.jpg").exists():
            entries.append(previous)
    MANIFEST.write_text(json.dumps({"figures": entries}, ensure_ascii=False, indent=2) + "\n")
    print(f"extracted={len(entries)} sources={len(source_items)}")


if __name__ == "__main__":
    main()
