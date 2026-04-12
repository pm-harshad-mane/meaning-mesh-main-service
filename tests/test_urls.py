from app.utils.urls import InvalidUrlError, hash_normalized_url, normalize_url


def test_normalize_url_applies_contract_rules() -> None:
    normalized = normalize_url(
        "HTTPS://Example.COM:443/news/story/?b=2&utm_source=x&a=1#fragment"
    )
    assert normalized == "https://example.com/news/story?a=1&b=2"


def test_normalize_url_keeps_meaningful_query_params_when_tracking_strip_disabled() -> None:
    normalized = normalize_url(
        "https://example.com/path/?utm_source=x&topic=ai",
        strip_tracking_params=False,
    )
    assert normalized == "https://example.com/path?topic=ai&utm_source=x"


def test_normalize_url_rejects_non_http_scheme() -> None:
    try:
        normalize_url("ftp://example.com/file")
    except InvalidUrlError as exc:
        assert "http" in str(exc)
    else:
        raise AssertionError("Expected InvalidUrlError")


def test_hash_normalized_url_uses_sha256_prefix() -> None:
    url_hash = hash_normalized_url("https://example.com")
    assert url_hash.startswith("sha256:")
    assert len(url_hash) == 71
