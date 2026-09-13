# GitHub Issues Gateway

## Overview

GitHub Issues Gateway is a FastAPI service that wraps the GitHub REST API for a single configured repository. It exposes a custom HTTP API for issue and comment operations, validates and records GitHub webhooks, and provides automated tests, Docker support, OpenAPI 3.1 documentation, and CI.

### Features

- Create, list, retrieve, update, close, and reopen issues
- Create and list issue comments
- Receive `issues`, `issue_comment`, and `ping` webhooks
- HMAC-SHA256 webhook signature validation
- Constant-time signature comparison
- Webhook delivery deduplication
- SQLite persistence for webhook delivery metadata
- GitHub pagination with `page`, `per_page`, and forwarded `Link` headers
- GitHub authentication and error/rate-limit translation
- OpenAPI 3.1 contract
- Unit and integration tests
- Ruff linting
- Docker packaging
- GitHub Actions CI

## Requirements

- Python 3.12+
- Git
- Docker Desktop
- A dedicated GitHub test repository
- A GitHub Fine-Grained Personal Access Token

## GitHub Repository and Credentials

Create a dedicated GitHub repository for testing. It can be public or private.

Create a Fine-Grained Personal Access Token restricted to the test repository.

Required repository permission:

```text
Issues: Read and write
```

The service reads these required environment variables:

```text
GITHUB_TOKEN
GITHUB_OWNER
GITHUB_REPO
WEBHOOK_SECRET
PORT
```

Do not commit the token, webhook secret, or `.env` file.

## Environment Variables

Create `.env` in the project root:

```env
GITHUB_TOKEN=your_token_here
GITHUB_OWNER=your_github_username
GITHUB_REPO=github-service
WEBHOOK_SECRET=your_webhook_secret
PORT=8000
```

## Run Locally

### Create a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### Start the service

```powershell
python -m uvicorn app.main:app --reload --port 8000
```

Service URL:

```text
http://localhost:8000
```

### Health Check

```bash
curl http://localhost:8000/healthz
```

Expected response:

```json
{
  "status": "ok"
}
```

## OpenAPI Documentation

Swagger UI:

```text
http://localhost:8000/docs
```

ReDoc:

```text
http://localhost:8000/redoc
```

The submission also includes the required OpenAPI 3.1 contract:

```text
openapi.yaml
```

## API Usage

### POST /issues

Create an issue.

Request:

```json
{
  "title": "Test issue",
  "body": "Created through the gateway.",
  "labels": ["bug"]
}
```

Example:

```bash
curl -X POST http://localhost:8000/issues \
  -H "Content-Type: application/json" \
  -d "{\"title\":\"Test issue\",\"body\":\"Created through the gateway.\",\"labels\":[\"bug\"]}"
```

The successful response is `201 Created` and includes a `Location` header:

```text
Location: /issues/{number}
```

### GET /issues

List issues.

```bash
curl "http://localhost:8000/issues"
```

```bash
curl "http://localhost:8000/issues?state=all"
```

```bash
curl "http://localhost:8000/issues?page=2&per_page=10"
```

```bash
curl "http://localhost:8000/issues?labels=bug"
```

Parameters:

| Parameter | Description |
|---|---|
| `state` | `open`, `closed`, or `all` |
| `labels` | GitHub label name |
| `page` | Page number, minimum 1 |
| `per_page` | Results per page, maximum 100 |

GitHub pagination metadata is forwarded through the `Link` response header.

### GET /issues/{number}

Retrieve an issue.

```bash
curl http://localhost:8000/issues/1
```

### PATCH /issues/{number}

Update an issue:

```bash
curl -X PATCH http://localhost:8000/issues/1 \
  -H "Content-Type: application/json" \
  -d "{\"title\":\"Updated title\",\"body\":\"Updated body\"}"
```

Close an issue:

```bash
curl -X PATCH http://localhost:8000/issues/1 \
  -H "Content-Type: application/json" \
  -d "{\"state\":\"closed\"}"
```

Reopen an issue:

```bash
curl -X PATCH http://localhost:8000/issues/1 \
  -H "Content-Type: application/json" \
  -d "{\"state\":\"open\"}"
```

GitHub does not provide issue deletion, so closing an issue is used as the assignment's delete operation.

### POST /issues/{number}/comments

Create a comment:

```bash
curl -X POST http://localhost:8000/issues/1/comments \
  -H "Content-Type: application/json" \
  -d "{\"body\":\"Test comment\"}"
```

### GET /issues/{number}/comments

List comments:

```bash
curl "http://localhost:8000/issues/1/comments?page=1&per_page=10"
```

The `Link` response header is forwarded for pagination.

### POST /webhook

Receive GitHub webhook deliveries.

Supported events:

```text
issues
issue_comment
ping
```

The endpoint validates:

```text
X-GitHub-Event
X-GitHub-Delivery
X-Hub-Signature-256
```

The HMAC-SHA256 signature is calculated from the raw request body using `WEBHOOK_SECRET` and compared with `hmac.compare_digest()`.

Responses:

```text
204 No Content → valid and supported delivery
400 Bad Request → unsupported event or missing delivery ID
401 Unauthorized → missing/invalid signature
```

Delivery IDs are stored in SQLite and used as the deduplication key.

### GET /events

Return recently processed webhook deliveries:

```bash
curl http://localhost:8000/events
```

Optional limit:

```bash
curl "http://localhost:8000/events?limit=5"
```

## Webhook Setup

GitHub needs a publicly reachable URL to call the local service. For local demonstrations, use a tunnel such as ngrok or Cloudflared.

Example:

```text
https://<public-tunnel>/webhook
```

In the GitHub repository:

```text
Settings → Webhooks → Add webhook
```

Use:

```text
Payload URL:
https://<public-tunnel>/webhook

Content type:
application/json

Secret:
same value as WEBHOOK_SECRET
```

Enable:

```text
Issues
Issue comments
```

Create or update an issue to generate a real webhook delivery.

GitHub's webhook delivery history can be used to inspect and redeliver an event.

## Persistence

Webhook metadata is stored locally in:

```text
events.db
```

Stored fields:

- delivery ID
- event type
- action
- issue number
- timestamp

The delivery ID is the primary key used for idempotent duplicate detection.

## Error Handling

GitHub API errors are translated into consistent gateway responses.

| GitHub result | Gateway result |
|---|---|
| `401` | `401 Unauthorized` |
| `403` | `403 Forbidden` |
| `403` + exhausted rate limit | `429 Too Many Requests` |
| `404` | `404 Not Found` |
| `429` | `429 Too Many Requests` |
| `5xx` | `503 Service Unavailable` |

Rate-limit responses preserve useful retry/reset information where available.

## Testing

### Unit Tests

Unit tests do not communicate with the live GitHub API.

```powershell
python -m pytest -m unit -v
```

Coverage:

```powershell
python -m pytest tests/unit --cov=app --cov-report=term-missing
```

The target is at least 80% unit-test line coverage.

Unit tests cover request validation, webhook signatures, tampered bodies, error mapping, rate limits, pagination parsing, GitHub client behavior, route behavior, webhook deduplication, and SQLite storage.

### Integration Tests

Integration tests communicate with the configured GitHub test repository:

```powershell
python -m pytest -m integration -v
```

The integration workflow covers:

```text
Create issue
    ↓
Get issue
    ↓
Update issue
    ↓
Close issue
    ↓
Reopen issue
    ↓
Create comment
    ↓
Get comments
```

### All Tests

```powershell
python -m pytest -v
```

## Linting

Run Ruff:

```powershell
python -m ruff check app tests
```

The CI workflow runs the same linting check.

## Docker

Build:

```powershell
docker build -t github-service .
```

Run:

```powershell
docker run --env-file .env -p 8000:8000 github-service
```

Open:

```text
http://localhost:8000/docs
```

The `.env` file is excluded from the Docker image.

For local SQLite persistence across container replacement:

```powershell
docker run --env-file .env -p 8000:8000 -v "${PWD}\events.db:/app/events.db" github-service
```

## Continuous Integration

GitHub Actions is defined in:

```text
.github/workflows/ci.yml
```

The CI workflow performs:

1. Checkout
2. Python setup
3. Dependency installation
4. Ruff linting
5. Unit tests
6. Coverage
7. Docker image build

Integration tests are kept separate because they modify and read the live GitHub test repository and require repository credentials.

## Security

- Secrets are loaded through environment variables.
- `.env` is excluded from Git.
- The GitHub PAT is scoped to the test repository.
- Webhook signatures use HMAC-SHA256.
- Signature comparison uses constant-time comparison.
- Secrets and raw webhook signatures are not logged.
- Webhook delivery IDs are used for deduplication.

## Submission Artifacts

The repository contains:

```text
openapi.yaml
README.md
DESIGN.md
Dockerfile
tests/
pytest.ini
requirements.txt
.github/workflows/ci.yml
```

A separate Word document should provide UI/API interaction screenshots and demonstrate the required issue operations, webhook processing, tests, Docker execution, and CI results.

## Author

Jin Ting Zhou
