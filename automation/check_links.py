#!/usr/bin/env python3
import re
import urllib.request
from pathlib import Path

root = Path(__file__).resolve().parents[1]
source = (root / "app/reports.ts").read_text()
urls = sorted(set(re.findall(r'url: "(https://[^\"]+)"', source)))
failures = []
for url in urls:
    try:
        request = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "EmbodiedReports/0.1"})
        with urllib.request.urlopen(request, timeout=20) as response:
            if response.status >= 400:
                failures.append((url, response.status))
    except Exception as exc:
        failures.append((url, str(exc)))
if failures:
    print("Links requiring review:")
    for url, reason in failures:
        print(f"- {url}: {reason}")
    raise SystemExit(1)
print(f"Checked {len(urls)} links")
