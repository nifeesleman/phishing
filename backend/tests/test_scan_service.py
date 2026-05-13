from __future__ import annotations

import threading
import unittest
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from services.local_history_store import LocalHistoryStore
from services.model_service import ModelPrediction
from services.scan_service import ScanService
from utils.auth import AuthenticatedUser
from utils.errors import UpstreamServiceError


class _FakeModelService:
    def predict(self, prepared_url):
        return ModelPrediction(
            storage_result="phishing",
            api_result="phishing",
            confidence=0.88,
            model_name="DecisionTreeClassifier",
            model_version="test-model",
            heuristics=prepared_url.heuristics,
        )


class _FailingScanService(ScanService):
    def _check_site_availability(self, prepared_url):
        return type("AvailabilityStatusStub", (), {"is_available": True, "message": None})()

    def _save_scan(self, user, prepared_url, prediction, *, created_at) -> None:
        raise UpstreamServiceError("save failed")


class _AdminStatsScanService(ScanService):
    def __init__(self, config, model_service, local_history_store) -> None:
        super().__init__(config, model_service, local_history_store)
        self.auth_users = [
            {
                "id": "user-123",
                "email": "admin@example.com",
                "created_at": "2026-04-01T10:00:00+00:00",
                "last_sign_in_at": "2026-04-18T12:00:00+00:00",
                "role": "authenticated",
                "app_metadata": {"role": "admin", "roles": ["admin"]},
            },
            {
                "id": "user-456",
                "email": "user@example.com",
                "created_at": "2026-04-02T10:00:00+00:00",
                "last_sign_in_at": None,
                "role": "authenticated",
                "app_metadata": {"provider": "email", "roles": ["user"]},
            },
        ]
        self.admin_role_user_ids = {"user-123"}
        self.deleted_user_ids: list[str] = []

    def _request(self, method, path, **kwargs):
        if path == "/rest/v1/scans":
            params = kwargs.get("params", {})
            if params.get("user_id") == "eq.user-456":
                limit = int(params.get("limit", "100"))
                offset = int(params.get("offset", "0"))
                rows = [
                    {
                        "id": "scan-1",
                        "user_id": "user-456",
                        "email": "user@example.com",
                        "url": "https://example.com/login",
                        "result": "phishing",
                        "confidence_score": 0.91,
                        "created_at": "2026-04-18T12:00:00+00:00",
                    },
                    {
                        "id": "scan-2",
                        "user_id": "user-456",
                        "email": "user@example.com",
                        "url": "https://example.com",
                        "result": "legitimate",
                        "confidence_score": 0.21,
                        "created_at": "2026-04-18T10:00:00+00:00",
                    },
                ]
                return rows[offset : offset + limit]
            return []
        if path == "/rest/v1/user_roles":
            params = kwargs.get("params", {})
            if params.get("role") == "eq.admin":
                limit = int(params.get("limit", "1000"))
                offset = int(params.get("offset", "0"))
                rows = [{"user_id": user_id} for user_id in sorted(self.admin_role_user_ids)]
                return rows[offset : offset + limit]
            return []
        if path.startswith("/auth/v1/admin/users"):
            if method == "DELETE":
                user_id = path.rsplit("/", 1)[-1]
                self.deleted_user_ids.append(user_id)
                self.auth_users = [user for user in self.auth_users if user.get("id") != user_id]
                return {}

            params = kwargs.get("params", {})
            page = int(params.get("page", "1"))
            per_page = int(params.get("per_page", "1000"))
            start = (page - 1) * per_page
            end = start + per_page
            return {
                "users": self.auth_users[start:end]
            }
        raise AssertionError(f"Unexpected request path: {path}")

    def _count_records(self, extra_filters=None, *, user=None) -> int:
        if extra_filters and extra_filters.get("user_id") == "eq.user-456":
            return 2
        return 0


class _DeferredPersistenceScanService(ScanService):
    def __init__(self, config, model_service, local_history_store) -> None:
        super().__init__(config, model_service, local_history_store)
        self.persist_event = threading.Event()
        self.persisted_urls: list[str] = []

    def _check_site_availability(self, prepared_url):
        return type("AvailabilityStatusStub", (), {"is_available": True, "message": None})()

    def _save_scan(self, user, prepared_url, prediction, *, created_at) -> None:
        self.persisted_urls.append(prepared_url.original_url)
        self.persist_event.set()


class _UnavailableScanService(ScanService):
    def _check_site_availability(self, prepared_url):
        return type(
            "AvailabilityStatusStub",
            (),
            {
                "is_available": False,
                "message": "The website appears to be down or unreachable right now.",
            },
        )()


class ScanServiceTestCase(unittest.TestCase):
    def test_scan_returns_prediction_when_persistence_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            service = _FailingScanService(
                {
                    "BRAND_KEYWORDS": {
                        "paypal": "PayPal",
                    }
                },
                _FakeModelService(),
                LocalHistoryStore(str(Path(temp_dir) / "history.sqlite")),
            )
            user = AuthenticatedUser(
                user_id="user-123",
                email="user@example.com",
                claims={"sub": "user-123"},
                is_admin=False,
                access_token="token",
            )

            result = service.scan_url(user, "https://paypal.com/login")
            history = service.get_history(user, limit=10, offset=0)

            self.assertEqual(result["result"], "phishing")
            self.assertEqual(result["confidence"], 0.88)
            self.assertEqual(result["model_name"], "DecisionTreeClassifier")
            self.assertEqual(result["model_version"], "test-model")
            self.assertIn("warning", result)
            self.assertEqual(history["total"], 1)
            self.assertEqual(history["items"][0]["url"], "https://paypal.com/login")

    def test_service_role_key_takes_precedence_for_supabase_requests(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            service = ScanService(
                {
                    "SUPABASE_URL": "https://example.supabase.co",
                    "SUPABASE_SERVICE_ROLE_KEY": "service-role-key",
                    "SUPABASE_PUBLISHABLE_KEY": "publishable-key",
                },
                _FakeModelService(),
                LocalHistoryStore(str(Path(temp_dir) / "history.sqlite")),
            )
            user = AuthenticatedUser(
                user_id="user-123",
                email="user@example.com",
                claims={"sub": "user-123"},
                is_admin=False,
                access_token="user-token",
            )

            api_key, auth_header = service._resolve_credentials(user)

            self.assertEqual(api_key, "service-role-key")
            self.assertEqual(auth_header, "Bearer service-role-key")

    def test_scan_can_defer_persistence_without_changing_prediction_payload(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            service = _DeferredPersistenceScanService(
                {
                    "BRAND_KEYWORDS": {
                        "paypal": "PayPal",
                    }
                },
                _FakeModelService(),
                LocalHistoryStore(str(Path(temp_dir) / "history.sqlite")),
            )
            user = AuthenticatedUser(
                user_id="user-123",
                email="user@example.com",
                claims={"sub": "user-123"},
                is_admin=False,
                access_token="token",
            )

            result = service.scan_url(user, "https://paypal.com/login", persist_mode="deferred")

            self.assertEqual(result["result"], "phishing")
            self.assertEqual(result["confidence"], 0.88)
            self.assertTrue(service.persist_event.wait(timeout=1))
            self.assertEqual(service.persisted_urls, ["https://paypal.com/login"])

    def test_admin_stats_include_auth_history(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            service = _AdminStatsScanService(
                {
                    "ADMIN_ANALYTICS_FETCH_LIMIT": 50,
                    "SUPABASE_SERVICE_ROLE_KEY": "service-role-key",
                },
                _FakeModelService(),
                LocalHistoryStore(str(Path(temp_dir) / "history.sqlite")),
            )

            result = service.get_admin_stats(range_value="30d", include_auth_history=True)

            self.assertEqual(len(result["auth_history"]), 2)
            self.assertEqual(result["auth_history"][0]["email"], "admin@example.com")
            self.assertTrue(result["auth_history"][0]["is_admin"])
            self.assertEqual(
                result["auth_history"][1]["signup_timestamp"], "2026-04-02T10:00:00+00:00"
            )

    def test_admin_stats_omits_auth_history_when_not_requested(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            service = _AdminStatsScanService(
                {
                    "ADMIN_ANALYTICS_FETCH_LIMIT": 50,
                    "SUPABASE_SERVICE_ROLE_KEY": "service-role-key",
                },
                _FakeModelService(),
                LocalHistoryStore(str(Path(temp_dir) / "history.sqlite")),
            )

            result = service.get_admin_stats(range_value="30d", include_auth_history=False)

            self.assertNotIn("auth_history", result)

    def test_admin_user_history_returns_all_matching_scans(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            service = _AdminStatsScanService(
                {
                    "ADMIN_ANALYTICS_FETCH_LIMIT": 50,
                    "SUPABASE_SERVICE_ROLE_KEY": "service-role-key",
                },
                _FakeModelService(),
                LocalHistoryStore(str(Path(temp_dir) / "history.sqlite")),
            )

            result = service.get_admin_user_history("user-456")

            self.assertEqual(result["total"], 2)
            self.assertEqual(len(result["items"]), 2)
            self.assertEqual(result["items"][0]["result"], "phishing")
            self.assertEqual(result["items"][1]["result"], "legit")

    def test_cleanup_inactive_auth_users_deletes_stale_non_admin_accounts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            service = _AdminStatsScanService(
                {
                    "ADMIN_ANALYTICS_FETCH_LIMIT": 50,
                    "SUPABASE_SERVICE_ROLE_KEY": "service-role-key",
                },
                _FakeModelService(),
                LocalHistoryStore(str(Path(temp_dir) / "history.sqlite")),
            )
            service.auth_users = [
                {
                    "id": "user-admin-db-role",
                    "email": "db-admin@example.com",
                    "created_at": "2024-01-01T00:00:00+00:00",
                    "last_sign_in_at": "2024-01-02T00:00:00+00:00",
                    "role": "authenticated",
                    "app_metadata": {"roles": ["user"]},
                },
                {
                    "id": "user-stale-last-sign-in",
                    "email": "stale@example.com",
                    "created_at": "2024-01-01T00:00:00+00:00",
                    "last_sign_in_at": "2024-03-01T00:00:00+00:00",
                    "role": "authenticated",
                    "app_metadata": {"provider": "email", "roles": ["user"]},
                },
                {
                    "id": "user-stale-never-signed-in",
                    "email": "never-signed-in@example.com",
                    "created_at": "2024-02-01T00:00:00+00:00",
                    "last_sign_in_at": None,
                    "role": "authenticated",
                    "app_metadata": {"provider": "email", "roles": ["user"]},
                },
                {
                    "id": "user-recent",
                    "email": "recent@example.com",
                    "created_at": datetime.now(UTC).isoformat(),
                    "last_sign_in_at": datetime.now(UTC).isoformat(),
                    "role": "authenticated",
                    "app_metadata": {"provider": "email", "roles": ["user"]},
                },
            ]
            service.admin_role_user_ids = {"user-admin-db-role"}

            result = service.cleanup_inactive_auth_users()

            self.assertEqual(result["deleted_count"], 2)
            self.assertEqual(result["failed_count"], 0)
            self.assertEqual(
                {entry["id"] for entry in result["deleted_users"]},
                {"user-stale-last-sign-in", "user-stale-never-signed-in"},
            )
            self.assertEqual(
                set(service.deleted_user_ids),
                {"user-stale-last-sign-in", "user-stale-never-signed-in"},
            )
            self.assertEqual(
                {user["id"] for user in service.auth_users},
                {"user-admin-db-role", "user-recent"},
            )

    def test_scan_returns_unavailable_when_site_is_down(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            service = _UnavailableScanService(
                {
                    "BRAND_KEYWORDS": {
                        "paypal": "PayPal",
                    }
                },
                _FakeModelService(),
                LocalHistoryStore(str(Path(temp_dir) / "history.sqlite")),
            )
            user = AuthenticatedUser(
                user_id="user-123",
                email="user@example.com",
                claims={"sub": "user-123"},
                is_admin=False,
                access_token="token",
            )

            result = service.scan_url(user, "https://example.com")
            history = service.get_history(user, limit=10, offset=0)

            self.assertEqual(result["result"], "unavailable")
            self.assertIsNone(result["confidence"])
            self.assertEqual(result["message"], "The website appears to be down or unreachable right now.")
            self.assertEqual(history["total"], 0)
