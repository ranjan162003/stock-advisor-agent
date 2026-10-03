"""Collects every route module under the `/api` prefix."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import (
    health_routes,
    provider_routes,
    recommendation_routes,
    stock_universe_routes,
    watchlist_routes,
)

api_router = APIRouter(prefix="/api")
api_router.include_router(health_routes.router)
api_router.include_router(provider_routes.router)
api_router.include_router(recommendation_routes.router)
api_router.include_router(watchlist_routes.router)
api_router.include_router(stock_universe_routes.router)
