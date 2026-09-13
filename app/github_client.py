# Author: Jin Ting Zhou
# Handles communication with the GitHub REST API.

from typing import Any, Optional

import httpx

from .config import GITHUB_OWNER, GITHUB_REPO, GITHUB_TOKEN


class GitHubAPIError(Exception):
    """Represents an error returned by GitHub's API."""

    def __init__(
        self,
        status_code: int,
        message: str,
        response_body: Optional[dict[str, Any]] = None,
        headers: Optional[httpx.Headers] = None,
    ):
        self.status_code = status_code
        self.message = message
        self.response_body = response_body
        self.headers = headers

        super().__init__(message)


class GitHubClient:
    """Small wrapper around GitHub's REST API."""

    BASE_URL = "https://api.github.com"

    def __init__(
        self,
        token: str,
        owner: str,
        repo: str,
    ):
        self.token = token
        self.owner = owner
        self.repo = repo

        # Create one reusable HTTP client.
        self.client = httpx.Client(
            base_url=self.BASE_URL,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=10.0,
        )

    def _url(self, path: str) -> str:
        return f"/repos/{self.owner}/{self.repo}{path}"

    def _handle_response(
        self,
        response: httpx.Response,
    ) -> dict[str, Any]:

        if response.is_success:
            return response.json()

        try:
            body = response.json()
        except ValueError:
            body = {}

        message = body.get(
            "message",
            "GitHub API request failed",
        )

        # Rate limiting can appear as 429 or as 403 with
        # X-RateLimit-Remaining: 0.
        if self._is_rate_limited(response):
            message = (
                body.get(
                    "message",
                    "GitHub API rate limit exceeded",
                )
            )

        raise GitHubAPIError(
            status_code=response.status_code,
            message=message,
            response_body=body,
            headers=response.headers,
        )

    def create_issue(
        self,
        title: str,
        body: Optional[str] = None,
        labels: Optional[list[str]] = None,
    ) -> dict[str, Any]:

        payload: dict[str, Any] = {
            "title": title,
        }

        if body is not None:
            payload["body"] = body

        if labels is not None:
            payload["labels"] = labels

        response = self.client.post(
            self._url("/issues"),
            json=payload,
        )

        return self._handle_response(response)

    def get_issue(
        self,
        number: int,
    ) -> dict[str, Any]:

        response = self.client.get(
            self._url(f"/issues/{number}")
        )

        return self._handle_response(response)

    def update_issue(
        self,
        number: int,
        title: Optional[str] = None,
        body: Optional[str] = None,
        state: Optional[str] = None,
    ) -> dict[str, Any]:

        payload: dict[str, Any] = {}

        if title is not None:
            payload["title"] = title

        if body is not None:
            payload["body"] = body

        if state is not None:
            payload["state"] = state

        response = self.client.patch(
            self._url(f"/issues/{number}"),
            json=payload,
        )

        return self._handle_response(response)

    def create_comment(
        self,
        number: int,
        body: str,
    ) -> dict[str, Any]:

        response = self.client.post(
            self._url(f"/issues/{number}/comments"),
            json={"body": body},
        )

        return self._handle_response(response)

    def list_issues(
        self,
        state: str = "open",
        labels: Optional[str] = None,
        page: int = 1,
        per_page: int = 30,
    ) -> httpx.Response:

        params: dict[str, Any] = {
            "state": state,
            "page": page,
            "per_page": per_page,
        }

        if labels:
            params["labels"] = labels

        return self.client.get(
            self._url("/issues"),
            params=params,
        )

    def list_comments(
        self,
        number: int,
        page: int = 1,
        per_page: int = 30,
    ) -> httpx.Response:

        return self.client.get(
            self._url(f"/issues/{number}/comments"),
            params={
                "page": page,
                "per_page": per_page,
            },
        )

    def _is_rate_limited(
        self,
        response: httpx.Response,
    ) -> bool:
        """Determine whether a GitHub response represents a rate limit."""

        remaining = response.headers.get(
            "X-RateLimit-Remaining"
        )

        if remaining == "0":
            return True

        if response.status_code == 429:
            return True

        return False

    def close(self):
        """Close the underlying HTTP client."""
        self.client.close()


github_client = GitHubClient(
    token=GITHUB_TOKEN or "",
    owner=GITHUB_OWNER or "",
    repo=GITHUB_REPO or "",
)