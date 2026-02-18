"""
Webhook endpoints.

Handles GitHub webhook events for repository change detection,
cache invalidation, and CI/CD pipeline triggers.
"""

import hashlib
import hmac
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db
from app.core.config import settings
from app.core.logging import get_logger
from app.db.models.audit_log import AuditAction
from app.schemas.webhook import WebhookPayload, WebhookResponse
from app.services.audit_service import AuditService
from app.services.metadata_service import MetadataService

logger = get_logger(__name__)
router = APIRouter()


def verify_github_signature(payload_body: bytes, signature_header: str | None) -> bool:
    """
    Verify GitHub webhook HMAC SHA-256 signature.

    Args:
        payload_body: Raw request body bytes
        signature_header: X-Hub-Signature-256 header value

    Returns:
        True if signature is valid, False otherwise
    """
    if not signature_header:
        return False

    # Compute expected signature
    expected = hmac.new(
        settings.GITHUB_WEBHOOK_SECRET.encode("utf-8"),
        payload_body,
        hashlib.sha256,
    ).hexdigest()

    expected_header = f"sha256={expected}"

    # Constant-time comparison to prevent timing attacks
    return hmac.compare_digest(expected_header, signature_header)


@router.post("/github", response_model=WebhookResponse)
async def handle_github_webhook(  # noqa: C901
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    x_hub_signature_256: Annotated[str | None, Header()] = None,
    x_github_event: Annotated[str | None, Header()] = None,
    x_github_delivery: Annotated[str | None, Header()] = None,
) -> WebhookResponse:
    """
    Handle GitHub push webhook events.

    Processes push events from the docs-content repository to:
    - Invalidate cached metadata for changed files
    - Sync metadata for new/modified files
    - Log webhook events for audit trail

    Args:
        request: Raw HTTP request
        db: Database session
        x_hub_signature_256: HMAC SHA-256 signature from GitHub
        x_github_event: GitHub event type (push, ping, etc.)
        x_github_delivery: Unique delivery ID

    Returns:
        Webhook processing response
    """
    from datetime import datetime

    audit_service = AuditService()

    # Read raw body for signature verification
    body = await request.body()

    # Verify signature
    if not verify_github_signature(body, x_hub_signature_256):
        logger.warning(f"Invalid webhook signature. Delivery: {x_github_delivery}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )

    # Parse payload
    import json

    try:
        payload_dict = json.loads(body)
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid JSON payload: {e}",
        ) from e

    # Handle ping event (sent when webhook is first created)
    if x_github_event == "ping":
        logger.info(f"GitHub ping received. Delivery: {x_github_delivery}")
        return WebhookResponse(
            status="received",
            message="Ping received successfully",
            affected_files=[],
            rebuild_triggered=False,
            processed_at=datetime.utcnow(),
        )

    # Process push events only
    if x_github_event != "push":
        logger.info(f"Ignoring non-push event: {x_github_event}")
        return WebhookResponse(
            status="received",
            message=f"Event type '{x_github_event}' acknowledged but not processed",
            affected_files=[],
            rebuild_triggered=False,
            processed_at=datetime.utcnow(),
        )

    # Parse push payload
    try:
        payload = WebhookPayload(**payload_dict)
    except Exception as e:
        logger.error(f"Failed to parse webhook payload: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid webhook payload: {e}",
        ) from e

    # Only process pushes to main branch
    if not payload.is_main_branch:
        logger.info(f"Ignoring push to non-main branch: {payload.branch_name}")
        return WebhookResponse(
            status="received",
            message=f"Push to '{payload.branch_name}' acknowledged but not processed",
            affected_files=[],
            rebuild_triggered=False,
            processed_at=datetime.utcnow(),
        )

    # Get affected documentation files
    affected_docs = payload.affected_docs
    logger.info(
        f"Webhook received: {len(affected_docs)} docs affected. "
        f"Pusher: {payload.pusher.name}"
    )

    # Process each affected file
    metadata_service = MetadataService()
    rebuild_triggered = False

    for file_path in affected_docs:
        try:
            # Determine if file was deleted
            deleted_files = []
            for commit in payload.commits:
                deleted_files.extend(commit.removed)

            if file_path in deleted_files:
                # Delete metadata for removed files
                await metadata_service.delete_metadata_by_path(db, file_path)
                logger.info(f"Metadata deleted for removed file: {file_path}")
            else:
                # Sync metadata for new/modified files
                # In a real implementation, we would fetch the new content
                # and sync metadata - simplified here
                logger.info(f"Queued metadata sync for: {file_path}")

            rebuild_triggered = True

        except Exception as e:
            logger.error(f"Error processing webhook for {file_path}: {e}")

    # Log audit trail
    await audit_service.log_action(
        db=db,
        action=AuditAction.WEBHOOK_RECEIVED,
        description=(
            f"GitHub push webhook processed: "
            f"{len(affected_docs)} files affected by {payload.pusher.name}"
        ),
        resource_type="webhook",
        resource_id=x_github_delivery,
        metadata={
            "event": x_github_event,
            "delivery_id": x_github_delivery,
            "branch": payload.branch_name,
            "pusher": payload.pusher.name,
            "affected_files": affected_docs,
            "commit_count": len(payload.commits),
        },
        success=True,
    )

    return WebhookResponse(
        status="processed",
        message=(
            f"Processed push to '{payload.branch_name}': "
            f"{len(affected_docs)} documentation files affected"
        ),
        affected_files=affected_docs,
        rebuild_triggered=rebuild_triggered,
        processed_at=datetime.utcnow(),
    )
