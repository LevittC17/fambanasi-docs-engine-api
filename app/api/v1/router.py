"""
API v1 main router.

Aggregates all API endpoint routers and provides versioned API structure.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    documents,
    drafts,
    media,
    metadata,
    navigation,
    search,
    webhooks,
)

# Create main API router
api_router = APIRouter()

# Include endpoint routers
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Authentication"],
)

api_router.include_router(
    documents.router,
    prefix="/documents",
    tags=["Documents"],
)

api_router.include_router(
    drafts.router,
    prefix="/drafts",
    tags=["Drafts"],
)

api_router.include_router(
    metadata.router,
    prefix="/metadata",
    tags=["Metadata"],
)

api_router.include_router(
    navigation.router,
    prefix="/navigation",
    tags=["Navigation"],
)

api_router.include_router(
    search.router,
    prefix="/search",
    tags=["Search"],
)

api_router.include_router(
    media.router,
    prefix="/media",
    tags=["Media"],
)

api_router.include_router(
    webhooks.router,
    prefix="/webhooks",
    tags=["Webhooks"],
)
