# Embodied Reports

A fast, continuously updated index of influential embodied-intelligence technical reports released since 2025, with special attention to research-company releases.

- Live site: https://embodied-reports.cherry-tick-5048.chatgpt.site
- GitHub Pages: https://dexin-wang.github.io/embodied-reports/
- Repository: https://github.com/dexin-wang/embodied-reports

## What it tracks

- Robot foundation models and VLAs
- Humanoid intelligence and whole-body systems
- Robot world models and video-action models
- Dexterous, force and tactile intelligence
- Influential datasets, benchmarks and embodied systems

Publication venue is not an inclusion requirement. Primary-source evidence is.

## Local development

```bash
npm ci
npm run dev
```

## Automated discovery

`automation/discover.py` queries public research feeds, scores candidates with transparent rules, and writes high-confidence entries to `data/discovered.json`. GitHub Actions runs discovery daily and link validation weekly.

The initial pipeline uses no private API key. Search-engine and structured LLM enrichment can be enabled later through repository secrets without exposing credentials.

See [DATA_POLICY.md](DATA_POLICY.md) for inclusion and verification rules.

## Publish this source repository

The production website is deployed separately from GitHub. GitHub Actions in this repository refresh report candidates and validates primary-source links. No API key is required for the conservative public-feed discovery stage.

The `Deploy GitHub Pages` workflow builds a static export after every push to
`main` and after every successful discovery run. Enable GitHub Pages with
`Settings → Pages → Source → GitHub Actions` once after pushing the repository.

To push the source into a new empty repository:

```bash
git init -b main
git add .
git commit -m "Initial release"
git remote add origin git@github.com:dexin-wang/embodied-reports.git
git push -u origin main
```
