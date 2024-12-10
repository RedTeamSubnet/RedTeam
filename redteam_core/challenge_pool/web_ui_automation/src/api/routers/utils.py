# -*- coding: utf-8 -*-

from fastapi import APIRouter, Response


router = APIRouter(tags=["Utils"])


@router.get("/", summary="Base", description="Base path for all API endpoints.")
async def get_base():
    return {"message": "Welcome to the challenger API!"}


@router.get(
    "/ping", summary="Ping", description="Check if the service is up and running."
)
async def get_ping(response: Response):
    response.headers["Cache-Control"] = "no-cache"
    return {"message": "Pong!"}


@router.get(
    "/health",
    summary="Health",
    description="Check health of all related backend services.",
)
async def get_health(response: Response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    return {"status": "healthy"}


__all__ = ["router"]
