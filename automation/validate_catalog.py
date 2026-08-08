#!/usr/bin/env python3
import json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
reports=json.loads((root/"data/verified.json").read_text())
ids=[r["id"] for r in reports]
assert len(ids)==len(set(ids)), "duplicate report ids"
manifest=json.loads((root/"public/frameworks/manifest.json").read_text()).get("figures",[])
for item in manifest:
    asset=item.get("asset","")
    assert asset and (root/"public"/asset).is_file(), f"missing image asset: {asset}"
print(f"validated reports={len(reports)} figures={len(manifest)}")
