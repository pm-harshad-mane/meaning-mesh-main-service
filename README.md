# meaning-mesh-main-service

AWS Lambda service for the public URL categorization request path.

Responsibilities:

- validate and normalize incoming URLs
- compute `sha256(normalized_url)` identifiers
- read cached categorization results from DynamoDB
- deduplicate in-flight work through conditional writes to `url_wip`
- enqueue fetch work to `url_fetcher_service_queue`
- return `ready`, `pending`, or `unknown` API responses

## Project Structure

```text
meaning-mesh-main-service/
  src/app/
  tests/
  docs/
  requirements.txt
  pyproject.toml
  .env.example
```

## Local Setup

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest
```

## Lambda Entry Point

Handler: `app.handler.lambda_handler`

Set `PYTHONPATH=src` for local execution.

## Environment Variables

See `.env.example` for the required configuration. Defaults follow the Meaning-Mesh contract where possible.
