# -*- coding: utf-8 -*-

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from api.config import config
from api.schemas.data_types import TaskPM


router = APIRouter(tags=["Challenge"])
_templates = Jinja2Templates(directory="./templates")


@router.get(
    "/task",
    summary="Get task",
    description="This endpoint returns the webpage URL for the challenge.",
    response_model=TaskPM,
)
async def get_task():
    _task = TaskPM(web_url=config.web.url)
    return _task


@router.get(
    "/web",
    summary="Serves the webpage",
    description="This endpoint serves the webpage for the challenge.",
    response_class=HTMLResponse,
)
async def get_web_ui(request: Request):
    _html_response = _templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"app_id": "APP_ID", "public_key": "PUBLIC_KEY"},
    )
    return _html_response


__all__ = ["router"]
