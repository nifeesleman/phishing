from __future__ import annotations

import unittest
import numpy as np

from app import create_app
from services.model_service import PhishingModelService
from utils.url_processing import prepare_url


class ModelServiceArtifactTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app({"TESTING": True})
        self.service = PhishingModelService(self.app.config)

    def test_service_loads_real_random_forest_bundle(self):
        self.service._ensure_loaded()

        self.assertEqual(type(self.service._model).__name__, "RandomForestClassifier")
        self.assertIsNone(self.service._vectorizer)
        self.assertEqual(self.service._input_mode, "url_feature_bundle")
        self.assertEqual(self.service._model.n_features_in_, 30)
        self.assertEqual(self.service._model.classes_.tolist(), [0, 1])

    def test_feature_extraction_mode_maps_negative_one_to_phishing(self):
        class _FakeFeatureModel:
            classes_ = np.array([-1, 1])
            n_features_in_ = 30

            def predict(self, features):
                return np.array([-1])

            def predict_proba(self, features):
                return np.array([[0.91, 0.09]])

        prepared_url = type(
            "PreparedUrlStub",
            (),
            {
                "normalized_url": "https://paypal.com/login",
                "heuristics": {"uses_https": True},
            },
        )()

        self.service._model = _FakeFeatureModel()
        self.service._vectorizer = None
        self.service._input_mode = "feature_extraction"
        self.service._extract_url_features = lambda prepared_url: np.zeros((1, 30))

        prediction = self.service.predict(prepared_url)

        self.assertEqual(prediction.api_result, "phishing")
        self.assertEqual(prediction.storage_result, "phishing")
        self.assertEqual(prediction.confidence, 0.91)

    def test_trusted_domain_override_marks_known_real_site_as_legit(self):
        class _FakeFeatureModel:
            classes_ = np.array([-1, 1])
            n_features_in_ = 30

            def predict(self, features):
                return np.array([-1])

            def predict_proba(self, features):
                return np.array([[0.99, 0.01]])

        prepared_url = prepare_url("https://chatgpt.com", self.app.config["BRAND_KEYWORDS"])

        self.service._model = _FakeFeatureModel()
        self.service._vectorizer = None
        self.service._input_mode = "feature_extraction"
        self.service._extract_url_features = lambda prepared_url: np.zeros((1, 30))

        prediction = self.service.predict(prepared_url)

        self.assertEqual(prediction.api_result, "legit")
        self.assertEqual(prediction.storage_result, "legitimate")
        self.assertEqual(prediction.confidence, 0.99)
        self.assertEqual(prediction.heuristics["trusted_domain"], "chatgpt.com")
        self.assertEqual(prediction.heuristics["trusted_domain_override"], "chatgpt.com")

    def test_trusted_domain_override_does_not_apply_to_lookalike_domain(self):
        class _FakeFeatureModel:
            classes_ = np.array([-1, 1])
            n_features_in_ = 30

            def predict(self, features):
                return np.array([-1])

            def predict_proba(self, features):
                return np.array([[0.99, 0.01]])

        prepared_url = prepare_url("https://chatgpt-security-check.com", self.app.config["BRAND_KEYWORDS"])

        self.service._model = _FakeFeatureModel()
        self.service._vectorizer = None
        self.service._input_mode = "feature_extraction"
        self.service._extract_url_features = lambda prepared_url: np.zeros((1, 30))

        prediction = self.service.predict(prepared_url)

        self.assertEqual(prediction.api_result, "phishing")
        self.assertEqual(prediction.storage_result, "phishing")
        self.assertIsNone(prediction.heuristics["trusted_domain"])

    def test_educational_domain_override_marks_academic_site_as_legit(self):
        class _FakeFeatureModel:
            classes_ = np.array([0, 1])
            n_features_in_ = 30

            def predict(self, features):
                return np.array([1])

            def predict_proba(self, features):
                return np.array([[0.04, 0.96]])

        prepared_url = prepare_url("https://amu.edu.et", self.app.config["BRAND_KEYWORDS"])

        self.service._model = _FakeFeatureModel()
        self.service._vectorizer = None
        self.service._input_mode = "feature_extraction"
        self.service._extract_url_features = lambda prepared_url: np.zeros((1, 30))

        prediction = self.service.predict(prepared_url)

        self.assertEqual(prediction.api_result, "legit")
        self.assertEqual(prediction.storage_result, "legitimate")
        self.assertEqual(prediction.confidence, 0.98)
        self.assertEqual(prediction.heuristics["educational_domain"], "edu.et")
        self.assertEqual(prediction.heuristics["educational_domain_override"], "edu.et")

    def test_educational_domain_override_does_not_apply_to_lookalike_domain(self):
        class _FakeFeatureModel:
            classes_ = np.array([0, 1])
            n_features_in_ = 30

            def predict(self, features):
                return np.array([1])

            def predict_proba(self, features):
                return np.array([[0.04, 0.96]])

        prepared_url = prepare_url("https://amu.edu.et.evil.com", self.app.config["BRAND_KEYWORDS"])

        self.service._model = _FakeFeatureModel()
        self.service._vectorizer = None
        self.service._input_mode = "feature_extraction"
        self.service._extract_url_features = lambda prepared_url: np.zeros((1, 30))

        prediction = self.service.predict(prepared_url)

        self.assertEqual(prediction.api_result, "phishing")
        self.assertEqual(prediction.storage_result, "phishing")
        self.assertIsNone(prediction.heuristics["educational_domain"])
        self.assertNotIn("educational_domain_override", prediction.heuristics)

    def test_brand_impersonation_override_marks_lookalike_as_phishing(self):
        class _FakeFeatureModel:
            classes_ = np.array([-1, 1])
            n_features_in_ = 30

            def predict(self, features):
                return np.array([1])

            def predict_proba(self, features):
                return np.array([[0.37, 0.63]])

        prepared_url = prepare_url("https://secure-paypal-login.com", self.app.config["BRAND_KEYWORDS"])

        self.service._model = _FakeFeatureModel()
        self.service._vectorizer = None
        self.service._input_mode = "feature_extraction"
        self.service._extract_url_features = lambda prepared_url: np.zeros((1, 30))

        prediction = self.service.predict(prepared_url)

        self.assertEqual(prediction.api_result, "phishing")
        self.assertEqual(prediction.storage_result, "phishing")
        self.assertGreaterEqual(prediction.confidence, 0.97)
        self.assertEqual(
            prediction.heuristics["brand_impersonation_override"]["matched_brands"],
            ["paypal"],
        )
        self.assertIn(
            "login",
            prediction.heuristics["brand_impersonation_override"]["suspicious_terms"],
        )

    def test_low_signal_override_marks_portfolio_style_url_as_legit(self):
        class _FakeFeatureModel:
            classes_ = np.array([0, 1])
            n_features_in_ = 30

            def predict(self, features):
                return np.array([1])

            def predict_proba(self, features):
                return np.array([[0.36, 0.64]])

        prepared_url = prepare_url("https://myportfolio.com", self.app.config["BRAND_KEYWORDS"])

        self.service._model = _FakeFeatureModel()
        self.service._vectorizer = None
        self.service._input_mode = "feature_extraction"
        self.service._extract_url_features = lambda prepared_url: np.zeros((1, 30))

        prediction = self.service.predict(prepared_url)

        self.assertEqual(prediction.api_result, "legit")
        self.assertEqual(prediction.storage_result, "legitimate")
        self.assertEqual(prediction.confidence, 0.75)
        self.assertEqual(
            prediction.heuristics["low_signal_override"]["reason"],
            "phishing prediction had low confidence and no phishing indicators",
        )

    def test_low_signal_override_does_not_apply_to_non_brand_suspicious_url(self):
        class _FakeFeatureModel:
            classes_ = np.array([0, 1])
            n_features_in_ = 30

            def predict(self, features):
                return np.array([1])

            def predict_proba(self, features):
                return np.array([[0.38, 0.62]])

        prepared_url = prepare_url("https://free-crypto-airdrop.xyz/claim", self.app.config["BRAND_KEYWORDS"])

        self.service._model = _FakeFeatureModel()
        self.service._vectorizer = None
        self.service._input_mode = "feature_extraction"
        self.service._extract_url_features = lambda prepared_url: np.zeros((1, 30))

        prediction = self.service.predict(prepared_url)

        self.assertEqual(prediction.api_result, "phishing")
        self.assertEqual(prediction.storage_result, "phishing")
        self.assertNotIn("low_signal_override", prediction.heuristics)

    def test_real_artifact_treats_chatgpt_as_legit(self):
        prepared_url = prepare_url("https://chatgpt.com", self.app.config["BRAND_KEYWORDS"])

        prediction = self.service.predict(prepared_url)

        self.assertEqual(prediction.api_result, "legit")
        self.assertEqual(prediction.storage_result, "legitimate")
        self.assertEqual(prediction.heuristics["trusted_domain"], "chatgpt.com")

    def test_real_artifact_treats_secure_paypal_login_as_phishing(self):
        prepared_url = prepare_url("https://secure-paypal-login.com", self.app.config["BRAND_KEYWORDS"])

        prediction = self.service.predict(prepared_url)

        self.assertEqual(prediction.api_result, "phishing")
        self.assertEqual(prediction.storage_result, "phishing")
        self.assertIn("paypal", prediction.heuristics["matched_brands"])
        self.assertIn("login", prediction.heuristics["suspicious_terms"])

    def test_real_artifact_treats_github_auth_check_as_phishing(self):
        prepared_url = prepare_url("https://github-auth-check.com", self.app.config["BRAND_KEYWORDS"])

        prediction = self.service.predict(prepared_url)

        self.assertEqual(prediction.api_result, "phishing")
        self.assertEqual(prediction.storage_result, "phishing")
        self.assertIn("github", prediction.heuristics["matched_brands"])
        self.assertIn("auth", prediction.heuristics["suspicious_terms"])

    def test_real_artifact_treats_portfolio_style_domain_as_legit(self):
        prepared_url = prepare_url("https://myportfolio.com", self.app.config["BRAND_KEYWORDS"])

        prediction = self.service.predict(prepared_url)

        self.assertEqual(prediction.api_result, "legit")
        self.assertEqual(prediction.storage_result, "legitimate")

    def test_real_artifact_treats_educational_domain_as_legit(self):
        prepared_url = prepare_url("https://amu.edu.et", self.app.config["BRAND_KEYWORDS"])

        prediction = self.service.predict(prepared_url)

        self.assertEqual(prediction.api_result, "legit")
        self.assertEqual(prediction.storage_result, "legitimate")
