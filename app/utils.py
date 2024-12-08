from fastapi.templating import Jinja2Templates
from fastapi import Request
from pathlib import Path
from app.models import models

# Настройка шаблонов Jinja2
templates = Jinja2Templates(directory="app/templates")

def get_context(request: Request, files: list = None):
    return {
        "request": request,
        "current_user": getattr(request.state, "current_user", None),
        "files": files
    }

def get_user_upload_dir(user: models.User) -> Path:
    return Path("uploads") / str(user.username)  # Используем ID пользователя для создания уникальной директории