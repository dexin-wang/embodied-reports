#!/usr/bin/env python3
"""No-network tests for direct per-organization official-source discovery."""

import http.client
import unittest
from unittest.mock import patch

import discover_official_projects as discovery


class OfficialDiscoveryTests(unittest.TestCase):
    def test_normalize_url_removes_fragment_and_rejects_non_https(self) -> None:
        self.assertEqual(
            discovery.normalize_url("https://Example.com/news#top"),
            "https://example.com/news",
        )
        self.assertEqual(discovery.normalize_url("http://example.com"), "")
        self.assertEqual(
            discovery.normalize_url("https://example.com/news/company news/"),
            "https://example.com/news/company%20news/",
        )
        self.assertEqual(discovery.normalize_url("not a url"), "")

    def test_crawl_expands_only_the_organization_official_host(self) -> None:
        root = "https://alpha.example.com/"
        project = "https://alpha.example.com/projects/alpha-vla"
        documents = {
            root: {
                "url": root, "title": "Alpha Robotics",
                "description": "", "dates": [],
                "links": [project, "https://untrusted.example.org/vla"],
                "feed_urls": [],
            },
            project: {
                "url": project, "title": "Alpha VLA Foundation Model",
                "description": "A robot policy for manipulation.",
                "dates": ["2026-06-14"],
                "links": [], "feed_urls": [],
            },
        }
        with patch.object(discovery, "fetch_document", side_effect=lambda url: documents[url]), \
             patch.object(discovery, "sitemap_links", return_value=[]):
            candidates, source_urls, scanned_urls, error = discovery.crawl_organization(
                {"id": "alpha", "name": "Alpha Robotics", "region": "International"},
                [root], [],
            )
        self.assertIsNone(error)
        self.assertEqual(source_urls, [root])
        self.assertEqual(scanned_urls, [root, project])
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["url"], project)
        self.assertEqual(candidates[0]["organization_hint"], "Alpha Robotics")

    def test_malformed_external_link_cannot_abort_an_organization_crawl(self) -> None:
        root = "https://alpha.example.com/"
        with patch.object(
            discovery, "fetch_document",
            side_effect=http.client.InvalidURL("URL can't contain control characters"),
        ), patch.object(discovery, "sitemap_links", return_value=[]):
            candidates, source_urls, scanned_urls, error = discovery.crawl_organization(
                {"id": "alpha", "name": "Alpha Robotics", "region": "International"},
                [root], [],
            )
        self.assertEqual(candidates, [])
        self.assertEqual(source_urls, [root])
        self.assertEqual(scanned_urls, [])
        self.assertIn("InvalidURL", error)

    def test_hardware_only_page_cannot_become_candidate(self) -> None:
        document = {
            "url": "https://alpha.example.com/news/new-humanoid",
            "title": "Our New Humanoid Robot",
            "description": "A new robot body product.",
            "dates": ["2026-02-01"], "links": [], "feed_urls": [],
        }
        item = discovery.candidate_from_document(
            {"id": "alpha", "name": "Alpha Robotics", "region": "International"},
            document, {},
        )
        self.assertIsNone(item)

    def test_bootstrap_candidate_requires_a_valid_date(self) -> None:
        document = {
            "url": "https://alpha.example.com/projects/alpha-vla",
            "title": "Alpha VLA",
            "description": "Robot policy", "dates": [], "links": [], "feed_urls": [],
        }
        item = discovery.candidate_from_document(
            {"id": "alpha", "name": "Alpha Robotics", "region": "International"},
            document,
            {document["url"]: {
                "title": "Alpha VLA", "url": document["url"],
                "date": "2026-01-15", "summary": "Official policy release",
                "organization_hint": "Alpha Robotics",
            }},
        )
        self.assertEqual(item["date"], "2026-01-15")


if __name__ == "__main__":
    unittest.main()
