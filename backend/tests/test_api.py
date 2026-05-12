from __future__ import annotations

import unittest

from app import create_app
from services.model_service import ModelPrediction
from utils.auth import AuthenticatedUser
from utils.errors import AuthorizationError, ValidationError


class FakeVerifier:
    def __init__(self, user: AuthenticatedUser) -> None:
        self._user = user

    def require_user(self) -> AuthenticatedUser:
        return self._user

    def require_admin(self) -> AuthenticatedUser:
        if not self._user.is_admin:
            raise AuthorizationError("admin only")
        return self._user


class FakeModelService:
    def predict(self, prepared_url):
        return ModelPrediction(
            storage_result="phishing",
            api_result="phishing",
            confidence=0.91,
            model_name="DecisionTreeClassifier",
            model_version="test-model",
            heuristics=prepared_url.heuristics,
        )


class FakeScanService:
    def __init__(self) -> None:
        self.saved_payloads = []

    def scan_url(self, user, raw_url, *, persist_mode="blocking"):
        if str(raw_url).startswith("ftp://"):
            raise ValidationError("Only http and https URLs are supported")
        self.saved_payloads.append({"user_id": user.user_id, "url": raw_url, "persist_mode": persist_mode})
        if str(raw_url) == "https://down.example.com":
            return {
                "result": "unavailable",
                "confidence": None,
                "model_name": None,
                "model_version": None,
                "message": "The website appears to be down or unreachable right now.",
            }
        return {
            "result": "phishing",
            "confidence": 0.91,
            "model_name": "GradientBoostingClassifier",
            "model_version": "test-model",
        }

    def get_history(self, user, limit, offset, **kwargs):
        return {
            "items": [
                {
                    "id": "scan-1",
                    "user_id": user.user_id,
                    "result": "phishing",
                    "confidence": 0.91,
                    "created_at": "2025-01-01T00:00:00+00:00",
                    "limit_seen": limit,
                    "offset_seen": offset,
                    "received_filters": kwargs,
                }
            ],
            "total": 1,
            "pagination": {"limit": limit, "offset": offset},
        }

    def get_admin_stats(self, *, range_value, include_auth_history=False):
        response = {
            "overview": {
                "total_scans": 10,
                "phishing_count": 4,
                "legit_count": 6,
                "unique_users": 3,
                "avg_confidence": 0.74,
            },
            "activity": [],
            "top_risky_urls": [],
            "recent_scans": [],
        }
        if include_auth_history:
            response["auth_history"] = [{"email": "admin@example.com", "is_admin": True}]
        return response

    def get_admin_user_history(self, user_id):
        return {
            "items": [
                {
                    "id": "scan-1",
                    "user_id": user_id,
                    "user_email": "user@example.com",
                    "url": "https://example.com/login",
                    "result": "phishing",
                    "confidence": 0.91,
                    "created_at": "2025-01-01T00:00:00+00:00",
                },
                {
                    "id": "scan-2",
                    "user_id": user_id,
                    "user_email": "user@example.com",
                    "url": "https://example.com",
                    "result": "legit",
                    "confidence": 0.12,
                    "created_at": "2025-01-02T00:00:00+00:00",
                },
            ],
            "total": 2,
        }

    def user_is_admin(self, user_id):
        return False


class FakeAuthService:
    def sign_up(self, *, email, password):
        if "@" not in email:
            raise ValidationError("Enter a valid email address")
        if len(password) < 6:
            raise ValidationError("Password must be at least 6 characters")
        return {"user": {"id": "user-456", "email": email}}


class ApiTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app({"TESTING": True})
        self.client = self.app.test_client()
        with self.app.app_context():
            self.app.extensions["auth_service"] = FakeAuthService()

    def _inject_services(self, *, is_admin: bool = False) -> FakeScanService:
        with self.app.app_context():
            user = AuthenticatedUser(
                user_id="user-123",
                email="admin@example.com" if is_admin else "user@example.com",
                claims={"sub": "user-123"},
                is_admin=is_admin,
                access_token="token",
            )
            self.app.extensions["jwt_verifier"] = FakeVerifier(user)
            scan_service = FakeScanService()
            self.app.extensions["scan_service"] = scan_service
            return scan_service

    def test_scan_endpoint_returns_prediction(self):
        scan_service = self._inject_services()

        response = self.client.post(
            "/scan",
            json={"url": "paypal.com/login"},
            headers={"Authorization": "Bearer token"},
        )

        self.assertEqual(response.status_code, 201)
        payload = response.get_json()
        self.assertEqual(payload["result"], "phishing")
        self.assertEqual(payload["confidence"], 0.91)
        self.assertEqual(len(scan_service.saved_payloads), 1)

    def test_predict_endpoint_returns_prediction(self):
        scan_service = self._inject_services()

        response = self.client.post(
            "/predict",
            json={"url": "paypal.com/login"},
            headers={"Authorization": "Bearer token"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json(),
            {
                "prediction": "phishing",
                "result": "phishing",
                "confidence": 0.91,
                "model_name": "GradientBoostingClassifier",
                "model_version": "test-model",
                "message": None,
            },
        )
        self.assertEqual(len(scan_service.saved_payloads), 1)
        self.assertEqual(scan_service.saved_payloads[0]["persist_mode"], "deferred")

    def test_predict_endpoint_returns_unavailable_for_down_site(self):
        self._inject_services()

        response = self.client.post(
            "/predict",
            json={"url": "https://down.example.com"},
            headers={"Authorization": "Bearer token"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json(),
            {
                "prediction": "unavailable",
                "result": "unavailable",
                "confidence": None,
                "model_name": None,
                "model_version": None,
                "message": "The website appears to be down or unreachable right now.",
            },
        )

    def test_predict_endpoint_handles_preflight(self):
        self._inject_services()

        response = self.client.open(
            "/predict",
            method="OPTIONS",
            headers={
                "Origin": "http://127.0.0.1:3004",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("Access-Control-Allow-Origin"), "http://127.0.0.1:3004")
        self.assertIn("POST", response.headers.get("Access-Control-Allow-Methods", ""))

    def test_scan_endpoint_validates_input(self):
        self._inject_services()
        response = self.client.post(
            "/scan",
            json={"url": "ftp://example.com"},
            headers={"Authorization": "Bearer token"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.get_json()["error"]["code"], "validation_error"
        )

    def test_history_endpoint_returns_records(self):
        self._inject_services()

        response = self.client.get(
            "/history?limit=5&offset=0",
            headers={"Authorization": "Bearer token"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["pagination"]["limit"], 5)
        self.assertEqual(payload["items"][0]["user_id"], "user-123")

    def test_admin_stats_requires_admin(self):
        self._inject_services(is_admin=False)
        response = self.client.get(
            "/admin/stats", headers={"Authorization": "Bearer token"}
        )

        self.assertEqual(response.status_code, 403)

    def test_admin_stats_returns_stats_for_admin(self):
        self._inject_services(is_admin=True)
        response = self.client.get(
            "/admin/stats?range=7d", headers={"Authorization": "Bearer token"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["overview"]["total_scans"], 10)

    def test_admin_stats_can_include_auth_history(self):
        self._inject_services(is_admin=True)
        response = self.client.get(
            "/admin/stats?range=7d&include_auth_history=true",
            headers={"Authorization": "Bearer token"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["auth_history"][0]["email"], "admin@example.com")

    def test_admin_user_history_returns_records_for_admin(self):
        self._inject_services(is_admin=True)
        response = self.client.get(
            "/admin/users/user-456/history", headers={"Authorization": "Bearer token"}
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["total"], 2)
        self.assertEqual(payload["items"][0]["user_id"], "user-456")

    def test_admin_user_history_handles_preflight(self):
        self._inject_services(is_admin=True)
        response = self.client.open(
            "/admin/users/user-456/history",
            method="OPTIONS",
            headers={
                "Origin": "http://localhost:8080",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("Access-Control-Allow-Origin"), "http://localhost:8080")
        self.assertIn("GET", response.headers.get("Access-Control-Allow-Methods", ""))

    def test_signup_endpoint_creates_account(self):
        response = self.client.post(
            "/auth/signup",
            json={"email": "user@example.com", "password": "strong-pass"},
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json()["user"]["email"], "user@example.com")

    def test_signup_endpoint_validates_input(self):
        response = self.client.post(
            "/auth/signup",
            json={"email": "invalid-email", "password": "123"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.get_json()["error"]["message"], "Enter a valid email address"
        )
