"""
Integration tests for draft API endpoints.

Tests the draft creation, review workflow, and publishing.
"""

import pytest
from httpx import AsyncClient

from unittest.mock import patch
from app.core.security import create_access_token
from app.db.models.draft import DraftStatus
from app.db.models.user import User


@pytest.fixture(autouse=True)
def mock_external_services():
    """Mock GitHub and Document services to prevent unmocked API calls in CI."""
    with (
        patch("app.services.draft_service.DocumentService"),
        patch("app.api.v1.endpoints.drafts.DraftService.publish_draft") as mock_publish,
    ):
        mock_publish.return_value = {"status": "success", "message": "Mocked publish"}
        yield


class TestCreateDraft:
    """Integration tests for POST /drafts/."""

    @pytest.mark.asyncio
    async def test_create_draft_requires_auth(self, async_client: AsyncClient):
        """Test that draft creation requires authentication."""
        response = await async_client.post(
            "/api/v1/drafts/",
            json={
                "title": "My Draft",
                "content": "# Draft\n\nContent",
                "target_path": "docs/my-draft.md",
            },
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_draft_success(
        self,
        async_client: AsyncClient,
        viewer_user: User,
    ):
        """Test successful draft creation by any authenticated user."""
        token = create_access_token(
            {
                "sub": str(viewer_user.id),
                "role": viewer_user.role.value,
            }
        )

        response = await async_client.post(
            "/api/v1/drafts/",
            json={
                "title": "My Draft",
                "content": "# Draft\n\nContent here.",
                "target_path": "docs/my-draft.md",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "My Draft"
        assert data["status"] == DraftStatus.DRAFT.value
        assert "id" in data

    @pytest.mark.asyncio
    async def test_create_draft_invalid_target_path(
        self,
        async_client: AsyncClient,
        viewer_user: User,
    ):
        """Test that invalid target path is rejected."""
        token = create_access_token(
            {
                "sub": str(viewer_user.id),
                "role": viewer_user.role.value,
            }
        )

        response = await async_client.post(
            "/api/v1/drafts/",
            json={
                "title": "Hack",
                "content": "# Hack",
                "target_path": "docs/../etc/passwd",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 422


class TestDraftWorkflow:
    """Integration tests for the draft review workflow."""

    @pytest.mark.asyncio
    async def test_full_draft_workflow(
        self,
        async_client: AsyncClient,
        viewer_user: User,
        editor_user: User,
        db_session,
    ):
        """
        Test the complete draft workflow:
        create -> submit -> review -> (publish skipped as it needs GitHub mock)
        """
        viewer_token = create_access_token(
            {
                "sub": str(viewer_user.id),
                "role": viewer_user.role.value,
            }
        )
        editor_token = create_access_token(
            {
                "sub": str(editor_user.id),
                "role": editor_user.role.value,
            }
        )

        # Step 1: Create draft
        create_resp = await async_client.post(
            "/api/v1/drafts/",
            json={
                "title": "Workflow Test",
                "content": "# Workflow\n\nTest content.",
                "target_path": "docs/workflow-test.md",
            },
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert create_resp.status_code == 201
        draft_id = create_resp.json()["id"]

        # Step 2: Submit for review
        submit_resp = await async_client.post(
            f"/api/v1/drafts/{draft_id}/submit",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert submit_resp.status_code == 200
        assert submit_resp.json()["status"] == DraftStatus.IN_REVIEW.value

        # Step 3: Approve (as editor)
        approve_resp = await async_client.post(
            f"/api/v1/drafts/{draft_id}/review",
            json={
                "status": DraftStatus.APPROVED.value,
                "review_comments": "Looks good!",
            },
            headers={"Authorization": f"Bearer {editor_token}"},
        )
        assert approve_resp.status_code == 200
        assert approve_resp.json()["status"] == DraftStatus.APPROVED.value

    @pytest.mark.asyncio
    async def test_viewer_cannot_review(
        self,
        async_client: AsyncClient,
        viewer_user: User,
        editor_user: User,
    ):
        """Test that viewer cannot approve/reject drafts."""
        viewer_token = create_access_token(
            {
                "sub": str(viewer_user.id),
                "role": viewer_user.role.value,
            }
        )

        # Create and submit draft as editor
        editor_token = create_access_token(
            {
                "sub": str(editor_user.id),
                "role": editor_user.role.value,
            }
        )

        create_resp = await async_client.post(
            "/api/v1/drafts/",
            json={
                "title": "Test Draft",
                "content": "# Test\n\nContent.",
                "target_path": "docs/test-draft.md",
            },
            headers={"Authorization": f"Bearer {editor_token}"},
        )
        draft_id = create_resp.json()["id"]

        # Submit
        await async_client.post(
            f"/api/v1/drafts/{draft_id}/submit",
            headers={"Authorization": f"Bearer {editor_token}"},
        )

        # Try to review as viewer
        review_resp = await async_client.post(
            f"/api/v1/drafts/{draft_id}/review",
            json={"status": DraftStatus.APPROVED.value},
            headers={"Authorization": f"Bearer {viewer_token}"},
        )

        assert review_resp.status_code == 403
