# Author: Jin Ting Zhou

import pytest
from pydantic import ValidationError

from app.models import (
    CreateIssueRequest,
    UpdateIssueRequest,
)

pytestmark = pytest.mark.unit

def test_missing_title():
    with pytest.raises(ValidationError):
        CreateIssueRequest()


def test_empty_title():
    with pytest.raises(ValidationError):
        CreateIssueRequest(title="")


def test_invalid_state():
    with pytest.raises(ValidationError):
        UpdateIssueRequest(
            state="banana"
        )


def test_valid_state():
    request = UpdateIssueRequest(
        state="closed"
    )

    assert request.state == "closed"


def test_valid_create_issue():
    request = CreateIssueRequest(
        title="Test issue",
        body="Test body",
        labels=["bug"],
    )

    assert request.title == "Test issue"
    assert request.body == "Test body"
    assert request.labels == ["bug"]