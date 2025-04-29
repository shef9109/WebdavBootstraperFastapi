from typing import Callable

from fastapi import FastAPI, Request, APIRouter
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from jose import jwt
from starlette.staticfiles import StaticFiles
import os
import re
import inspect
from functools import partial
from operator import is_not
import importlib
from types import ModuleType

from app.resources import crud
from app.database.db import Base, engine
from app.resources.auth import SECRET_KEY, ALGORITHM
from app.resources.auth import get_db
from app.controllers import auth, users, files
from app.utilis.bootstrap import bootstrap_controllers

python_controller_mask = re.compile(r'^(?P<Name>[^_]\w+)\.py$')
python_controller_class_mask = re.compile(r'^(?P<Name>[^_]\w+)Controller$')
python_action_mask = re.compile(r'^(?P<Type>(Post|Get|Put|Options|Head|Delete|Patch|))(?P<Name>[^_]\w+)Action$')
kebab_case_converter = re.compile(r'((?<=[a-z0-9])[A-Z]|(?!^)[A-Z](?=[a-z]))')
docstring_method_mask = re.compile(r'\s+(@method)\s+(?P<Type>(get|post|put|options))')
docstring_response_model_mask = re.compile(r'@response_model\s(?P<Name>\w+)')


app = FastAPI(
    debug=True,
    title="Webdav + Fastapi",
    version="1.0.0",
)

# Монтирование статических файлов
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Создаем таблицы в базе данных
Base.metadata.create_all(bind=engine)

# Настройка CORS
origins = [
    "http://localhost",
    "http://localhost:8000",
    "http://localhost:8081"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Глобальная зависимость для передачи current_user в шаблоны
@app.middleware("http")
async def add_current_user(request: Request, call_next):
    try:
        token = request.cookies.get("access_token")
        if token:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username: str | None = payload.get("sub")
            if username:
                db = get_db()
                db_session = next(db)
                user = crud.get_user_by_username(db_session, username=username)
                request.state.current_user = user
                db_session.close()
            else:
                request.state.current_user = None
        else:
            request.state.current_user = None
    except Exception as e:
        request.state.current_user = None
    response = await call_next(request)
    return response


bootstrap_controllers(app)
