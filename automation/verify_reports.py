#!/usr/bin/env python3
"""Publish only influential embodied-robotics projects with external evidence.

Candidate feeds can contain ordinary papers.  This verifier uses the OpenAI
Responses API web-search tool to find an official project release, resolve the
responsible company/university/research institute, and require discussion on at
least two distinct social platforms.  Nothing is placed in `data/verified.json`
unless all of those conditions are evidenced in the response.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "automation" / "sources.json").read_text())
CANDIDATES = ROOT / "automation" / "candidates.json"
VERIFIED = ROOT / "data" / "verified.json"
AUDIT = ROOT / "automation" / "verification_audit.json"
API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = os.getenv("OPENAI_VERIFIER_MODEL", "gpt-5.6")

SOCIAL_DOMAINS = {
    "x.com": "X", "twitter.com": "X", "linkedin.com": "LinkedIn",
    "youtube.com": "YouTube", "youtu.be": "YouTube", "bilibili.com": "Bilibili",
    "weixin.qq.com": "WeChat", "mp.weixin.qq.com": "WeChat", "zhihu.com": "Zhihu",
    "reddit.com": "Reddit", "facebook.com": "Facebook", "instagram.com": "Instagram",
}

SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "include": {"type": "boolean"},
        "reason": {"type": "string"},
        "official_project_url": {"type": "string"},
        "official_organization_url": {"type": "string"},
        "organization_en": {"type": "string"},
        "organization_zh": {"type": "string"},
        "organization_kind": {"type": "string", "enum": ["Company", "University", "Research Lab"]},
        "fields": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 4},
        "summary_zh": {"type": "string"},
        "key_points": {"type": "array", "items": {"type": "string"}, "minItems": 3, "maxItems": 5},
        "capabilities": {"type": "array", "items": {"type": "string"}, "minItems": 2, "maxItems": 4},
        "metrics": {
            "type": "array",
            "items": {
                "type": "object", "additionalProperties": False,
                "properties": {"label": {"type": "string"}, "value": {"type": "string"}, "note": {"type": "string"}},
                "required": ["label", "value", "note"],
            }, "minItems": 1, "maxItems": 4,
        },
        "open_source": {"type": "boolean"},
        "social_evidence": {
            "type": "array",
            "items": {
                "type": "object", "additionalProperties": False,
                "properties": {"platform": {"type": "string"}, "url": {"type": "string"}, "independent": {"type": "boolean"}},
                "required": ["platform", "url", "independent"],
            }, "minItems": 0, "maxItems": 5,
        },
    },
    "required": [
        "include", "reason", "official_project_url", "official_organization_url", "organization_en", "organization_zh",
        "organization_kind", "fields", "summary_zh", "key_points", "capabilities", "metrics", "open_source", "social_evidence",
    ],
}


def slug(title: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:48]
    return f"{normalized or 'report'}-{hashlib.sha1(title.encode()).hexdigest()[:7]}"


def call_model(candidate: dict) -> dict:
    prompt = f"""You curate a strict public index of influential embodied-robotics technical projects released since 2025.
Use web search before deciding. A candidate is eligible ONLY if all conditions are met:
1. It is materially about physical robots / embodied intelligence (not merely autonomous driving, generic vision, or a normal ML paper).
2. A dedicated official project page, official organization announcement, or official research-lab project page exists. arXiv alone is never official-project evidence.
3. A specific company, university, or named research institute is explicitly responsible. Never use vague labels such as 'Research team'.
4. There is public discussion on at least TWO distinct social platforms. At least one must be by an account/publication not controlled by the responsible organization.
5. Do not require open source, a paper, or a PDF.

If any condition cannot be supported by accessible web sources, set include=false and state the missing condition in reason. Do not guess URLs, affiliations, dates, metrics, or social evidence.
For a Chinese organization, use its established Chinese and English names; otherwise organization_zh is an empty string.
Write summary_zh, key_points, capabilities and metrics in concise Chinese based only on the official page/report. For metrics without a reliable numerical comparison, state the exact qualitative capability rather than inventing a number.
Allowed fields: Vision-language-action, Humanoid intelligence, Whole-body control, World models, Robot manipulation, Dexterous manipulation, Tactile intelligence, Data & benchmarks, Robot systems, Embodied AI.

CANDIDATE TITLE: {candidate['title']}
ARXIV/PRIMARY LEAD: {candidate['url']}
DATE: {candidate['date']}
AUTHORS: {', '.join(candidate.get('authors', [])[:12])}
ABSTRACT: {candidate['summary'][:6000]}
"""
    payload = {
        "model": MODEL,
        "reasoning": {"effort": "low"},
        "tools": [{"type": "web_search", "search_context_size": "medium"}],
        "include": ["web_search_call.action.sources"],
        "input": [{"role": "user", "content": [{"type": "input_text", "text": prompt}]}],
        "text": {"format": {"type": "json_schema", "name": "embodied_project_verdict", "strict": True, "schema": SCHEMA}},
    }
    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        result = json.loads(response.read())
    return json.loads(result["output_text"])


def is_url(url: str) -> bool:
    return url.startswith("https://") and bool(urlparse(url).netloc)


def social_platform(url: str) -> str | None:
    host = urlparse(url).netloc.lower().removeprefix("www.")
    return next((label for domain, label in SOCIAL_DOMAINS.items() if host == domain or host.endswith(f".{domain}")), None)


def valid_verdict(verdict: dict) -> tuple[bool, str, list[dict]]:
    if not verdict["include"]:
        return False, verdict["reason"], []
    if not all((verdict["organization_en"].strip(), verdict["official_project_url"].strip(), verdict["official_organization_url"].strip())):
        return False, "missing named institution or official source", []
    if verdict["organization_en"].strip().lower() in {"research team", "unknown", "n/a"}:
        return False, "generic institution label", []
    if not all(is_url(verdict[key]) for key in ("official_project_url", "official_organization_url")):
        return False, "invalid official URL", []
    if "arxiv.org" in urlparse(verdict["official_project_url"]).netloc.lower():
        return False, "arXiv alone is not an official project page", []
    evidence = []
    for item in verdict["social_evidence"]:
        platform = social_platform(item["url"])
        if platform:
            evidence.append({**item, "platform": platform})
    platforms = {item["platform"] for item in evidence}
    if len(platforms) < 2 or not any(item["independent"] for item in evidence):
        return False, "insufficient independent multi-platform social evidence", []
    return True, "", evidence


def report_from(candidate: dict, verdict: dict, evidence: list[dict]) -> dict:
    chinese, english = verdict["organization_zh"].strip(), verdict["organization_en"].strip()
    organization = f"{chinese} / {english}" if chinese else english
    links = [
        {"label": "Project", "url": verdict["official_project_url"]},
        {"label": "Evidence", "url": verdict["official_organization_url"]},
        {"label": "Report", "url": candidate["url"]},
    ]
    seen = {link["url"] for link in links}
    for item in evidence:
        if item["url"] not in seen:
            links.append({"label": "Evidence", "url": item["url"]})
            seen.add(item["url"])
    return {
        "id": slug(candidate["title"]), "title": candidate["title"], "organization": organization,
        "organizationKind": verdict["organization_kind"], "date": candidate["date"], "year": int(candidate["date"][:4]),
        "summary": verdict["summary_zh"], "tags": verdict["fields"], "fields": verdict["fields"],
        "featured": len(evidence) >= 3, "openSource": verdict["open_source"], "verification": "Automated",
        "details": {"keyPoints": verdict["key_points"], "capabilities": verdict["capabilities"], "metrics": verdict["metrics"]},
        "links": links,
    }


def main() -> None:
    if not API_KEY:
        raise SystemExit("OPENAI_API_KEY is required for strict official-source verification")
    candidates = json.loads(CANDIDATES.read_text()).get("candidates", []) if CANDIDATES.exists() else []
    verified = json.loads(VERIFIED.read_text()) if VERIFIED.exists() else []
    audit = json.loads(AUDIT.read_text()) if AUDIT.exists() else {}
    verified_by_id = {item["id"]: item for item in verified}
    max_per_run = int(CONFIG.get("max_verifications_per_run", 30))
    todo = [item for item in candidates if slug(item["title"]) not in audit][:max_per_run]
    if not todo:
        print(f"verification cache is current: verified={len(verified_by_id)}")
        return
    def check(candidate: dict) -> tuple[dict, dict | None, Exception | None]:
        try:
            return candidate, call_model(candidate), None
        except urllib.error.HTTPError as exc:
            # Authentication, model access and schema errors must fail the run
            # visibly rather than making the index look silently up to date.
            body = exc.read().decode("utf-8", "ignore")[:500]
            raise RuntimeError(f"OpenAI request failed ({exc.code}): {body}") from exc
        except (urllib.error.URLError, TimeoutError, KeyError, ValueError, json.JSONDecodeError) as exc:
            return candidate, None, exc

    workers = min(int(CONFIG.get("verification_workers", 4)), len(todo))
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = [pool.submit(check, candidate) for candidate in todo]
        checked = [future.result() for future in as_completed(futures)]

    for index, (candidate, verdict, error) in enumerate(checked, 1):
        item_id = slug(candidate["title"])
        if error:
            print(f"warning: verification retry later for {candidate['title']}: {error}")
            continue
        try:
            accepted, reason, evidence = valid_verdict(verdict)
            audit[item_id] = {
                "checked_at": datetime.now(timezone.utc).isoformat(), "title": candidate["title"],
                "accepted": accepted, "reason": reason or verdict["reason"], "verdict": verdict,
            }
            if accepted:
                verified_by_id[item_id] = report_from(candidate, verdict, evidence)
            print(f"verified={index}/{len(todo)} accepted={accepted} {candidate['title']}")
        except (KeyError, ValueError, json.JSONDecodeError) as exc:
            # Do not cache malformed/transient responses: a later scheduled run retries them.
            print(f"warning: verification retry later for {candidate['title']}: {exc}")
            continue
        AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n")
        VERIFIED.write_text(json.dumps(sorted(verified_by_id.values(), key=lambda x: (x["date"], x["title"]), reverse=True), ensure_ascii=False, indent=2) + "\n")
    print(f"verified_total={len(verified_by_id)} checked_this_run={len(todo)}")


if __name__ == "__main__":
    main()
