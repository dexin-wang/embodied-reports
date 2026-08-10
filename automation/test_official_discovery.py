#!/usr/bin/env python3
"""No-network tests for organization-batched official discovery."""

import json
import math
import unittest
from pathlib import Path

import discover_official_projects as discovery


class OfficialDiscoveryTests(unittest.TestCase):
    def test_every_roster_entry_is_assigned_to_one_batch(self) -> None:
        roster_path = Path(__file__).with_name("company_roster.json")
        previous = discovery.COMPANY_ROSTER
        self.addCleanup(setattr, discovery, "COMPANY_ROSTER", previous)
        discovery.COMPANY_ROSTER = roster_path
        roster = json.loads(roster_path.read_text(encoding="utf-8"))
        topics = discovery.official_topics()
        assigned = [name for _, names in topics for name in names]
        self.assertEqual(assigned, [item["name"] for item in roster])
        self.assertEqual(len(topics), len(discovery.TOPICS) + math.ceil(len(roster) / discovery.COMPANY_BATCH_SIZE))


if __name__ == "__main__":
    unittest.main()
