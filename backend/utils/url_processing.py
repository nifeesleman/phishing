from __future__ import annotations

import ipaddress
import posixpath
import re
from dataclasses import dataclass
from urllib.parse import parse_qsl, quote, unquote, urlencode, urlsplit, urlunsplit

from utils.errors import ValidationError

_CONTROL_CHARACTERS = re.compile(r"[\x00-\x1f\x7f]+")
_SCHEME_PREFIX = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*://")
_HOST_LABEL = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$", re.IGNORECASE)
_SUSPICIOUS_TERMS = {
    "account",
    "alert",
    "auth",
    "billing",
    "confirm",
    "login",
    "password",
    "secure",
    "signin",
    "support",
    "unlock",
    "update",
    "verify",
}


@dataclass(frozen=True)
class PreparedUrl:
    original_url: str
    normalized_url: str
    hostname: str
    inferred_target: str
    combined_text: str
    heuristics: dict


def _normalize_hostname(hostname: str) -> str:
    sanitized = hostname.strip().strip(".").lower()
    if not sanitized:
        raise ValidationError("URL hostname is required")
    try:
        normalized = sanitized.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise ValidationError("URL hostname is invalid") from exc

    if any(character.isspace() for character in normalized):
        raise ValidationError("URL hostname is invalid")

    try:
        ipaddress.ip_address(normalized)
        return normalized
    except ValueError:
        pass

    if normalized == "localhost":
        return normalized

    labels = normalized.split(".")
    if len(labels) < 2:
        raise ValidationError("URL hostname must be a fully qualified domain or IP address")
    if any(not _HOST_LABEL.fullmatch(label) for label in labels):
        raise ValidationError("URL hostname is invalid")

    if len(labels) > 2 and labels[0] == "www":
        return ".".join(labels[1:])

    return normalized


def _normalize_path(path: str) -> str:
    unquoted = unquote(path or "/")
    normalized = posixpath.normpath(unquoted)
    if normalized == ".":
        normalized = "/"
    if not normalized.startswith("/"):
        normalized = f"/{normalized}"
    if path.endswith("/") and not normalized.endswith("/"):
        normalized = f"{normalized}/"
    return quote(normalized, safe="/:@")


def _normalize_query(query: str) -> str:
    if not query:
        return ""
    items = parse_qsl(query, keep_blank_values=True)
    return urlencode(items, doseq=True, quote_via=quote)


def _infer_target(normalized_url: str, hostname: str, brand_keywords: dict[str, str]) -> str:
    candidate = f"{normalized_url} {hostname}".lower()
    compact = re.sub(r"[^a-z0-9]+", "", candidate)
    for keyword, target in brand_keywords.items():
        normalized_keyword = re.sub(r"[^a-z0-9]+", "", keyword.lower())
        if keyword.lower() in candidate or normalized_keyword in compact:
            return target
    return "Other"


def _match_brand_keywords(hostname: str, brand_keywords: dict[str, str]) -> list[str]:
    compact_hostname = re.sub(r"[^a-z0-9]+", "", hostname.lower())
    matches: list[str] = []
    for keyword in brand_keywords:
        normalized_keyword = re.sub(r"[^a-z0-9]+", "", keyword.lower())
        if keyword.lower() in hostname.lower() or normalized_keyword in compact_hostname:
            if keyword not in matches:
                matches.append(keyword)
    return matches


def _find_suspicious_terms(*values: str) -> list[str]:
    terms: list[str] = []
    for value in values:
        for token in re.findall(r"[a-z0-9]+", value.lower()):
            if token in _SUSPICIOUS_TERMS and token not in terms:
                terms.append(token)
    return terms


def prepare_url(raw_url: str | None, brand_keywords: dict[str, str]) -> PreparedUrl:
    if not raw_url or not isinstance(raw_url, str):
        raise ValidationError("url is required")

    cleaned_input = _CONTROL_CHARACTERS.sub("", raw_url).strip()
    if not cleaned_input:
        raise ValidationError("url is required")
    if len(cleaned_input) > 2048:
        raise ValidationError("url must be 2048 characters or fewer")

    candidate = cleaned_input if _SCHEME_PREFIX.match(cleaned_input) else f"https://{cleaned_input}"
    try:
        parsed = urlsplit(candidate)
    except ValueError as exc:
        raise ValidationError("URL hostname is invalid") from exc
    if parsed.scheme.lower() not in {"http", "https"}:
        raise ValidationError("Only http and https URLs are supported")
    if not parsed.hostname:
        raise ValidationError("URL must include a valid hostname")

    hostname = _normalize_hostname(parsed.hostname)
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValidationError("URL port is invalid") from exc

    default_port = (parsed.scheme.lower() == "http" and port == 80) or (
        parsed.scheme.lower() == "https" and port == 443
    )
    netloc = hostname if not port or default_port else f"{hostname}:{port}"
    normalized_url = urlunsplit(
        (
            parsed.scheme.lower(),
            netloc,
            _normalize_path(parsed.path),
            _normalize_query(parsed.query),
            "",
        )
    )
    inferred_target = _infer_target(normalized_url, hostname, brand_keywords)
    matched_brands = _match_brand_keywords(hostname, brand_keywords)
    suspicious_terms = _find_suspicious_terms(hostname, parsed.path, parsed.query)
    heuristics = {
        "uses_https": parsed.scheme.lower() == "https",
        "contains_ip_address": bool(re.fullmatch(r"\d{1,3}(?:\.\d{1,3}){3}", hostname)),
        "subdomain_depth": max(0, len(hostname.split(".")) - 2),
        "path_depth": len([segment for segment in parsed.path.split("/") if segment]),
        "has_hyphenated_hostname": "-" in hostname,
        "matched_brands": matched_brands,
        "suspicious_terms": suspicious_terms,
    }
    return PreparedUrl(
        original_url=cleaned_input,
        normalized_url=normalized_url,
        hostname=hostname,
        inferred_target=inferred_target,
        combined_text=f"{normalized_url} {inferred_target}",
        heuristics=heuristics,
    )
