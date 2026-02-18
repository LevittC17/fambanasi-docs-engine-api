"""
Integration tests for document API endpoints.

Tests the full request/response cycle including authentication,
validation, and service orchestration.
"""

from unittest.mock import patch

import pytest
from httpx import AsyncClient

from app.core.security import create_access_token
from app.db.models.user import User


class TestGetDocument:
    """Integration tests for GET /documents/{path}."""

    @pytest.mark.asyncio
    async def test_get_document_success(self, async_client: AsyncClient, mock_github_service):
        """Test successful document retrieval."""
        with patch(
            "app.services.document_service.GitHubService",
            return_value=mock_github_service,
        ):
            response = await async_client.get("/api/v1/documents/docs/test.md")

        assert response.status_code == 200
        data = response.json()
        assert "path" in data
        assert "content" in data
        assert "title" in data

    @pytest.mark.asyncio
    async def test_get_document_with_branch(self, async_client: AsyncClient, mock_github_service):
        """Test document retrieval with specific branch."""
        with patch(
            "app.services.document_service.GitHubService",
            return_value=mock_github_service,
        ):
            response = await async_client.get(
                "/api/v1/documents/docs/test.md", params={"branch": "feature/new-docs"}
            )

        assert response.status_code == 200


class TestCreateDocument:
    """Integration tests for POST /documents/."""

    @pytest.mark.asyncio
    async def test_create_document_requires_auth(self, async_client: AsyncClient):
        """Test that document creation requires authentication."""
        response = await async_client.post(
            "/api/v1/documents/",
            json={
                "path": "docs/new.md",
                "title": "New Doc",
                "content": "# New\n\nContent",
            },
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_document_requires_editor(
        self,
        async_client: AsyncClient,
        viewer_user: User,
    ):
        """Test that document creation requires Editor role."""
        token = create_access_token(
            {
                "sub": str(viewer_user.id),
                "role": viewer_user.role.value,
            }
        )

        response = await async_client.post(
            "/api/v1/documents/",
            json={
                "path": "docs/new.md",
                "title": "New Doc",
                "content": "# New\n\nContent",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_create_document_success(
        self,
        async_client: AsyncClient,
        editor_user: User,
        mock_github_service,
        db_session,
    ):
        """Test successful document creation by editor."""
        token = create_access_token(
            {
                "sub": str(editor_user.id),
                "role": editor_user.role.value,
            }
        )

        with patch(
            "app.services.document_service.GitHubService",
            return_value=mock_github_service,
        ):
            response = await async_client.post(
                "/api/v1/documents/",
                json={
                    "path": "docs/new-guide.md",
                    "title": "New Guide",
                    "content": "# New Guide\n\nContent here.",
                    "branch": "main",
                },
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_create_document_invalid_path(
        self,
        async_client: AsyncClient,
        editor_user: User,
    ):
        """Test that invalid path is rejected."""
        token = create_access_token(
            {
                "sub": str(editor_user.id),
                "role": editor_user.role.value,
            }
        )

        response = await async_client.post(
            "/api/v1/documents/",
            json={
                "path": "docs/../../../etc/passwd",
                "title": "Hack",
                "content": "# Hack",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_document_missing_content(
        self,
        async_client: AsyncClient,
        editor_user: User,
    ):
        """Test that empty content is rejected."""
        token = create_access_token(
            {
                "sub": str(editor_user.id),
                "role": editor_user.role.value,
            }
        )

        response = await async_client.post(
            "/api/v1/documents/",
            json={
                "path": "docs/empty.md",
                "title": "Empty Doc",
                "content": "   ",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 422


class TestDeleteDocument:
    """Integration tests for DELETE /documents/{path}."""

    @pytest.mark.asyncio
    async def test_delete_requires_editor(
        self,
        async_client: AsyncClient,
        viewer_user: User,
    ):
        """Test that deletion requires at least Editor role."""
        token = create_access_token(
            {
                "sub": str(viewer_user.id),
                "role": viewer_user.role.value,
            }
        )

        response = await async_client.delete(
            "/api/v1/documents/docs/test.md",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 403
