# Author: Jin Ting Zhou
# Receives and validates GitHub webhook events.

import hashlib
import hmac
from datetime import datetime, timezone

from fastapi import APIRouter, Header, HTTPException, Query, Request, status

from ..config import WEBHOOK_SECRET
from ..storage.event_store import event_store

router = APIRouter(
    tags=["Webhooks"],
)




@router.post("/webhook", status_code=status.HTTP_204_NO_CONTENT)
async def receive_webhook(
    request: Request,
    x_github_event: str | None = Header(default=None),
    x_github_delivery: str | None = Header(default=None),
    x_hub_signature_256: str | None = Header(default=None),
):
    body = await request.body()

    verify_signature(
            body,
            x_hub_signature_256,
    )

    if x_github_event not in {
        "issues",
        "issue_comment",
        "ping",
    }:
        raise HTTPException(
            status_code=400,
            detail="Unsupported GitHub event",
        )

    if not x_github_delivery:
        raise HTTPException(
            status_code=400,
            detail="Missing X-GitHub-Delivery header",
        )

    if event_store.event_exists(x_github_delivery):
        return

    payload = await request.json()

    action = payload.get("action")
    issue = payload.get("issue")

    issue_number = None

    if issue:
        issue_number = issue.get("number")

    event_store.save_event(
        delivery_id=x_github_delivery,
        event=x_github_event,
        action=action,
        issue_number=issue_number,
        timestamp=datetime.now(
            timezone.utc
        ).isoformat(),
)

    print(
        f"Webhook received: "
        f"event={x_github_event}, "
        f"action={action}, "
        f"delivery={x_github_delivery}, "
        f"issue={issue_number}"
    )

@router.get("/events")
def list_events(
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
    )
):
    return event_store.get_events(limit=limit)




def verify_signature(
    body: bytes,
    signature: str | None,
) -> None:

    if not WEBHOOK_SECRET:
        raise HTTPException(
            status_code=500,
            detail="Webhook secret is not configured",
        )

    if not signature:
        raise HTTPException(
            status_code=401,
            detail="Missing webhook signature",
        )

    secret_bytes = WEBHOOK_SECRET.encode("utf-8")

    expected_hash = hmac.new(
        secret_bytes,
        body,
        hashlib.sha256,
    ).hexdigest()

    expected = f"sha256={expected_hash}"


    if not hmac.compare_digest(expected, signature):
        raise HTTPException(
            status_code=401,
            detail="Invalid webhook signature",
        )