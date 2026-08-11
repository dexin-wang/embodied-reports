#!/usr/bin/env python3
"""Discover software releases by crawling one organization's official sources at a time.

The previous implementation asked a model to search several organizations in one
request.  A response could omit most names, yet the whole batch was recorded as
complete.  This module instead persists an official-source registry and records
one crawl result for exactly one canonical organization.
"""

from __future__ import annotations

import argparse
import http.client
import json
import os
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import quote, urljoin, urlparse, urlunparse

from organization_coverage import (
    ensure_coverage,
    organization_id,
    record_official_result,
    roster_entries,
)


ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = ROOT / "automation" / "candidates.json"
COMPANY_ROSTER = ROOT / "automation" / "company_roster.json"
MEDIA_WATCHLIST = ROOT / "automation" / "media_watchlist.json"
SOURCE_REGISTRY = ROOT / "automation" / "official_source_registry.json"
API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = os.getenv("OPENAI_VERIFIER_MODEL", "gpt-5.6")
API_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
RETRY_ATTEMPTS = 3
HTTP_TIMEOUT_SECONDS = 12
MAX_DOCUMENT_BYTES = 1_500_000
MAX_CRAWL_PAGES = 28
DEFAULT_BOOTSTRAP_LIMIT = 12
FETCH_ERRORS = (
    urllib.error.URLError, urllib.error.HTTPError, http.client.HTTPException,
    TimeoutError, OSError, ValueError, UnicodeError,
)

SOFTWARE_TERMS = (
    "vision-language", "vision language", "vla", "foundation model",
    "world model", "action model", "robot policy", "policy learning",
    "imitation learning", "reinforcement learning", "embodied ai",
    "embodied agent", "physical ai", "robot learning", "robotics software",
    "dataset", "benchmark", "data engine", "data collection", "simulation",
    "simulator", "sim-to-real", "planning", "control", "inference",
    "model", "模型", "具身智能", "视觉语言", "策略", "数据集", "数据引擎",
    "世界模型", "动作模型", "仿真", "规划", "控制", "大语言模型",
)
HARDWARE_ONLY_TERMS = (
    "robot body", "humanoid robot", "quadruped robot", "robot hand",
    "robot arm", "sensor", "actuator", "motor", "hardware specification",
    "new humanoid", "人形机器人整机", "机器人本体", "机械臂产品",
    "灵巧手产品", "传感器产品", "新品发布会",
)
PUBLICATION_PATH_TERMS = (
    "/blog", "/news", "/research", "/project", "/projects", "/post", "/posts",
    "/release", "/releases", "/updates", "/insight", "/insights", "/story",
    "/stories", "/resource", "/resources", "/article", "/articles",
)
DATE_PATTERN = re.compile(r"(20(?:25|26|27))[-/.年](0?[1-9]|1[0-2])[-/.月](0?[1-9]|[12]\d|3[01])?")


MEDIA_ITEM = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "title": {"type": "string"}, "url": {"type": "string"}, "date": {"type": "string"},
        "summary": {"type": "string"}, "organization_hint": {"type": "string"},
    },
    "required": ["title", "url", "date", "summary", "organization_hint"],
}
MEDIA_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {"candidates": {"type": "array", "items": MEDIA_ITEM, "minItems": 0, "maxItems": 20}},
    "required": ["candidates"],
}
BOOTSTRAP_CANDIDATE = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "title": {"type": "string"}, "url": {"type": "string"}, "date": {"type": "string"},
        "summary": {"type": "string"},
    },
    "required": ["title", "url", "date", "summary"],
}
BOOTSTRAP_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "official_organization_urls": {
            "type": "array", "items": {"type": "string"}, "minItems": 0, "maxItems": 5,
        },
        "candidates": {
            "type": "array", "items": BOOTSTRAP_CANDIDATE, "minItems": 0, "maxItems": 8,
        },
    },
    "required": ["official_organization_urls", "candidates"],
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def normalize_url(value: object) -> str:
    """Return a request-safe HTTPS URL or an empty string.

    Official sites often contain human-readable links such as
    "/news/company news/".  Spaces are legal page-path text but not legal in an
    HTTP request, so they must be encoded before urlopen sees them.  Embedded
    control characters are discarded because no public URL may contain them.
    """
    if not isinstance(value, str):
        return ""
    value = re.sub(r"[\x00-\x1f\x7f]+", "", value).strip()
    try:
        parsed = urlparse(value)
    except ValueError:
        return ""
    if parsed.scheme != "https" or not parsed.netloc or any(char.isspace() for char in parsed.netloc):
        return ""
    path = quote(parsed.path or "/", safe="/%:@!def normalize_url(value: object) -> str:
    if not isinstance(value, str):
        return ""
    value = value.strip()
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc:
        return ""
    return urlunparse((
        "https", parsed.netloc.lower(), parsed.path or "/", parsed.params, parsed.query, "",
    ))
'()*+,;=-._~")
    query = quote(parsed.query, safe="=%&/:?@!

def https_urls(values: object, limit: int = 40) -> list[str]:
    if not isinstance(values, list):
        return []
    return sorted({url for value in values if (url := normalize_url(value))})[:limit]


def response_text(result: dict[str, Any]) -> str:
    direct = result.get("output_text")
    if isinstance(direct, str) and direct.strip():
        return direct
    parts: list[str] = []
    for output in result.get("output", []):
        if not isinstance(output, dict):
            continue
        for content in output.get("content", []):
            if isinstance(content, dict) and content.get("type") == "output_text":
                text = content.get("text")
                if isinstance(text, str):
                    parts.append(text)
    if parts:
        return "\n".join(parts)
    summary = json.dumps(
        {key: result.get(key) for key in ("status", "error", "incomplete_details", "output")},
        ensure_ascii=False,
    )[:1600]
    raise ValueError(f"Responses API returned no output text: {summary}")


def response_json(result: dict[str, Any]) -> dict[str, Any]:
    text = response_text(result).lstrip()
    start = text.find("{")
    if start < 0:
        raise ValueError(f"Responses API output did not contain JSON: {text[:800]}")
    value, _ = json.JSONDecoder().raw_decode(text[start:])
    if not isinstance(value, dict):
        raise ValueError("Responses API JSON output was not an object")
    return value


def request_model(payload: dict[str, Any], label: str) -> tuple[dict[str, Any] | None, str | None]:
    if not API_KEY:
        return None, "OPENAI_API_KEY is not configured"
    request = urllib.request.Request(
        f"{API_BASE_URL}/responses",
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
    )
    error = "unknown provider error"
    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                return json.loads(response.read()), None
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "ignore")[:1000]
            if 400 <= exc.code < 500 and exc.code != 429:
                return None, f"{label} request rejected ({exc.code}): {detail}"
            error = f"HTTP {exc.code}: {detail}"
        except (urllib.error.URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError) as exc:
            error = f"{type(exc).__name__}: {exc}"
        if attempt < RETRY_ATTEMPTS:
            delay = 4 * attempt
            print(f"warning: {label} failed ({attempt}/{RETRY_ATTEMPTS}); retrying in {delay}s: {error}")
            time.sleep(delay)
    return None, f"{label} provider exhausted retries: {error}"


def bootstrap_sources(organization: dict[str, str]) -> tuple[list[str], list[dict[str, str]], str | None]:
    """Use one targeted web-search request only to establish a missing official source."""
    prompt = f"""Find the official web presence for exactly one organization: {organization["name"]}.
Return up to five official organization roots (company, lab, project, newsroom, research or official GitHub) and up to eight qualifying official software releases since 2025 from that same organization.

A qualifying release is software for embodied robotics or LLMs: VLA/foundation/world/action model, policy, data engine/dataset, simulator, planning/control stack, benchmark or embodied-agent framework. Exclude hardware-only robot, hand, sensor, motor, body and product announcements.
Every returned URL must be an official organization-owned page or the organization's official GitHub release/repository. Do not return media, arXiv, aggregators, or guessed URLs. If no qualifying release exists, return an empty candidates array but still return the official root(s) when known.
Dates must be YYYY-MM-DD and not earlier than 2025-01-01. Return factual English summaries only."""
    payload = {
        "model": MODEL,
        "reasoning": {"effort": "low"},
        "tools": [{"type": "web_search", "search_context_size": "medium"}],
        "input": [{"role": "user", "content": [{"type": "input_text", "text": prompt}]}],
        "text": {"format": {
            "type": "json_schema", "name": "organization_official_sources",
            "strict": True, "schema": BOOTSTRAP_SCHEMA,
        }},
    }
    result, error = request_model(payload, f"official-source bootstrap for {organization['name']}")
    if error or result is None:
        return [], [], error
    try:
        value = response_json(result)
        roots = https_urls(value.get("official_organization_urls", []), limit=5)
        candidates = [
            {
                "title": item["title"].strip(), "url": normalize_url(item["url"]),
                "date": item["date"].strip(), "summary": item["summary"].strip(),
                "organization_hint": organization["name"],
            }
            for item in value.get("candidates", [])
            if isinstance(item, dict) and normalize_url(item.get("url"))
            and isinstance(item.get("date"), str) and item["date"] >= "2025-01-01"
        ]
        return roots, candidates, None
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        return [], [], f"invalid bootstrap response: {exc}"


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_parts: list[str] = []
        self.in_title = False
        self.links: list[str] = []
        self.meta: dict[str, str] = {}
        self.feed_urls: list[str] = []
        self.time_values: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.lower(): (value or "") for key, value in attrs}
        tag = tag.lower()
        if tag == "title":
            self.in_title = True
        elif tag == "a" and values.get("href"):
            self.links.append(values["href"])
        elif tag == "meta":
            key = (values.get("property") or values.get("name") or "").lower()
            content = values.get("content", "")
            if key and content:
                self.meta[key] = content
        elif tag == "link" and values.get("href"):
            relation = values.get("rel", "").lower()
            kind = values.get("type", "").lower()
            if "alternate" in relation and ("rss" in kind or "atom" in kind):
                self.feed_urls.append(values["href"])
        elif tag == "time" and values.get("datetime"):
            self.time_values.append(values["datetime"])

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self.in_title = False

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title_parts.append(data)


def fetch_text(url: str, *, timeout: int = HTTP_TIMEOUT_SECONDS) -> tuple[str, str]:
    normalized = normalize_url(url)
    if not normalized:
        raise ValueError(f"invalid official-source URL: {url!r}")
    request = urllib.request.Request(normalized, headers={
        "User-Agent": "embodied-reports-bot/1.0 (+https://github.com/dexin-wang/embodied-reports)",
        "Accept": "text/html,application/xhtml+xml,application/xml,text/xml,text/plain;q=0.8,*/*;q=0.2",
    })
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            final_url = normalize_url(response.geturl()) or normalized
            raw = response.read(MAX_DOCUMENT_BYTES)
            charset = response.headers.get_content_charset() or "utf-8"
    except http.client.HTTPException as exc:
        # urllib raises InvalidURL (an HTTPException) before it can become a
        # URLError.  Convert it to a normal per-site fetch failure.
        raise ValueError(f"invalid official-source URL: {normalized!r}: {exc}") from exc
    return final_url, raw.decode(charset, errors="replace")


def fetch_document(url: str) -> dict[str, Any]:
    final_url, html = fetch_text(url)
    parser = PageParser()
    parser.feed(html)
    parser.close()
    title = unescape(" ".join(parser.title_parts)).strip()
    description = unescape(
        parser.meta.get("og:description") or parser.meta.get("description") or ""
    ).strip()
    return {
        "url": final_url,
        "title": title,
        "description": description,
        "links": [urljoin(final_url, value) for value in parser.links],
        "feed_urls": [urljoin(final_url, value) for value in parser.feed_urls],
        "dates": parser.time_values + [
            parser.meta[key] for key in (
                "article:published_time", "date", "publishdate", "pubdate", "datepublished"
            ) if parser.meta.get(key)
        ],
    }


def host(url: str) -> str:
    return urlparse(url).netloc.lower().removeprefix("www.")


def source_host(url: str) -> str:
    return host(url)


def same_official_host(url: str, roots: list[str]) -> bool:
    candidate_host = host(url)
    if candidate_host == "github.com":
        return True
    return any(candidate_host == source_host(root) or candidate_host.endswith("." + source_host(root)) for root in roots)


def page_text(document: dict[str, Any]) -> str:
    return " ".join(str(document.get(key, "")) for key in ("url", "title", "description")).lower()


def has_software_signal(value: str) -> bool:
    return any(term in value for term in SOFTWARE_TERMS)


def hardware_only(value: str) -> bool:
    return any(term in value for term in HARDWARE_ONLY_TERMS) and not has_software_signal(value)


def publication_link(url: str) -> bool:
    path = urlparse(url).path.lower()
    return any(term in path for term in PUBLICATION_PATH_TERMS)


def parse_date(values: list[object]) -> str:
    for value in values:
        if not isinstance(value, str):
            continue
        match = DATE_PATTERN.search(value)
        if not match:
            continue
        year, month, day = match.groups()
        day = day or "01"
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
    return ""


def sitemap_links(root: str) -> list[str]:
    """Read standard sitemap locations without treating failed pages as successful scans."""
    origin = f"https://{urlparse(root).netloc}"
    sitemap_urls = [f"{origin}/sitemap.xml", f"{origin}/sitemap_index.xml"]
    try:
        _, robots = fetch_text(f"{origin}/robots.txt")
        sitemap_urls.extend(re.findall(r"(?im)^sitemap:\\s*(https?://\\S+)", robots))
    except FETCH_ERRORS:
        pass
    links: list[str] = []
    for sitemap in https_urls(sitemap_urls, limit=5):
        try:
            _, xml = fetch_text(sitemap)
        except FETCH_ERRORS:
            continue
        links.extend(re.findall(r"<loc>\\s*([^<\\s]+)\\s*</loc>", xml, flags=re.I))
    return https_urls(links, limit=160)


def candidate_from_document(
    organization: dict[str, str],
    document: dict[str, Any],
    bootstrap_by_url: dict[str, dict[str, str]],
) -> dict[str, str] | None:
    url = normalize_url(document.get("url"))
    if not url:
        return None
    bootstrap = bootstrap_by_url.get(url)
    text = page_text(document)
    if hardware_only(text):
        return None
    if not bootstrap and not has_software_signal(text):
        return None
    date = (bootstrap or {}).get("date") or parse_date(document.get("dates", []))
    if not date or date < "2025-01-01":
        return None
    title = (bootstrap or {}).get("title") or str(document.get("title") or "").strip()
    if not title:
        return None
    summary = (bootstrap or {}).get("summary") or str(document.get("description") or "").strip()
    if not summary:
        summary = f"Official release page from {organization['name']}."
    return {
        "title": title, "url": url, "date": date, "summary": summary[:1200],
        "organization_hint": organization["name"],
    }


def crawl_organization(
    organization: dict[str, str],
    roots: list[str],
    bootstrap_candidates: list[dict[str, str]],
) -> tuple[list[dict[str, str]], list[str], list[str], str | None]:
    """Crawl one institution's official pages, sitemap and feed links."""
    roots = https_urls(roots, limit=8)
    bootstrap_by_url = {
        normalize_url(item["url"]): item for item in bootstrap_candidates
        if normalize_url(item.get("url"))
    }
    queue = list(roots) + list(bootstrap_by_url)
    visited: set[str] = set()
    scanned: list[str] = []
    documents: list[dict[str, Any]] = []
    errors: list[str] = []
    while queue and len(visited) < MAX_CRAWL_PAGES:
        current = normalize_url(queue.pop(0))
        if not current or current in visited:
            continue
        if roots and not same_official_host(current, roots):
            continue
        visited.add(current)
        try:
            document = fetch_document(current)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, ValueError) as exc:
            errors.append(f"{current}: {type(exc).__name__}")
            continue
        scanned.append(document["url"])
        documents.append(document)
        links = [normalize_url(value) for value in [*document["links"], *document["feed_urls"]]]
        for link in links:
            if link and link not in visited and same_official_host(link, roots):
                if publication_link(link) or has_software_signal(link.lower()):
                    queue.append(link)

    # Sitemaps are a fallback after normal navigation. They make blog/news pages
    # discoverable even when a site uses a JavaScript-only menu.
    if not any(candidate_from_document(organization, page, bootstrap_by_url) for page in documents):
        for root in roots[:3]:
            for link in sitemap_links(root):
                if len(visited) >= MAX_CRAWL_PAGES:
                    break
                if link in visited or not same_official_host(link, roots):
                    continue
                if not (publication_link(link) or has_software_signal(link.lower())):
                    continue
                visited.add(link)
                try:
                    document = fetch_document(link)
                except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, ValueError) as exc:
                    errors.append(f"{link}: {type(exc).__name__}")
                    continue
                scanned.append(document["url"])
                documents.append(document)

    candidates: dict[str, dict[str, str]] = {}
    for document in documents:
        item = candidate_from_document(organization, document, bootstrap_by_url)
        if item:
            candidates[item["url"]] = item
    # A candidate explicit in the targeted official-source lookup stays eligible
    # even if the page is temporarily blocked to the crawler. It remains subject
    # to the strict downstream official-source verifier.
    for url, item in bootstrap_by_url.items():
        if item.get("date", "") >= "2025-01-01" and url not in candidates:
            candidates[url] = item
    error = "; ".join(errors[:4]) if not scanned and errors else None
    return list(candidates.values()), roots, https_urls(scanned), error


def load_registry() -> dict[str, Any]:
    registry = load_json(SOURCE_REGISTRY, {})
    if registry.get("schema_version") != 1 or not isinstance(registry.get("organizations"), dict):
        return {"schema_version": 1, "updated_at": None, "organizations": {}}
    return registry


def save_registry(registry: dict[str, Any]) -> None:
    registry["schema_version"] = 1
    registry["updated_at"] = utc_now()
    write_json(SOURCE_REGISTRY, registry)


def registry_entry(registry: dict[str, Any], organization: dict[str, str]) -> dict[str, Any]:
    return registry["organizations"].get(organization["id"], {})


def store_sources(
    registry: dict[str, Any],
    organization: dict[str, str],
    roots: list[str],
    bootstrap_candidates: list[dict[str, str]],
    error: str | None = None,
) -> None:
    registry["organizations"][organization["id"]] = {
        "name": organization["name"],
        "official_urls": https_urls(roots, limit=8),
        "bootstrap_candidate_urls": https_urls([item.get("url", "") for item in bootstrap_candidates], limit=8),
        "last_bootstrapped_at": utc_now(),
        "last_error": error,
    }


def merge_candidates(existing: dict[str, dict[str, Any]], items: list[dict[str, str]], reason: str) -> int:
    added = 0
    for item in items:
        url = normalize_url(item.get("url"))
        date = item.get("date", "")
        if not url or not isinstance(date, str) or date < "2025-01-01":
            continue
        previous = existing.get(url, {})
        existing[url] = {
            **previous, **item, "url": url, "authors": [],
            "score": 100,
            "reasons": sorted(set([*previous.get("reasons", []), reason])),
        }
        added += 1
    return added


def write_candidates(by_url: dict[str, dict[str, Any]]) -> None:
    merged = sorted(
        by_url.values(),
        key=lambda item: (item.get("date", ""), item.get("title", "")),
        reverse=True,
    )
    write_json(CANDIDATES, {"generated_at": utc_now(), "candidates": merged})


def call_media() -> tuple[list[dict[str, str]], str | None]:
    watchlist = load_json(MEDIA_WATCHLIST, [])
    accounts = [item.get("name", "") for item in watchlist if isinstance(item, dict) and item.get("name")]
    prompt = """Search public WeChat Official Account articles from these independent AI/robotics media accounts: """
    prompt += ", ".join(accounts)
    prompt += """.
Find influential embodied-robotics or LLM SOFTWARE releases since 2025. Media is discovery evidence only: resolve every item to a dedicated official project/release page and return that official URL, never the media article.
Include VLA/foundation/world/action models, policies, data engines/datasets, simulators, control/planning stacks, benchmarks or embodied-agent frameworks. Exclude hardware-only robot/product announcements. Do not return arXiv URLs."""
    payload = {
        "model": MODEL, "reasoning": {"effort": "low"},
        "tools": [{"type": "web_search", "search_context_size": "medium"}],
        "input": [{"role": "user", "content": [{"type": "input_text", "text": prompt}]}],
        "text": {"format": {
            "type": "json_schema", "name": "media_resolved_official_projects",
            "strict": True, "schema": MEDIA_SCHEMA,
        }},
    }
    result, error = request_model(payload, "media discovery")
    if error or result is None:
        return [], error
    try:
        return [
            {**item, "url": normalize_url(item["url"])}
            for item in response_json(result)["candidates"]
            if normalize_url(item.get("url"))
            and isinstance(item.get("date"), str) and item["date"] >= "2025-01-01"
        ], None
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        return [], f"invalid media response: {exc}"


def run_official_discovery(bootstrap_limit: int) -> tuple[int, dict[str, int]]:
    payload = load_json(CANDIDATES, {"candidates": []})
    by_url = {
        normalize_url(item.get("url")): item for item in payload.get("candidates", [])
        if isinstance(item, dict) and normalize_url(item.get("url"))
    }
    registry = load_registry()
    ensure_coverage()
    batch_prefix = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    added = 0
    bootstrapped = 0

    for index, organization in enumerate(roster_entries(), 1):
        entry = registry_entry(registry, organization)
        roots = https_urls(entry.get("official_urls", []), limit=8)
        candidate_urls = https_urls(entry.get("bootstrap_candidate_urls", []), limit=8)
        bootstrap_candidates = [
            {"title": "", "url": url, "date": "", "summary": "", "organization_hint": organization["name"]}
            for url in candidate_urls
        ]
        if not roots:
            if bootstrapped >= bootstrap_limit:
                # Leave the status pending: it was not scanned, rather than
                # falsely declaring a zero-result crawl complete.
                continue
            bootstrapped += 1
            roots, bootstrap_candidates, error = bootstrap_sources(organization)
            store_sources(registry, organization, roots, bootstrap_candidates, error)
            # Checkpoint source discovery immediately. A later unrelated site
            # failure must not force the next run to pay for this bootstrap again.
            save_registry(registry)
            if error:
                record_official_result(
                    organization["name"], [], status="failed",
                    batch=f"official-{batch_prefix}-{index:03d}",
                    source_urls=roots, scanned_urls=[], error=error,
                )
                continue
        candidates, source_urls, scanned_urls, error = crawl_organization(
            organization, roots, bootstrap_candidates,
        )
        if candidates:
            status = "found"
        elif scanned_urls:
            status = "no_qualifying_release"
        else:
            status = "failed"
            error = error or "official source could not be fetched"
        record_official_result(
            organization["name"], candidates, status=status,
            batch=f"official-{batch_prefix}-{index:03d}",
            source_urls=source_urls, scanned_urls=scanned_urls, error=error,
        )
        added += merge_candidates(by_url, candidates, "official web-project discovery")
        # Candidate data is also checkpointed per organization. This is cheap
        # and makes a subsequent retry resume instead of rediscovering pages.
        write_candidates(by_url)

    save_registry(registry)
    write_candidates(by_url)
    coverage = ensure_coverage()
    summary = {
        "organizations": len(coverage["organizations"]),
        "found": sum(item["official_scan"]["status"] == "found" for item in coverage["organizations"]),
        "no_qualifying_release": sum(item["official_scan"]["status"] == "no_qualifying_release" for item in coverage["organizations"]),
        "pending": sum(item["official_scan"]["status"] == "pending" for item in coverage["organizations"]),
        "failed": sum(item["official_scan"]["status"] == "failed" for item in coverage["organizations"]),
        "bootstrapped_this_run": bootstrapped,
    }
    return added, summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("official", "media"), default="official")
    parser.add_argument("--bootstrap-limit", type=int, default=DEFAULT_BOOTSTRAP_LIMIT)
    args = parser.parse_args()
    if args.bootstrap_limit < 0:
        raise SystemExit("--bootstrap-limit must be non-negative")

    if args.mode == "media":
        payload = load_json(CANDIDATES, {"candidates": []})
        by_url = {
            normalize_url(item.get("url")): item for item in payload.get("candidates", [])
            if isinstance(item, dict) and normalize_url(item.get("url"))
        }
        items, error = call_media()
        if error:
            print(f"warning: media discovery skipped: {error}")
            return
        added = merge_candidates(by_url, items, "media-resolved official project discovery")
        merged = sorted(by_url.values(), key=lambda item: (item.get("date", ""), item.get("title", "")), reverse=True)
        write_json(CANDIDATES, {"generated_at": utc_now(), "candidates": merged})
        print(f"media_project_leads_added={added} candidates_total={len(merged)}")
        return

    added, summary = run_official_discovery(args.bootstrap_limit)
    print(f"official_coverage={json.dumps(summary, ensure_ascii=False, sort_keys=True)}")
    print(f"official_project_leads_added={added}")


if __name__ == "__main__":
    main()
()*+,;.-_~")
    return urlunparse((
        "https", parsed.netloc.lower(), path, parsed.params, query, "",
    ))


def https_urls(values: object, limit: int = 40) -> list[str]:
    if not isinstance(values, list):
        return []
    return sorted({url for value in values if (url := normalize_url(value))})[:limit]


def response_text(result: dict[str, Any]) -> str:
    direct = result.get("output_text")
    if isinstance(direct, str) and direct.strip():
        return direct
    parts: list[str] = []
    for output in result.get("output", []):
        if not isinstance(output, dict):
            continue
        for content in output.get("content", []):
            if isinstance(content, dict) and content.get("type") == "output_text":
                text = content.get("text")
                if isinstance(text, str):
                    parts.append(text)
    if parts:
        return "\n".join(parts)
    summary = json.dumps(
        {key: result.get(key) for key in ("status", "error", "incomplete_details", "output")},
        ensure_ascii=False,
    )[:1600]
    raise ValueError(f"Responses API returned no output text: {summary}")


def response_json(result: dict[str, Any]) -> dict[str, Any]:
    text = response_text(result).lstrip()
    start = text.find("{")
    if start < 0:
        raise ValueError(f"Responses API output did not contain JSON: {text[:800]}")
    value, _ = json.JSONDecoder().raw_decode(text[start:])
    if not isinstance(value, dict):
        raise ValueError("Responses API JSON output was not an object")
    return value


def request_model(payload: dict[str, Any], label: str) -> tuple[dict[str, Any] | None, str | None]:
    if not API_KEY:
        return None, "OPENAI_API_KEY is not configured"
    request = urllib.request.Request(
        f"{API_BASE_URL}/responses",
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
    )
    error = "unknown provider error"
    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                return json.loads(response.read()), None
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "ignore")[:1000]
            if 400 <= exc.code < 500 and exc.code != 429:
                return None, f"{label} request rejected ({exc.code}): {detail}"
            error = f"HTTP {exc.code}: {detail}"
        except (urllib.error.URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError) as exc:
            error = f"{type(exc).__name__}: {exc}"
        if attempt < RETRY_ATTEMPTS:
            delay = 4 * attempt
            print(f"warning: {label} failed ({attempt}/{RETRY_ATTEMPTS}); retrying in {delay}s: {error}")
            time.sleep(delay)
    return None, f"{label} provider exhausted retries: {error}"


def bootstrap_sources(organization: dict[str, str]) -> tuple[list[str], list[dict[str, str]], str | None]:
    """Use one targeted web-search request only to establish a missing official source."""
    prompt = f"""Find the official web presence for exactly one organization: {organization["name"]}.
Return up to five official organization roots (company, lab, project, newsroom, research or official GitHub) and up to eight qualifying official software releases since 2025 from that same organization.

A qualifying release is software for embodied robotics or LLMs: VLA/foundation/world/action model, policy, data engine/dataset, simulator, planning/control stack, benchmark or embodied-agent framework. Exclude hardware-only robot, hand, sensor, motor, body and product announcements.
Every returned URL must be an official organization-owned page or the organization's official GitHub release/repository. Do not return media, arXiv, aggregators, or guessed URLs. If no qualifying release exists, return an empty candidates array but still return the official root(s) when known.
Dates must be YYYY-MM-DD and not earlier than 2025-01-01. Return factual English summaries only."""
    payload = {
        "model": MODEL,
        "reasoning": {"effort": "low"},
        "tools": [{"type": "web_search", "search_context_size": "medium"}],
        "input": [{"role": "user", "content": [{"type": "input_text", "text": prompt}]}],
        "text": {"format": {
            "type": "json_schema", "name": "organization_official_sources",
            "strict": True, "schema": BOOTSTRAP_SCHEMA,
        }},
    }
    result, error = request_model(payload, f"official-source bootstrap for {organization['name']}")
    if error or result is None:
        return [], [], error
    try:
        value = response_json(result)
        roots = https_urls(value.get("official_organization_urls", []), limit=5)
        candidates = [
            {
                "title": item["title"].strip(), "url": normalize_url(item["url"]),
                "date": item["date"].strip(), "summary": item["summary"].strip(),
                "organization_hint": organization["name"],
            }
            for item in value.get("candidates", [])
            if isinstance(item, dict) and normalize_url(item.get("url"))
            and isinstance(item.get("date"), str) and item["date"] >= "2025-01-01"
        ]
        return roots, candidates, None
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        return [], [], f"invalid bootstrap response: {exc}"


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_parts: list[str] = []
        self.in_title = False
        self.links: list[str] = []
        self.meta: dict[str, str] = {}
        self.feed_urls: list[str] = []
        self.time_values: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.lower(): (value or "") for key, value in attrs}
        tag = tag.lower()
        if tag == "title":
            self.in_title = True
        elif tag == "a" and values.get("href"):
            self.links.append(values["href"])
        elif tag == "meta":
            key = (values.get("property") or values.get("name") or "").lower()
            content = values.get("content", "")
            if key and content:
                self.meta[key] = content
        elif tag == "link" and values.get("href"):
            relation = values.get("rel", "").lower()
            kind = values.get("type", "").lower()
            if "alternate" in relation and ("rss" in kind or "atom" in kind):
                self.feed_urls.append(values["href"])
        elif tag == "time" and values.get("datetime"):
            self.time_values.append(values["datetime"])

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self.in_title = False

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title_parts.append(data)


def fetch_text(url: str, *, timeout: int = HTTP_TIMEOUT_SECONDS) -> tuple[str, str]:
    request = urllib.request.Request(url, headers={
        "User-Agent": "embodied-reports-bot/1.0 (+https://github.com/dexin-wang/embodied-reports)",
        "Accept": "text/html,application/xhtml+xml,application/xml,text/xml,text/plain;q=0.8,*/*;q=0.2",
    })
    with urllib.request.urlopen(request, timeout=timeout) as response:
        final_url = normalize_url(response.geturl()) or normalize_url(url)
        raw = response.read(MAX_DOCUMENT_BYTES)
        charset = response.headers.get_content_charset() or "utf-8"
    return final_url, raw.decode(charset, errors="replace")


def fetch_document(url: str) -> dict[str, Any]:
    final_url, html = fetch_text(url)
    parser = PageParser()
    parser.feed(html)
    parser.close()
    title = unescape(" ".join(parser.title_parts)).strip()
    description = unescape(
        parser.meta.get("og:description") or parser.meta.get("description") or ""
    ).strip()
    return {
        "url": final_url,
        "title": title,
        "description": description,
        "links": [urljoin(final_url, value) for value in parser.links],
        "feed_urls": [urljoin(final_url, value) for value in parser.feed_urls],
        "dates": parser.time_values + [
            parser.meta[key] for key in (
                "article:published_time", "date", "publishdate", "pubdate", "datepublished"
            ) if parser.meta.get(key)
        ],
    }


def host(url: str) -> str:
    return urlparse(url).netloc.lower().removeprefix("www.")


def source_host(url: str) -> str:
    return host(url)


def same_official_host(url: str, roots: list[str]) -> bool:
    candidate_host = host(url)
    if candidate_host == "github.com":
        return True
    return any(candidate_host == source_host(root) or candidate_host.endswith("." + source_host(root)) for root in roots)


def page_text(document: dict[str, Any]) -> str:
    return " ".join(str(document.get(key, "")) for key in ("url", "title", "description")).lower()


def has_software_signal(value: str) -> bool:
    return any(term in value for term in SOFTWARE_TERMS)


def hardware_only(value: str) -> bool:
    return any(term in value for term in HARDWARE_ONLY_TERMS) and not has_software_signal(value)


def publication_link(url: str) -> bool:
    path = urlparse(url).path.lower()
    return any(term in path for term in PUBLICATION_PATH_TERMS)


def parse_date(values: list[object]) -> str:
    for value in values:
        if not isinstance(value, str):
            continue
        match = DATE_PATTERN.search(value)
        if not match:
            continue
        year, month, day = match.groups()
        day = day or "01"
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
    return ""


def sitemap_links(root: str) -> list[str]:
    """Read standard sitemap locations without treating failed pages as successful scans."""
    origin = f"https://{urlparse(root).netloc}"
    sitemap_urls = [f"{origin}/sitemap.xml", f"{origin}/sitemap_index.xml"]
    try:
        _, robots = fetch_text(f"{origin}/robots.txt")
        sitemap_urls.extend(re.findall(r"(?im)^sitemap:\\s*(https?://\\S+)", robots))
    except FETCH_ERRORS:
        pass
    links: list[str] = []
    for sitemap in https_urls(sitemap_urls, limit=5):
        try:
            _, xml = fetch_text(sitemap)
        except FETCH_ERRORS:
            continue
        links.extend(re.findall(r"<loc>\\s*([^<\\s]+)\\s*</loc>", xml, flags=re.I))
    return https_urls(links, limit=160)


def candidate_from_document(
    organization: dict[str, str],
    document: dict[str, Any],
    bootstrap_by_url: dict[str, dict[str, str]],
) -> dict[str, str] | None:
    url = normalize_url(document.get("url"))
    if not url:
        return None
    bootstrap = bootstrap_by_url.get(url)
    text = page_text(document)
    if hardware_only(text):
        return None
    if not bootstrap and not has_software_signal(text):
        return None
    date = (bootstrap or {}).get("date") or parse_date(document.get("dates", []))
    if not date or date < "2025-01-01":
        return None
    title = (bootstrap or {}).get("title") or str(document.get("title") or "").strip()
    if not title:
        return None
    summary = (bootstrap or {}).get("summary") or str(document.get("description") or "").strip()
    if not summary:
        summary = f"Official release page from {organization['name']}."
    return {
        "title": title, "url": url, "date": date, "summary": summary[:1200],
        "organization_hint": organization["name"],
    }


def crawl_organization(
    organization: dict[str, str],
    roots: list[str],
    bootstrap_candidates: list[dict[str, str]],
) -> tuple[list[dict[str, str]], list[str], list[str], str | None]:
    """Crawl one institution's official pages, sitemap and feed links."""
    roots = https_urls(roots, limit=8)
    bootstrap_by_url = {
        normalize_url(item["url"]): item for item in bootstrap_candidates
        if normalize_url(item.get("url"))
    }
    queue = list(roots) + list(bootstrap_by_url)
    visited: set[str] = set()
    scanned: list[str] = []
    documents: list[dict[str, Any]] = []
    errors: list[str] = []
    while queue and len(visited) < MAX_CRAWL_PAGES:
        current = normalize_url(queue.pop(0))
        if not current or current in visited:
            continue
        if roots and not same_official_host(current, roots):
            continue
        visited.add(current)
        try:
            document = fetch_document(current)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, ValueError) as exc:
            errors.append(f"{current}: {type(exc).__name__}")
            continue
        scanned.append(document["url"])
        documents.append(document)
        links = [normalize_url(value) for value in [*document["links"], *document["feed_urls"]]]
        for link in links:
            if link and link not in visited and same_official_host(link, roots):
                if publication_link(link) or has_software_signal(link.lower()):
                    queue.append(link)

    # Sitemaps are a fallback after normal navigation. They make blog/news pages
    # discoverable even when a site uses a JavaScript-only menu.
    if not any(candidate_from_document(organization, page, bootstrap_by_url) for page in documents):
        for root in roots[:3]:
            for link in sitemap_links(root):
                if len(visited) >= MAX_CRAWL_PAGES:
                    break
                if link in visited or not same_official_host(link, roots):
                    continue
                if not (publication_link(link) or has_software_signal(link.lower())):
                    continue
                visited.add(link)
                try:
                    document = fetch_document(link)
                except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, ValueError) as exc:
                    errors.append(f"{link}: {type(exc).__name__}")
                    continue
                scanned.append(document["url"])
                documents.append(document)

    candidates: dict[str, dict[str, str]] = {}
    for document in documents:
        item = candidate_from_document(organization, document, bootstrap_by_url)
        if item:
            candidates[item["url"]] = item
    # A candidate explicit in the targeted official-source lookup stays eligible
    # even if the page is temporarily blocked to the crawler. It remains subject
    # to the strict downstream official-source verifier.
    for url, item in bootstrap_by_url.items():
        if item.get("date", "") >= "2025-01-01" and url not in candidates:
            candidates[url] = item
    error = "; ".join(errors[:4]) if not scanned and errors else None
    return list(candidates.values()), roots, https_urls(scanned), error


def load_registry() -> dict[str, Any]:
    registry = load_json(SOURCE_REGISTRY, {})
    if registry.get("schema_version") != 1 or not isinstance(registry.get("organizations"), dict):
        return {"schema_version": 1, "updated_at": None, "organizations": {}}
    return registry


def save_registry(registry: dict[str, Any]) -> None:
    registry["schema_version"] = 1
    registry["updated_at"] = utc_now()
    write_json(SOURCE_REGISTRY, registry)


def registry_entry(registry: dict[str, Any], organization: dict[str, str]) -> dict[str, Any]:
    return registry["organizations"].get(organization["id"], {})


def store_sources(
    registry: dict[str, Any],
    organization: dict[str, str],
    roots: list[str],
    bootstrap_candidates: list[dict[str, str]],
    error: str | None = None,
) -> None:
    registry["organizations"][organization["id"]] = {
        "name": organization["name"],
        "official_urls": https_urls(roots, limit=8),
        "bootstrap_candidate_urls": https_urls([item.get("url", "") for item in bootstrap_candidates], limit=8),
        "last_bootstrapped_at": utc_now(),
        "last_error": error,
    }


def merge_candidates(existing: dict[str, dict[str, Any]], items: list[dict[str, str]], reason: str) -> int:
    added = 0
    for item in items:
        url = normalize_url(item.get("url"))
        date = item.get("date", "")
        if not url or not isinstance(date, str) or date < "2025-01-01":
            continue
        previous = existing.get(url, {})
        existing[url] = {
            **previous, **item, "url": url, "authors": [],
            "score": 100,
            "reasons": sorted(set([*previous.get("reasons", []), reason])),
        }
        added += 1
    return added


def call_media() -> tuple[list[dict[str, str]], str | None]:
    watchlist = load_json(MEDIA_WATCHLIST, [])
    accounts = [item.get("name", "") for item in watchlist if isinstance(item, dict) and item.get("name")]
    prompt = """Search public WeChat Official Account articles from these independent AI/robotics media accounts: """
    prompt += ", ".join(accounts)
    prompt += """.
Find influential embodied-robotics or LLM SOFTWARE releases since 2025. Media is discovery evidence only: resolve every item to a dedicated official project/release page and return that official URL, never the media article.
Include VLA/foundation/world/action models, policies, data engines/datasets, simulators, control/planning stacks, benchmarks or embodied-agent frameworks. Exclude hardware-only robot/product announcements. Do not return arXiv URLs."""
    payload = {
        "model": MODEL, "reasoning": {"effort": "low"},
        "tools": [{"type": "web_search", "search_context_size": "medium"}],
        "input": [{"role": "user", "content": [{"type": "input_text", "text": prompt}]}],
        "text": {"format": {
            "type": "json_schema", "name": "media_resolved_official_projects",
            "strict": True, "schema": MEDIA_SCHEMA,
        }},
    }
    result, error = request_model(payload, "media discovery")
    if error or result is None:
        return [], error
    try:
        return [
            {**item, "url": normalize_url(item["url"])}
            for item in response_json(result)["candidates"]
            if normalize_url(item.get("url"))
            and isinstance(item.get("date"), str) and item["date"] >= "2025-01-01"
        ], None
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        return [], f"invalid media response: {exc}"


def run_official_discovery(bootstrap_limit: int) -> tuple[int, dict[str, int]]:
    payload = load_json(CANDIDATES, {"candidates": []})
    by_url = {
        normalize_url(item.get("url")): item for item in payload.get("candidates", [])
        if isinstance(item, dict) and normalize_url(item.get("url"))
    }
    registry = load_registry()
    ensure_coverage()
    batch_prefix = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    added = 0
    bootstrapped = 0

    for index, organization in enumerate(roster_entries(), 1):
        entry = registry_entry(registry, organization)
        roots = https_urls(entry.get("official_urls", []), limit=8)
        candidate_urls = https_urls(entry.get("bootstrap_candidate_urls", []), limit=8)
        bootstrap_candidates = [
            {"title": "", "url": url, "date": "", "summary": "", "organization_hint": organization["name"]}
            for url in candidate_urls
        ]
        if not roots:
            if bootstrapped >= bootstrap_limit:
                # Leave the status pending: it was not scanned, rather than
                # falsely declaring a zero-result crawl complete.
                continue
            bootstrapped += 1
            roots, bootstrap_candidates, error = bootstrap_sources(organization)
            store_sources(registry, organization, roots, bootstrap_candidates, error)
            if error:
                record_official_result(
                    organization["name"], [], status="failed",
                    batch=f"official-{batch_prefix}-{index:03d}",
                    source_urls=roots, scanned_urls=[], error=error,
                )
                continue
        candidates, source_urls, scanned_urls, error = crawl_organization(
            organization, roots, bootstrap_candidates,
        )
        if candidates:
            status = "found"
        elif scanned_urls:
            status = "no_qualifying_release"
        else:
            status = "failed"
            error = error or "official source could not be fetched"
        record_official_result(
            organization["name"], candidates, status=status,
            batch=f"official-{batch_prefix}-{index:03d}",
            source_urls=source_urls, scanned_urls=scanned_urls, error=error,
        )
        added += merge_candidates(by_url, candidates, "official web-project discovery")

    save_registry(registry)
    merged = sorted(by_url.values(), key=lambda item: (item.get("date", ""), item.get("title", "")), reverse=True)
    write_json(CANDIDATES, {"generated_at": utc_now(), "candidates": merged})
    coverage = ensure_coverage()
    summary = {
        "organizations": len(coverage["organizations"]),
        "found": sum(item["official_scan"]["status"] == "found" for item in coverage["organizations"]),
        "no_qualifying_release": sum(item["official_scan"]["status"] == "no_qualifying_release" for item in coverage["organizations"]),
        "pending": sum(item["official_scan"]["status"] == "pending" for item in coverage["organizations"]),
        "failed": sum(item["official_scan"]["status"] == "failed" for item in coverage["organizations"]),
        "bootstrapped_this_run": bootstrapped,
    }
    return added, summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("official", "media"), default="official")
    parser.add_argument("--bootstrap-limit", type=int, default=DEFAULT_BOOTSTRAP_LIMIT)
    args = parser.parse_args()
    if args.bootstrap_limit < 0:
        raise SystemExit("--bootstrap-limit must be non-negative")

    if args.mode == "media":
        payload = load_json(CANDIDATES, {"candidates": []})
        by_url = {
            normalize_url(item.get("url")): item for item in payload.get("candidates", [])
            if isinstance(item, dict) and normalize_url(item.get("url"))
        }
        items, error = call_media()
        if error:
            print(f"warning: media discovery skipped: {error}")
            return
        added = merge_candidates(by_url, items, "media-resolved official project discovery")
        merged = sorted(by_url.values(), key=lambda item: (item.get("date", ""), item.get("title", "")), reverse=True)
        write_json(CANDIDATES, {"generated_at": utc_now(), "candidates": merged})
        print(f"media_project_leads_added={added} candidates_total={len(merged)}")
        return

    added, summary = run_official_discovery(args.bootstrap_limit)
    print(f"official_coverage={json.dumps(summary, ensure_ascii=False, sort_keys=True)}")
    print(f"official_project_leads_added={added}")


if __name__ == "__main__":
    main()
