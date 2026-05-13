from __future__ import annotations
import calendar

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import logging
from collections import defaultdict
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from urllib.parse import quote, urlsplit, urlunsplit

import requests

from services.local_history_store import LocalHistoryStore
from services.model_service import ModelPrediction, PhishingModelService
from utils.auth import AuthenticatedUser
from utils.errors import ConfigurationError, UpstreamServiceError
from utils.url_processing import PreparedUrl, prepare_url

logger = logging.getLogger(__name__)


def _subtract_months(value: datetime, months: int) -> datetime:
    year = value.year
    month = value.month - months
    while month <= 0:
        year -= 1
        month += 12
    day = min(value.day, calendar.monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


@dataclass(frozen=True)
class AvailabilityStatus:
    is_available: bool
    message: str | None = None


class ScanService:
    def __init__(self, config, model_service: PhishingModelService, local_history_store: LocalHistoryStore) -> None:
        self._config = config
        self._model_service = model_service
        self._local_history_store = local_history_store
        self._persistence_executor = ThreadPoolExecutor(
            max_workers=max(1, int(self._config.get("SCAN_PERSIST_WORKERS", 2)))
        )
        # Shared pool for parallel Supabase read requests (history, admin stats)
        self._request_executor = ThreadPoolExecutor(
            max_workers=max(4, int(self._config.get("SCAN_REQUEST_WORKERS", 4)))
        )

    @property
    def _scans_table(self) -> str:
        return self._config.get("SUPABASE_SCANS_TABLE", "scans")

    def scan_url(self, user: AuthenticatedUser, raw_url: str, *, persist_mode: str = "blocking") -> dict:
        prepared_url = prepare_url(raw_url, self._config["BRAND_KEYWORDS"])
        availability = self._check_site_availability(prepared_url)
        if not availability.is_available:
            return {
                "result": "unavailable",
                "confidence": None,
                "model_name": None,
                "model_version": None,
                "message": availability.message or "The website appears to be unavailable right now.",
            }
        prediction = self._model_service.predict(prepared_url)
        created_at = datetime.now(UTC).isoformat()
        response = {
            "result": prediction.api_result,
            "confidence": prediction.confidence,
            "model_name": prediction.model_name,
            "model_version": prediction.model_version,
        }
        if persist_mode == "deferred":
            self._persist_scan_deferred(user, prepared_url, prediction, created_at=created_at)
            return response

        warning = self._persist_scan_with_fallback(
            user=user,
            prepared_url=prepared_url,
            prediction=prediction,
            created_at=created_at,
        )
        if warning:
            response["warning"] = warning
        return response

    def _persist_scan_with_fallback(
        self,
        *,
        user: AuthenticatedUser,
        prepared_url: PreparedUrl,
        prediction: ModelPrediction,
        created_at: str,
    ) -> str | None:
        try:
            self._save_scan(user, prepared_url, prediction, created_at=created_at)
        except (ConfigurationError, UpstreamServiceError) as exc:
            logger.warning("Scan completed but could not be persisted: %s", exc)
            self._save_local_scan(
                user=user,
                url=prepared_url.original_url,
                prediction=prediction,
                created_at=created_at,
            )
            return "Scan completed and was saved to local history because the remote history store is unavailable."
        return None

    def _persist_scan_deferred(
        self,
        user: AuthenticatedUser,
        prepared_url: PreparedUrl,
        prediction: ModelPrediction,
        *,
        created_at: str,
    ) -> None:
        try:
            self._persistence_executor.submit(
                self._persist_scan_background,
                user,
                prepared_url,
                prediction,
                created_at,
            )
        except RuntimeError:
            warning = self._persist_scan_with_fallback(
                user=user,
                prepared_url=prepared_url,
                prediction=prediction,
                created_at=created_at,
            )
            if warning:
                logger.warning(warning)

    def _persist_scan_background(
        self,
        user: AuthenticatedUser,
        prepared_url: PreparedUrl,
        prediction: ModelPrediction,
        created_at: str,
    ) -> None:
        warning = self._persist_scan_with_fallback(
            user=user,
            prepared_url=prepared_url,
            prediction=prediction,
            created_at=created_at,
        )
        if warning:
            logger.warning(warning)

    def _check_site_availability(self, prepared_url: PreparedUrl) -> AvailabilityStatus:
        alternate_url = self._build_alternate_availability_url(prepared_url.normalized_url)
        candidates = [prepared_url.normalized_url]
        if alternate_url and alternate_url not in candidates:
            candidates.append(alternate_url)

        for candidate_url in candidates:
            try:
                response = requests.get(
                    candidate_url,
                    allow_redirects=True,
                    timeout=float(self._config.get("SITE_AVAILABILITY_TIMEOUT_SECONDS", 5)),
                    headers={
                        "User-Agent": (
                            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/124.0.0.0 Safari/537.36"
                        )
                    },
                    stream=True,
                )
                status_code = response.status_code
            except requests.RequestException as exc:
                logger.info("Site availability check failed for %s: %s", candidate_url, exc)
                continue
            finally:
                if "response" in locals():
                    response.close()
                    del response

            if status_code < 500:
                return AvailabilityStatus(is_available=True)

        return AvailabilityStatus(
            is_available=False,
            message="The website appears to be down or unreachable right now.",
        )

    @staticmethod
    def _build_alternate_availability_url(normalized_url: str) -> str | None:
        parsed = urlsplit(normalized_url)
        hostname = parsed.hostname
        if not hostname:
            return None

        if hostname.startswith("www."):
            alternate_hostname = hostname[4:]
        else:
            alternate_hostname = f"www.{hostname}"

        if alternate_hostname == hostname:
            return None

        netloc = alternate_hostname
        if parsed.port:
            netloc = f"{alternate_hostname}:{parsed.port}"

        return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, ""))

    def get_history(
        self,
        user: AuthenticatedUser,
        *,
        limit: int,
        offset: int,
        search: str = "",
        result: str | None = None,
        sort: str = "newest",
    ) -> dict:
        filters = {"user_id": f"eq.{user.user_id}"}
        if result:
            filters["result"] = f"eq.{self._to_storage_result(result)}"
        if search:
            filters["url"] = f"ilike.*{quote(search)}*"

        try:
            count_future = self._request_executor.submit(
                lambda: self._count_records(filters, user=user)
            )
            data_future = self._request_executor.submit(
                lambda: self._request(
                    "GET",
                    f"/rest/v1/{self._scans_table}",
                    params=self._build_history_params(filters, limit, offset, sort),
                    user=user,
                )
            )
            total = count_future.result()
            response = data_future.result()
            items = response if isinstance(response, list) else []
            return {
                "items": [self._serialize_history_item(item) for item in items],
                "total": total,
                "pagination": {"limit": limit, "offset": offset},
            }
        except (ConfigurationError, UpstreamServiceError) as exc:
            logger.warning("Falling back to local history store: %s", exc)
            fallback = self._local_history_store.fetch_history(
                user_id=user.user_id,
                limit=limit,
                offset=offset,
                search=search,
                result=result,
                sort=sort,
            )
            return {
                "items": [self._serialize_history_item(item) for item in fallback["items"]],
                "total": fallback["total"],
                "pagination": fallback["pagination"],
            }

    def get_admin_stats(self, *, range_value: str = "30d", include_auth_history: bool = False) -> dict:
        now = datetime.now(UTC)
        start = now - {"7d": timedelta(days=7), "30d": timedelta(days=30), "90d": timedelta(days=90)}[
            range_value
        ]
        range_filter = {"created_at": f"gte.{start.isoformat()}"}

        # Fire all Supabase requests in parallel to avoid serial round-trips
        recent_future = self._request_executor.submit(
            lambda: self._request(
                "GET",
                f"/rest/v1/{self._scans_table}",
                params={
                    "select": "id,user_id,email,url,result,confidence_score,created_at",
                    "created_at": f"gte.{start.isoformat()}",
                    "order": "created_at.desc",
                    "limit": str(self._config["ADMIN_ANALYTICS_FETCH_LIMIT"]),
                },
            )
        )
        phishing_future = self._request_executor.submit(
            self._count_records, {**range_filter, "result": "eq.phishing"}
        )
        legit_future = self._request_executor.submit(
            self._count_records, {**range_filter, "result": "eq.legitimate"}
        )
        total_future = self._request_executor.submit(self._count_records, range_filter)
        auth_future = (
            self._request_executor.submit(self._fetch_admin_auth_history)
            if include_auth_history
            else None
        )

        recent_rows_raw = recent_future.result()
        phishing_count = phishing_future.result()
        legit_count = legit_future.result()
        total_scans = total_future.result()

        rows = recent_rows_raw if isinstance(recent_rows_raw, list) else []
        serialized_rows = [self._serialize_history_item(row) for row in rows]

        activity = defaultdict(lambda: {"total": 0, "phishing": 0, "legit": 0})
        top_urls: dict[str, dict] = {}
        user_histories: dict[str, list[dict]] = defaultdict(list)
        for row in serialized_rows:
            created_at = row.get("created_at")
            if created_at:
                day_key = created_at[:10]
                activity[day_key]["total"] += 1
                activity[day_key][row["result"]] += 1
            user_id = row.get("user_id")
            if user_id:
                user_histories[str(user_id)].append(row)
            if row["result"] == "phishing":
                current = top_urls.setdefault(
                    row["url"],
                    {"url": row["url"], "count": 0, "result": "phishing", "last_seen": created_at},
                )
                current["count"] += 1
                if created_at and (not current["last_seen"] or created_at > current["last_seen"]):
                    current["last_seen"] = created_at

        confidence_values = [
            float(row["confidence"])
            for row in serialized_rows
            if isinstance(row.get("confidence"), (int, float))
        ]
        response = {
            "overview": {
                "total_scans": total_scans,
                "phishing_count": phishing_count,
                "legit_count": legit_count,
                "unique_users": len({row["user_id"] for row in serialized_rows if row.get("user_id")}),
                "avg_confidence": round(sum(confidence_values) / len(confidence_values), 4)
                if confidence_values
                else 0,
            },
            "activity": [
                {"date": date, **values}
                for date, values in sorted(activity.items(), key=lambda item: item[0])
            ],
            "top_risky_urls": sorted(top_urls.values(), key=lambda item: (-item["count"], item["url"]))[:10],
            "recent_scans": serialized_rows[:20],
            "user_histories": dict(user_histories),
        }
        if auth_future is not None:
            response["auth_history"] = auth_future.result()
        return response

    def get_admin_user_history(self, user_id: str) -> dict:
        filters = {"user_id": f"eq.{user_id}"}
        total = self._count_records(filters)
        if total <= 0:
            return {"items": [], "total": 0}

        batch_size = 100
        serialized_rows: list[dict] = []
        offset = 0

        while offset < total:
            response = self._request(
                "GET",
                f"/rest/v1/{self._scans_table}",
                params=self._build_history_params(filters, batch_size, offset, "newest"),
            )
            rows = response if isinstance(response, list) else []
            if not rows:
                break

            serialized_rows.extend(self._serialize_history_item(row) for row in rows)
            offset += len(rows)

        return {
            "items": serialized_rows,
            "total": total,
        }

    def user_is_admin(self, user_id: str) -> bool:
        response = self._request(
            "GET",
            "/rest/v1/user_roles",
            params={"select": "role", "user_id": f"eq.{user_id}", "role": "eq.admin", "limit": "1"},
        )
        return bool(response)

    def cleanup_inactive_auth_users(self) -> dict:
        if not self._config.get("SUPABASE_SERVICE_ROLE_KEY"):
            raise ConfigurationError("SUPABASE_SERVICE_ROLE_KEY must be configured for inactive user cleanup")

        cutoff = _subtract_months(datetime.now(UTC), 6)
        auth_users = self._fetch_all_auth_users()
        admin_user_ids = self._fetch_admin_user_ids()
        stale_users: list[dict] = []

        for user in auth_users:
            serialized_user = self._serialize_auth_history_item(user)
            user_id = str(serialized_user.get("id") or "").strip()
            if not user_id:
                continue

            if user_id in admin_user_ids or serialized_user.get("is_admin"):
                continue

            activity_timestamp = self._get_auth_user_activity_timestamp(serialized_user)
            if activity_timestamp is None or activity_timestamp > cutoff:
                continue

            stale_users.append(serialized_user)

        deleted_users: list[dict] = []
        failed_users: list[dict] = []

        for user in stale_users:
            user_id = str(user.get("id") or "").strip()
            if not user_id:
                continue

            try:
                self._delete_auth_user(user_id)
            except UpstreamServiceError as exc:
                failed_users.append({**user, "message": str(exc)})
            else:
                deleted_users.append(user)

        return {
            "cutoff_timestamp": cutoff.isoformat(),
            "deleted_count": len(deleted_users),
            "failed_count": len(failed_users),
            "deleted_users": deleted_users,
            "failed_users": failed_users,
        }

    def _save_scan(
        self,
        user: AuthenticatedUser,
        prepared_url: PreparedUrl,
        prediction: ModelPrediction,
        *,
        created_at: str,
    ) -> None:
        payload = {
            "user_id": user.user_id,
            "email": user.email,
            "url": prepared_url.original_url,
            "normalized_url": prepared_url.normalized_url,
            "hostname": prepared_url.hostname,
            "inferred_target": prepared_url.inferred_target,
            "result": prediction.storage_result,
            "confidence_score": prediction.confidence,
            "detection_method": "ml",
            "details": {
                "hostname": prepared_url.hostname,
                "heuristics": prediction.heuristics,
                "model": {
                    "name": prediction.model_name,
                    "version": prediction.model_version,
                },
            },
            "model_name": prediction.model_name,
            "model_version": prediction.model_version,
            "metadata": {},
            "created_at": created_at,
        }
        response = self._request(
            "POST",
            f"/rest/v1/{self._scans_table}",
            json=payload,
            headers={"Prefer": "return=minimal"},
            user=user,
        )
        if response not in ({}, None):
            return

    def _save_local_scan(
        self,
        *,
        user: AuthenticatedUser,
        url: str,
        prediction: ModelPrediction,
        created_at: str,
    ) -> None:
        self._local_history_store.save_scan(
            user_id=user.user_id,
            user_email=user.email,
            url=url,
            result=prediction.api_result,
            confidence=prediction.confidence,
            created_at=created_at,
        )

    def _count_records(self, extra_filters: Mapping[str, str] | None = None, *, user: AuthenticatedUser | None = None) -> int:
        params = {"select": "id", "limit": "1"}
        if extra_filters:
            params.update(extra_filters)
        response = self._request(
            "GET",
            f"/rest/v1/{self._scans_table}",
            params=params,
            headers={"Prefer": "count=exact"},
            return_response=True,
            user=user,
        )
        content_range = response.headers.get("Content-Range", "*/0")
        try:
            return int(content_range.split("/")[-1])
        except ValueError as exc:
            raise UpstreamServiceError("Supabase count response was malformed") from exc

    def _build_history_params(self, filters: dict[str, str], limit: int, offset: int, sort: str) -> dict:
        order = {
            "oldest": "created_at.asc",
            "confidence_desc": "confidence_score.desc",
            "confidence_asc": "confidence_score.asc",
        }.get(sort, "created_at.desc")
        params = {
            "select": "id,user_id,email,url,result,confidence_score,created_at",
            "limit": str(limit),
            "offset": str(offset),
            "order": order,
        }
        params.update(filters)
        return params

    def _fetch_admin_auth_history(self) -> list[dict]:
        if not self._config.get("SUPABASE_SERVICE_ROLE_KEY"):
            raise ConfigurationError("SUPABASE_SERVICE_ROLE_KEY must be configured for admin auth history")

        users = self._fetch_all_auth_users()
        history = [self._serialize_auth_history_item(user) for user in users if user.get("email")]
        history.sort(
            key=lambda item: (
                item.get("last_sign_in_timestamp") or item.get("signup_timestamp") or ""
            ),
            reverse=True,
        )
        return history

    def _fetch_all_auth_users(self) -> list[dict]:
        users: list[dict] = []
        page = 1
        per_page = min(int(self._config.get("ADMIN_ANALYTICS_FETCH_LIMIT", 1000)), 1000)

        while True:
            response = self._request(
                "GET",
                "/auth/v1/admin/users",
                params={
                    "page": str(page),
                    "per_page": str(per_page),
                },
            )
            batch = response.get("users", []) if isinstance(response, dict) else []
            if not isinstance(batch, list) or not batch:
                break

            users.extend(user for user in batch if isinstance(user, dict))
            if len(batch) < per_page:
                break
            page += 1

        return users

    def _fetch_admin_user_ids(self) -> set[str]:
        admin_user_ids: set[str] = set()
        limit = 1000
        offset = 0

        while True:
            response = self._request(
                "GET",
                "/rest/v1/user_roles",
                params={
                    "select": "user_id",
                    "role": "eq.admin",
                    "limit": str(limit),
                    "offset": str(offset),
                },
            )
            rows = response if isinstance(response, list) else []
            if not rows:
                break

            for row in rows:
                if isinstance(row, dict) and row.get("user_id"):
                    admin_user_ids.add(str(row["user_id"]))

            if len(rows) < limit:
                break
            offset += len(rows)

        return admin_user_ids

    def _delete_auth_user(self, user_id: str) -> None:
        self._request(
            "DELETE",
            f"/auth/v1/admin/users/{quote(user_id)}",
        )

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict | None = None,
        json: dict | None = None,
        headers: dict | None = None,
        return_response: bool = False,
        user: AuthenticatedUser | None = None,
    ):
        api_key, auth_header = self._resolve_credentials(user)
        merged_headers = {
            "apikey": api_key,
            "Authorization": auth_header,
            "Content-Type": "application/json",
        }
        if headers:
            merged_headers.update(headers)

        response = requests.request(
            method=method,
            url=f"{self._config['SUPABASE_URL']}{path}",
            params=params,
            json=json,
            headers=merged_headers,
            timeout=self._config["SUPABASE_TIMEOUT_SECONDS"],
        )
        if response.status_code >= 400:
            raise UpstreamServiceError(
                f"Supabase request failed with status {response.status_code}: {response.text}"
            )
        if return_response:
            return response
        if not response.content:
            return {}
        return response.json()

    def _resolve_credentials(self, user: AuthenticatedUser | None = None) -> tuple[str, str]:
        if not self._config.get("SUPABASE_URL"):
            raise ConfigurationError("SUPABASE_URL must be configured")

        service_role_key = self._config.get("SUPABASE_SERVICE_ROLE_KEY", "")
        if service_role_key:
            return service_role_key, f"Bearer {service_role_key}"

        publishable_key = self._config.get("SUPABASE_PUBLISHABLE_KEY", "")
        if user and user.access_token and publishable_key:
            return publishable_key, f"Bearer {user.access_token}"

        raise ConfigurationError(
            "Configure SUPABASE_SERVICE_ROLE_KEY or SUPABASE_PUBLISHABLE_KEY for authenticated scan access"
        )

    @staticmethod
    def _to_api_result(storage_result: str | None) -> str:
        return "phishing" if storage_result == "phishing" else "legit"

    @staticmethod
    def _to_storage_result(api_result: str) -> str:
        return "phishing" if api_result == "phishing" else "legitimate"

    def _serialize_history_item(self, record: dict) -> dict:
        return {
            "id": record.get("id"),
            "user_id": record.get("user_id"),
            "user_email": record.get("email") or record.get("user_email"),
            "url": record.get("url", ""),
            "result": self._to_api_result(record.get("result")) if record.get("result") in {"phishing", "legitimate"} else (record.get("result") or "legit"),
            "confidence": record.get("confidence_score") if record.get("confidence_score") is not None else record.get("confidence", 0),
            "created_at": record.get("created_at"),
        }

    def _serialize_auth_history_item(self, user: dict) -> dict:
        app_metadata = user.get("app_metadata") if isinstance(user.get("app_metadata"), dict) else {}
        roles = {str(user.get("role", "")).lower(), str(app_metadata.get("role", "")).lower()}
        for entry in app_metadata.get("roles", []) or []:
            roles.add(str(entry).lower())

        providers = []
        raw_providers = app_metadata.get("providers")
        if isinstance(raw_providers, list):
            providers = [str(provider) for provider in raw_providers if provider]
        elif app_metadata.get("provider"):
            providers = [str(app_metadata["provider"])]

        return {
            "id": user.get("id"),
            "email": user.get("email"),
            "phone": user.get("phone"),
            "signup_timestamp": user.get("created_at"),
            "last_sign_in_timestamp": user.get("last_sign_in_at"),
            "email_confirmed_timestamp": user.get("email_confirmed_at"),
            "providers": providers,
            "is_admin": "admin" in roles or "service_role" in roles,
        }

    @staticmethod
    def _parse_auth_timestamp(value: str | None) -> datetime | None:
        if not value:
            return None

        normalized_value = value.replace("Z", "+00:00")
        try:
            parsed_value = datetime.fromisoformat(normalized_value)
        except ValueError:
            return None

        if parsed_value.tzinfo is None:
            parsed_value = parsed_value.replace(tzinfo=UTC)

        return parsed_value.astimezone(UTC)

    def _get_auth_user_activity_timestamp(self, user: dict) -> datetime | None:
        last_sign_in = self._parse_auth_timestamp(
            user.get("last_sign_in_timestamp") if isinstance(user, dict) else None
        )
        if last_sign_in is not None:
            return last_sign_in

        return self._parse_auth_timestamp(
            user.get("signup_timestamp") if isinstance(user, dict) else None
        )
