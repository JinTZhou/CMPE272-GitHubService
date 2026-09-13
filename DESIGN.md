# Design Note — GitHub Issues Gateway

## 1. Architecture

The GitHub Issues Gateway is implemented as a FastAPI service that exposes a custom HTTP API over the GitHub REST API.

The main request flow is:

```text
Client
  |
  v
FastAPI Route
  |
  v
GitHubClient
  |
  v
GitHub REST API
```

Webhook processing follows a separate path:

```text
GitHub
  |
  v
POST /webhook
  |
  v
HMAC-SHA256 Verification
  |
  v
Delivery-ID Deduplication
  |
  v
SQLite Event Store
```

The application keeps HTTP routing, GitHub communication, webhook processing, and persistence as separate responsibilities. Configuration and credentials are supplied through environment variables.

## 2. Error Mapping and Reliability

The gateway translates GitHub errors into consistent API responses:

| GitHub result | Gateway result |
|---|---|
| `401` | `401 Unauthorized` |
| `403` | `403 Forbidden` |
| `403` + `X-RateLimit-Remaining: 0` | `429 Too Many Requests` |
| `404` | `404 Not Found` |
| `429` | `429 Too Many Requests` |
| `5xx` | `503 Service Unavailable` |
| Other client errors | `400 Bad Request` |

Rate-limit information such as `Retry-After` or the GitHub reset timestamp is preserved where available. This gives API clients useful information without exposing the full third-party response as the public contract.

The `/healthz` endpoint provides a simple service health check.

## 3. Pagination Strategy

The gateway supports `page` and `per_page` parameters for issue and comment listing.

`per_page` is validated to a maximum of 100, and the requested values are passed to GitHub.

GitHub returns pagination metadata in the HTTP `Link` response header. The gateway forwards this header to its own clients. This preserves GitHub pagination semantics without requiring the gateway to maintain page state.

A separate pagination parsing utility is tested independently so pagination logic can be verified without contacting GitHub.

## 4. Webhook Validation

The `/webhook` endpoint accepts:

```text
issues
issue_comment
ping
```

The service reads the raw request body before parsing the JSON payload. It calculates the expected signature using:

```text
HMAC-SHA256(WEBHOOK_SECRET, raw request body)
```

The expected signature is compared with `X-Hub-Signature-256` using `hmac.compare_digest()`.

Invalid signatures return `401`. Unsupported events and missing delivery IDs return `400`. A valid supported delivery is acknowledged with `204 No Content`.

Using the raw request body ensures the bytes used for signature verification are the same bytes that were signed.

## 5. Webhook Deduplication and Persistence

GitHub supplies a delivery identifier through:

```text
X-GitHub-Delivery
```

The SQLite event table stores this value as its primary key.

Processing is therefore:

```text
Receive delivery ID
       |
       v
Already stored?
   /       \
 yes       no
 |          |
 v          v
204       store event
            |
            v
           204
```

A duplicate delivery is acknowledged without being inserted or processed again. This provides idempotent webhook handling and supports safe redelivery.

SQLite was selected because it requires no separate database server and is sufficient for a small local assignment service. A production implementation would normally use a durable managed database and a more scalable event-processing design.

## 6. Security Trade-offs

The GitHub token and webhook secret are stored outside source code and supplied through environment variables. The GitHub token should be a Fine-Grained PAT limited to the configured test repository with the required Issues permission.

Webhook authentication uses HMAC-SHA256 and constant-time comparison. Secrets and raw signatures are not logged.

For local demonstrations, a public tunnel may expose `/webhook` to GitHub. This creates additional public exposure, so the webhook secret should remain private and can be rotated after demonstrations.

The assignment uses a local SQLite store because of its simplicity. This is appropriate for the expected scale but would not by itself provide the durability, availability, and concurrency characteristics expected of a production webhook platform.

## 7. Testing Strategy

The test suite separates isolated unit tests from live integration tests.

Unit tests use mocked or local dependencies and cover:

- request validation
- HMAC signature validation
- tampered webhook bodies
- GitHub error mapping
- rate-limit handling
- pagination parsing
- GitHub client methods
- API routes
- webhook deduplication
- SQLite persistence

Integration tests communicate with the configured GitHub repository and verify the end-to-end issue/comment workflow:

```text
Create → Read → Update → Close → Reopen → Comment → Read comments
```

This separation keeps routine tests fast and prevents unit-test execution from modifying the live test repository.

## 8. Deployment and CI

The service is packaged as a Docker image so the runtime and Python dependencies are reproducible.

GitHub Actions performs linting, unit tests, coverage, and a Docker build on repository changes.

Integration tests are intentionally separate from normal CI because they require credentials and communicate with a live GitHub repository.

## 9. Rubric Alignment

- **Correctness:** Custom HTTP endpoints implement issue CRUD-style operations and comments.
- **Webhooks:** Supported GitHub events are validated, persisted, acknowledged, and deduplicated.
- **OpenAPI quality:** `openapi.yaml` documents the public API using OpenAPI 3.1.
- **Testing:** Unit and integration tests cover positive and negative paths, including external API mocking.
- **Reliability:** Pagination, rate limits, GitHub errors, and health checking are addressed.
- **Security:** Environment-based secrets, limited GitHub permissions, HMAC validation, and constant-time comparison are used.
- **DevEx:** README documentation, Docker, test commands, and CI are provided.
- **Code quality:** Application code and tests are separated by responsibility, with linting through Ruff.
