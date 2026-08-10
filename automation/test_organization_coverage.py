#!/usr/bin/env python3
"""No-network tests for the per-organization coverage ledger."""

import json
import tempfile
import unittest
from pathlib import Path

from organization_coverage import ensure_coverage, record_official_batch, validate_coverage


class CoverageLedgerTests(unittest.TestCase):
    def test_initialization_and_batch_recording(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            roster_path = root / "company_roster.json"
            coverage_path = root / "organization_coverage.json"
            roster_path.write_text(json.dumps([
                {"name": "甲公司 / Alpha Robotics", "region": "China"},
                {"name": "Beta Robotics", "region": "International"},
            ], ensure_ascii=False), encoding="utf-8")
            coverage = ensure_coverage(roster_path, coverage_path, "2026-08-10T00:00:00+00:00")
            validate_coverage(coverage, roster_path)
            coverage = record_official_batch(
                ["甲公司 / Alpha Robotics"],
                [{"organization_hint": "Alpha Robotics", "title": "Alpha VLA", "summary": "policy", "url": "https://example.com/alpha"}],
                status="completed", batch="official-1", roster_path=roster_path, coverage_path=coverage_path,
                timestamp="2026-08-10T00:01:00+00:00",
            )
            alpha, beta = coverage["organizations"]
            self.assertEqual(alpha["official_scan"]["status"], "completed")
            self.assertEqual(alpha["official_scan"]["candidate_count"], 1)
            self.assertEqual(beta["official_scan"]["status"], "pending")
            validate_coverage(coverage, roster_path)


if __name__ == "__main__":
    unittest.main()
