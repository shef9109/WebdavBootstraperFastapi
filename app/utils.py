from fastapi.templating import Jinja2Templates
from fastapi import Request
from pathlib import Path

# Настройка шаблонов Jinja2
templates = Jinja2Templates(directory="app/templates")


def get_context(request: Request, files: list = None):
    return {
        "request": request,
        "current_user": getattr(request.state, "current_user", None),
        "files": files
    }
