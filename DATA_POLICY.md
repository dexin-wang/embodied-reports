# Data policy

Embodied Reports prioritizes primary sources and fully automated publication.

## Inclusion

A public entry must be dated 2025 or later, directly concern embodied intelligence or physical robots, and describe a consequential model, system, dataset, benchmark, or major version release. Conference or journal acceptance is not required.

## Evidence

Facts should come from an official technical report, project page, repository, model card, or organization announcement. Missing values remain unreported; they are never inferred from adjacent models.

## Automation

The discovery job searches public feeds, removes duplicates, validates a dated primary-source record, and applies a transparent relevance score. Every entry above the configured threshold is published directly—there is no manual approval queue. `automation/candidates.json` records every score and rule match for auditability.

The stable catalog retains published entries across feed failures. A discovery run with fewer than the configured minimum candidates preserves the catalog and the last valid discovery snapshot instead of replacing them with an empty file.

For entries with an accessible public PDF, the job downloads the source and extracts an early figure whose caption indicates a framework, architecture, method, pipeline, or system overview. The site displays this original crop with an attribution to its source PDF; it never redraws the method diagram.

Automated summaries and organization labels are descriptive, not endorsements. Organization is left as “Research team” unless it can be identified from a model name in the report title; the source material remains authoritative.

When the optional `OPENAI_API_KEY` repository secret is configured, `automation/enrich_reports.py` sends the relevant source PDF/webpage text to the OpenAI Responses API and requires a structured, source-grounded dossier: bilingual organization labels, institution type, technical highlights, capabilities, and reported metrics. It does not run without that secret.
