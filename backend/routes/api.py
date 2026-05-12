from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

from services.auth_service import AuthService
from services.scan_service import ScanService
from utils.auth import get_jwt_verifier
from utils.errors import ConfigurationError, ValidationError

api_blueprint = Blueprint("api", __name__)


def _get_scan_service() -> ScanService:
    service = current_app.extensions.get("scan_service")
    if service is None:
        raise ConfigurationError("Scan service is unavailable")
    return service


def _get_auth_service() -> AuthService:
    service = current_app.extensions.get("auth_service")
    if service is None:
        raise ConfigurationError("Auth service is unavailable")
    return service


def _parse_limit_offset() -> tuple[int, int]:
    try:
        limit = int(request.args.get("limit", "20"))
        offset = int(request.args.get("offset", "0"))
    except ValueError as exc:
        raise ValidationError("limit and offset must be integers") from exc

    if limit < 1 or limit > 100:
        raise ValidationError("limit must be between 1 and 100")
    if offset < 0:
        raise ValidationError("offset must be greater than or equal to 0")
    return limit, offset


def _parse_history_filters() -> dict:
    result = request.args.get("result", "").strip().lower()
    if result and result not in {"phishing", "legit"}:
        raise ValidationError("result must be phishing or legit")

    sort = request.args.get("sort", "newest").strip().lower()
    if sort not in {"newest", "oldest", "confidence_desc", "confidence_asc"}:
        raise ValidationError("sort must be newest, oldest, confidence_desc, or confidence_asc")

    return {
        "search": request.args.get("search", "").strip(),
        "result": result or None,
        "sort": sort,
    }


def _parse_bool_query_arg(name: str, default: bool = False) -> bool:
    value = request.args.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _parse_json_body() -> dict:
    payload = request.get_json(silent=False)
    if not isinstance(payload, dict):
        raise ValidationError("Request body must be a JSON object")
    return payload


@api_blueprint.post("/auth/signup")
def signup():
    payload = _parse_json_body()
    return (
        jsonify(
            _get_auth_service().sign_up(
                email=str(payload.get("email", "")),
                password=str(payload.get("password", "")),
            )
        ),
        201,
    )


@api_blueprint.post("/scan")
def scan_url():
    user = get_jwt_verifier().require_user()
    payload = _parse_json_body()
    result = _get_scan_service().scan_url(user, payload.get("url"))
    return jsonify(result), 201


@api_blueprint.post("/predict")
def predict_url():
    user = get_jwt_verifier().require_user()
    payload = _parse_json_body()
    result = _get_scan_service().scan_url(user, payload.get("url"), persist_mode="deferred")
    prediction = str(result.get("result", "")).strip().lower()
    return (
        jsonify(
            {
                "prediction": "phishing" if prediction == "phishing" else ("unavailable" if prediction == "unavailable" else "safe"),
                "result": prediction,
                "confidence": result.get("confidence"),
                "model_name": result.get("model_name"),
                "model_version": result.get("model_version"),
                "message": result.get("message"),
            }
        ),
        200,
    )


@api_blueprint.get("/history")
def history():
    user = get_jwt_verifier().require_user()
    limit, offset = _parse_limit_offset()
    filters = _parse_history_filters()
    return jsonify(
        _get_scan_service().get_history(
            user,
            limit=limit,
            offset=offset,
            search=filters["search"],
            result=filters["result"],
            sort=filters["sort"],
        )
    )


@api_blueprint.get("/admin/stats")
def admin_stats():
    user = get_jwt_verifier().require_user()
    range_value = request.args.get("range", "30d").strip().lower()
    include_auth_history = _parse_bool_query_arg("include_auth_history")
    if range_value not in {"7d", "30d", "90d"}:
        raise ValidationError("range must be one of 7d, 30d, or 90d")

    scan_service = _get_scan_service()
    if not user.is_admin and not scan_service.user_is_admin(user.user_id):
        from utils.errors import AuthorizationError

        raise AuthorizationError("Admin privileges are required")

    return jsonify(
        scan_service.get_admin_stats(
            range_value=range_value,
            include_auth_history=include_auth_history,
        )
    )


@api_blueprint.route("/admin/users/<user_id>/history", methods=["GET", "OPTIONS"])
def admin_user_history(user_id: str):
    if request.method == "OPTIONS":
        return ("", 200)

    user = get_jwt_verifier().require_user()
    scan_service = _get_scan_service()
    if not user.is_admin and not scan_service.user_is_admin(user.user_id):
        from utils.errors import AuthorizationError

        raise AuthorizationError("Admin privileges are required")

    return jsonify(scan_service.get_admin_user_history(user_id))
