#!/usr/bin/env python3
"""No-network tests for the per-organization direct-crawl coverage ledger."""

import json
import tempfile
import unittest
from pathlib import Path

from organization_coverage import (
    coverage_summary,
    ensure_coverage,
    record_official_result,
    validate_coverage,
)


class CoverageLedgerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        root = Path(self.directory.name)
        self.roster_path = root / "company_roster.json"
        self.coverage_path = root / "organization_coverage.json"
        self.roster_path.write_text(json.dumps([
            {"name": "甲公司 / Alpha Robotics", "region": "China"},
            {"name": "Beta Robotics", "region": "International"},
        ], ensure_ascii=False), encoding="utf-8")

    def test_each_result_is_recorded_for_one_direct_crawl(self) -> None:
        coverage = ensure_coverage(self.roster_path, self.coverage_path, "2026-08-10T00:00:00+00:00")
        validate_coverage(coverage, self.roster_path)

        coverage = record_official_result(
            "甲公司 / Alpha Robotics",
            [{"url": "https://alpha.example.com/project", "title": "Alpha VLA"}],
            status="found", batch="official-001",
            source_urls=["https://alpha.example.com/"],
            scanned_urls=["https://alpha.example.com/", "https://alpha.example.com/project"],
            roster_path=self.roster_path, coverage_path=self.coverage_path,
            timestamp="2026-08-10T00:01:00+00:00",
        )
        coverage = record_official_result(
            "Beta Robotics", [], status="no_qualifying_release", batch="official-002",
            source_urls=["https://beta.example.com/"],
            scanned_urls=["https://beta.example.com/"],
            roster_path=self.roster_path, coverage_path=self.coverage_path,
            timestamp="2026-08-10T00:02:00+00:00",
        )
        alpha, beta = coverage["organizations"]
        self.assertEqual(alpha["official_scan"]["status"], "found")
        self.assertEqual(alpha["official_scan"]["candidate_count"], 1)
        self.assertEqual(beta["official_scan"]["status"], "no_qualifying_release")
        self.assertEqual(coverage_summary(coverage)["with_candidates"], 1)
        validate_coverage(coverage, self.roster_path)

    def test_legacy_batched_zero_result_is_reset_to_pending(self) -> None:
        self.coverage_path.write_text(json.dumps({
            "schema_version": 1,
            "organizations": [{
                "id": "ignored", "name": "not-used",
                "official_scan": {"status": "completed", "candidate_count": 0},
            }],
        }), encoding="utf-8")
        coverage = ensure_coverage(self.roster_path, self.coverage_path, "2026-08-10T00:00:00+00:00")
        self.assertTrue(all(
            item["official_scan"]["status"] == "pending"
            for item in coverage["organizations"]
        ))
        validate_coverage(coverage, self.roster_path)


if __name__ == "__main__":
    unittest.main()
