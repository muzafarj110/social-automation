"""Approval (inbox) request/response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class GenerateApprovalRequest(BaseModel):
    """Draft an action via the Hub and queue it for approval.

    `params` is passed straight through to the Hub endpoint for the kind
    (field names depend on the Hub's schema, e.g. comment → post_url/angle).
    `context` holds targeting info used when the action is sent/executed
    (e.g. comment_id + organization_urn for a company-page reply via Zernio).
    """

    kind: str = Field(..., pattern="^(comment|dm|outreach|profile)$")
    account_id: int | None = None
    params: dict[str, Any] = Field(default_factory=dict)
    context: dict[str, Any] | None = None
    # Only honored for company-page comment replies (the one compliant path):
    # generate AND post the reply via Zernio in one step, no manual approval.
    auto_send: bool = False


class EditApprovalRequest(BaseModel):
    draft_text: str = Field(..., min_length=1)


class ApprovalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    account_id: int | None
    kind: str
    ai_payload: dict[str, Any] | None
    draft_text: str | None
    context: dict[str, Any] | None
    status: str
    executed_via: str | None
    error: str | None
    created_at: datetime
    resolved_at: datetime | None
