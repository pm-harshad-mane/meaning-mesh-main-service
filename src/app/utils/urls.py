from __future__ import annotations

import hashlib
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

TRACKING_QUERY_KEYS = {"gclid", "fbclid", "mc_cid", "mc_eid"}


class InvalidUrlError(ValueError):
    """Raised when a URL cannot be normalized into a valid canonical form."""


def _normalized_path(path: str) -> str:
    if not path:
        return "/"
    if path != "/" and path.endswith("/"):
        return path.rstrip("/")
    return path


def _filter_and_sort_query(query: str, strip_tracking_params: bool) -> str:
    pairs = parse_qsl(query, keep_blank_values=True)
    filtered_pairs: list[tuple[str, str]] = []

    for key, value in pairs:
        if strip_tracking_params and (
            key.lower().startswith("utm_") or key.lower() in TRACKING_QUERY_KEYS
        ):
            continue
        filtered_pairs.append((key, value))

    filtered_pairs.sort(key=lambda item: (item[0], item[1]))
    return urlencode(filtered_pairs, doseq=True)


def normalize_url(url: str, *, strip_tracking_params: bool = True) -> str:
    parts = urlsplit(url)
    scheme = parts.scheme.lower()
    host = (parts.hostname or "").lower()

    if scheme not in {"http", "https"} or not host:
        raise InvalidUrlError("Only absolute http(s) URLs are supported")

    port = parts.port
    if (scheme == "http" and port == 80) or (scheme == "https" and port == 443):
        port = None

    auth = ""
    if parts.username:
        auth = parts.username
        if parts.password:
            auth = f"{auth}:{parts.password}"
        auth = f"{auth}@"

    netloc = f"{auth}{host}"
    if port is not None:
        netloc = f"{netloc}:{port}"

    normalized = urlunsplit(
        (
            scheme,
            netloc,
            _normalized_path(parts.path),
            _filter_and_sort_query(parts.query, strip_tracking_params),
            "",
        )
    )
    return normalized


def hash_normalized_url(normalized_url: str) -> str:
    digest = hashlib.sha256(normalized_url.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"
