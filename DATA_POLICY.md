# Data policy

Embodied Reports is an automatically maintained index of influential embodied-robotics project releases, not an arXiv paper feed.

## Inclusion

A public entry must be dated 2025 or later and directly concern embodied intelligence or physical robots: a consequential model, system, dataset, benchmark, or major version release. Conference or journal acceptance, open source, and a PDF are not requirements.

Every automatically published entry must pass all three hard gates:

1. An official project page, organization announcement, or official university/research-lab project page exists. arXiv alone is never sufficient.
2. The responsible company, university, or named research institute is explicit on an official source. Ambiguous labels such as `Research team` are rejected.
3. Public discussion is found on at least two distinct social platforms, with at least one independent source. The corresponding evidence URLs are retained on the card.

## Evidence

Facts come from an official technical report, project page, repository, model card, or organization announcement. Missing values are not inferred. Chinese institutions are shown as `中文 / English` when an established bilingual name is available.

## Automation

`automation/discover.py` and `automation/discover_official_projects.py` find leads; they never publish cards directly. `automation/verify_reports.py` uses web search to enforce the three inclusion gates and writes only accepted records to `data/verified.json`. There is no manual approval queue.

`automation/candidates.json` and `automation/verification_audit.json` preserve the automated decision, source evidence, and rejection reason. A temporary source outage preserves the existing candidate snapshot and verified index.

For a verified entry with an accessible public PDF, the job extracts an early source figure whose caption indicates a framework, architecture, method, pipeline, or system overview. The site displays this original crop with its source attribution; it never redraws the diagram.

`OPENAI_API_KEY` is required for official-source and impact verification. The workflow fails visibly when the key is unavailable or invalid rather than silently publishing unverified papers.
