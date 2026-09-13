# Author: Jin Ting Zhou
# FastAPI routes for GitHub Issues.

from fastapi import APIRouter, HTTPException, Response, status

from ..github_client import GitHubAPIError, github_client
from ..models import (
    CreateCommentRequest,
    CreateIssueRequest,
    UpdateIssueRequest,
)


router = APIRouter(
    prefix="/issues",
    tags=["Issues"],
)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_issue(request: CreateIssueRequest, response: Response):
    try:
        issue = github_client.create_issue(
            title=request.title,
            body=request.body,
            labels=request.labels,
        )

        response.headers["Location"] = f"/issues/{issue['number']}"

        return {
            "number": issue["number"],
            "html_url": issue["html_url"],
            "state": issue["state"],
            "title": issue["title"],
            "body": issue["body"],
            "labels": [
                label["name"]
                for label in issue.get("labels", [])
            ],
            "created_at": issue["created_at"],
            "updated_at": issue["updated_at"],
        }

    except GitHubAPIError as exc:
        raise map_github_error(exc)


@router.get("")
def list_issues(
    response: Response,
    state: str = "open",
    labels: str | None = None,
    page: int = 1,
    per_page: int = 30,
):
    if state not in {"open", "closed", "all"}:
        raise HTTPException(
            status_code=400,
            detail="state must be open, closed, or all",
        )

    if page < 1:
        raise HTTPException(
            status_code=400,
            detail="page must be at least 1",
        )

    if per_page < 1 or per_page > 100:
        raise HTTPException(
            status_code=400,
            detail="per_page must be between 1 and 100",
        )

    try:
        github_response = github_client.list_issues(
            state=state,
            labels=labels,
            page=page,
            per_page=per_page,
        )

        if "link" in github_response.headers:
            response.headers["Link"] = (
                github_response.headers["link"]
            )

        issues = github_response.json()

        return [
            {
                "number": issue["number"],
                "html_url": issue["html_url"],
                "state": issue["state"],
                "title": issue["title"],
                "body": issue["body"],
                "labels": [
                    label["name"]
                    for label in issue.get("labels", [])
                ],
                "created_at": issue["created_at"],
                "updated_at": issue["updated_at"],
            }
            for issue in issues
        ]

    except GitHubAPIError as exc:
        raise map_github_error(exc)


@router.get("/{number}")
def get_issue(number: int):
    try:
        issue = github_client.get_issue(number)

        return {
            "number": issue["number"],
            "html_url": issue["html_url"],
            "state": issue["state"],
            "title": issue["title"],
            "body": issue["body"],
            "labels": [
                label["name"]
                for label in issue.get("labels", [])
            ],
            "created_at": issue["created_at"],
            "updated_at": issue["updated_at"],
        }

    except GitHubAPIError as exc:
        raise map_github_error(exc)


@router.patch("/{number}")
def update_issue(
    number: int,
    request: UpdateIssueRequest,
):
    if (
        request.title is None
        and request.body is None
        and request.state is None
    ):
        raise HTTPException(
            status_code=400,
            detail="At least one field must be provided",
        )

    try:
        issue = github_client.update_issue(
            number=number,
            title=request.title,
            body=request.body,
            state=request.state,
        )

        return {
            "number": issue["number"],
            "html_url": issue["html_url"],
            "state": issue["state"],
            "title": issue["title"],
            "body": issue["body"],
            "labels": [
                label["name"]
                for label in issue.get("labels", [])
            ],
            "created_at": issue["created_at"],
            "updated_at": issue["updated_at"],
        }

    except GitHubAPIError as exc:
        raise map_github_error(exc)


@router.post(
    "/{number}/comments",
    status_code=status.HTTP_201_CREATED,
)
def create_comment(
    number: int,
    request: CreateCommentRequest,
):
    try:
        comment = github_client.create_comment(
            number=number,
            body=request.body,
        )

        return {
            "id": comment["id"],
            "body": comment["body"],
            "user": comment["user"]["login"],
            "created_at": comment["created_at"],
            "html_url": comment["html_url"],
        }

    except GitHubAPIError as exc:
        raise map_github_error(exc)

@router.get("/{number}/comments")
def list_comments(
    response: Response,
    number: int,
    page: int = 1,
    per_page: int = 30,
):
    if page < 1:
        raise HTTPException(
            status_code=400,
            detail="page must be at least 1",
        )

    if per_page < 1 or per_page > 100:
        raise HTTPException(
            status_code=400,
            detail="per_page must be between 1 and 100",
        )

    try:
        github_response = github_client.list_comments(
            number=number,
            page=page,
            per_page=per_page,
        )

        if "link" in github_response.headers:
            response.headers["Link"] = (
                github_response.headers["link"]
            )

        comments = github_response.json()

        return [
            {
                "id": comment["id"],
                "body": comment["body"],
                "user": comment["user"]["login"],
                "created_at": comment["created_at"],
                "html_url": comment["html_url"],
            }
            for comment in comments
        ]

    except GitHubAPIError as exc:
        raise map_github_error(exc)


def map_github_error(
    exc: GitHubAPIError,
) -> HTTPException:

    if exc.status_code == 401:
        return HTTPException(
            status_code=401,
            detail={
                "code": "GITHUB_UNAUTHORIZED",
                "message": (
                    "GitHub authentication failed"
                ),
            },
        )

    if exc.status_code == 403:

        remaining = None
        reset = None

        if exc.headers:
            remaining = exc.headers.get(
                "X-RateLimit-Remaining"
            )
            reset = exc.headers.get(
                "X-RateLimit-Reset"
            )

        if remaining == "0":
            detail = {
                "code": "GITHUB_RATE_LIMIT",
                "message": (
                    "GitHub API rate limit exceeded"
                ),
            }

            if reset is not None:
                detail["reset_at"] = int(reset)

            return HTTPException(
                status_code=429,
                detail=detail,
            )

        return HTTPException(
            status_code=403,
            detail={
                "code": "GITHUB_FORBIDDEN",
                "message": (
                    "GitHub denied access to the repository"
                ),
            },
        )

    if exc.status_code == 404:
        return HTTPException(
            status_code=404,
            detail={
                "code": "ISSUE_NOT_FOUND",
                "message": exc.message,
            },
        )

    if exc.status_code == 429:
        retry_after = None

        if exc.headers:
            retry_after = exc.headers.get(
                "Retry-After"
            )

        detail = {
            "code": "GITHUB_RATE_LIMIT",
            "message": exc.message,
        }

        if retry_after:
            detail["retry_after"] = int(retry_after)

        headers = {}

        if retry_after:
            headers["Retry-After"] = retry_after

        return HTTPException(
            status_code=429,
            detail=detail,
            headers=headers,
        )

    if 500 <= exc.status_code <= 599:
        return HTTPException(
            status_code=503,
            detail={
                "code": "GITHUB_UNAVAILABLE",
                "message": (
                    "GitHub is temporarily unavailable"
                ),
            },
        )

    return HTTPException(
        status_code=400,
        detail={
            "code": "GITHUB_ERROR",
            "message": exc.message,
        },
    )