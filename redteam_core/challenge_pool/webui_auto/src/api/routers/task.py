# -*- coding: utf-8 -*-

import os
from fastapi import APIRouter, Response, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from api.config import config


router = APIRouter(tags=["Challenge"])

@router.get("/task", summary="Challenge", description="Get UI automation challenge task")
async def get_task():

    

    return {"web_url": config.web_url}


_templates = Jinja2Templates(directory="./templates/html")


@router.get("/web", summary="Web UI", description="Get Web UI")
async def get_web_ui(request: Request):

    print(os.getcwd())

    return _templates.TemplateResponse(
        request=request, name="index.html", context={"id": id}
    )


__all__ = ["router"]
