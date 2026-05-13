from __future__ import annotations

import unittest

from utils.errors import ValidationError
from utils.url_processing import prepare_url


class UrlProcessingTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.brand_keywords = {"paypal": "PayPal"}

    def test_rejects_single_label_hostname(self):
        with self.assertRaisesRegex(
            ValidationError, "URL hostname must be a fully qualified domain or IP address"
        ):
            prepare_url("okay", self.brand_keywords)

    def test_rejects_hostname_with_whitespace(self):
        with self.assertRaisesRegex(ValidationError, "URL hostname is invalid"):
            prepare_url("not correct", self.brand_keywords)

    def test_rejects_malformed_bracketed_hostname(self):
        with self.assertRaisesRegex(ValidationError, "URL hostname is invalid"):
            prepare_url("https://[.]/login", self.brand_keywords)

    def test_accepts_fully_qualified_domain(self):
        prepared = prepare_url("secure-paypal-login.com", self.brand_keywords)

        self.assertEqual(prepared.hostname, "secure-paypal-login.com")
        self.assertEqual(prepared.normalized_url, "https://secure-paypal-login.com/")
        self.assertEqual(prepared.heuristics["matched_brands"], ["paypal"])
        self.assertIn("secure", prepared.heuristics["suspicious_terms"])
        self.assertIn("login", prepared.heuristics["suspicious_terms"])

    def test_accepts_ip_address_hostname(self):
        prepared = prepare_url("http://192.168.1.1/verify", self.brand_keywords)

        self.assertEqual(prepared.hostname, "192.168.1.1")

    def test_normalizes_www_subdomain_to_canonical_hostname(self):
        prepared = prepare_url("https://www.phishing.com", self.brand_keywords)

        self.assertEqual(prepared.hostname, "phishing.com")
        self.assertEqual(prepared.normalized_url, "https://phishing.com/")
