# Main Service Contracts

This repo implements the request-path contract from `../codex_instructions.md`.

Primary request lifecycle:

1. Parse and validate the incoming URL request.
2. Normalize the URL into a canonical identity.
3. Compute `sha256(normalized_url)` with the `sha256:` prefix.
4. Read `url_categorization`.
5. Return cached `ready` or `unknown` data when present and not expired.
6. Otherwise write a conditional `url_wip` item.
7. If the write fails, return `pending`.
8. If the write succeeds, enqueue a fetch job and return `pending`.

The fetch queue message schema is:

```json
{
  "url_hash": "sha256:...",
  "normalized_url": "https://example.com/page",
  "trace_id": "trace-...",
  "queued_at": 1775862000,
  "requested_ttl_seconds": 2592000
}
```
