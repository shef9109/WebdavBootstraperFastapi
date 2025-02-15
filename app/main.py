from typing import Callable

from fastapi import FastAPI, Request, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from jose import jwt
from starlette.staticfiles import StaticFiles
import os
import re
import inspect
from functools import partial
from operator import is_not
import importlib

from app.resources import crud
from app.database.db import Base, engine
from app.resources.auth import SECRET_KEY, ALGORITHM
from app.resources.auth import get_db
from app.controllers import auth, users, files

python_controller_mask = re.compile(r'^(?P<Name>[^_]\w+)\.py$')
python_controller_class_mask = re.compile(r'^(?P<Name>[^_]\w+)Controller$')
python_action_mask = re.compile(r'^(?P<Type>(Post|Get|Put|Options|Head|Delete|Patch|))(?P<Name>[^_]\w+)Action$')
kebab_case_converter = re.compile(r'((?<=[a-z0-9])[A-Z]|(?!^)[A-Z](?=[a-z]))')


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

# Монтирование роутеров
# app.include_router(auth.router)
# app.include_router(users.router)
# app.include_router(files.router)


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

def to_kebab_case(func_name: str) -> str:
    return kebab_case_converter.sub(r'-\1', func_name).lower()

def get_action_type(func: Callable) -> str:
    docstring = func.__doc__
    if docstring:
        if 'Post' in docstring:
            return 'POST'
        elif 'Put' in docstring:
            return 'PUT'
        elif 'Patch' in docstring:
            return 'PATCH'
        elif 'Delete' in docstring:
            return 'DELETE'
        elif 'Options' in docstring:
            return 'OPTIONS'
        elif 'Head' in docstring:
            return 'HEAD'
    return 'GET'

def register_action(router: APIRouter, name: str, func: Callable) -> None:
    action_name = python_action_mask.match(name).group('Name')
    action_type = python_action_mask.match(name).group('Type').upper()
    if action_type == '':
        action_type = get_action_type(func)
    print(action_type, action_name)
    router.add_api_route(path=f'/{to_kebab_case(action_name)}', endpoint=func, methods=[action_type,])
    if action_name == 'Index':
        router.add_api_route(path='/', endpoint=func, methods=[action_type,])

def create_routers(name: str) -> list[APIRouter]:
    controller_name = python_controller_class_mask.match(name).group('Name')
    routers = [APIRouter(
        prefix=f"/{to_kebab_case(controller_name)}" if not to_kebab_case(controller_name).startswith(
            '/') else to_kebab_case(controller_name),
        tags=[name])]
    if controller_name == 'Index':
        routers.append(APIRouter(prefix='', tags=[name]))
    return routers

def bootstrap_controllers(app_instance: FastAPI):
    controller_files = os.listdir('app/controllers') # Список всех  файлов в дириктории
    controller_model_names = list(map(lambda f:python_controller_mask.match(f).group('Name'), filter(python_controller_mask.match, controller_files))) # Имена .py модулей из дирикторивских модулей
    modules = __import__('app.controllers', fromlist=controller_model_names) # Перечень самих пакетов модулей
    controller_modules = {controller_module:getattr(modules, controller_module) for controller_module in controller_model_names} # Словарь с именем модуля и ссылкой на него

    # Фильтрованный список контроллеров по имени и классу
    all_controllers = filter(
        lambda name_cls: python_controller_class_mask.match(name_cls[0]),
        ((name, cls) for module in controller_modules.values() for name, cls in
         inspect.getmembers(module, inspect.isclass))
    )

    # Создание контроллера из имени и класса
    # create_router = lambda name, cls: (
    #     controller_name := python_controller_class_mask.match(name).group('Name'),
    #     router := APIRouter(
    #         prefix=f"/{to_kebab_case(controller_name)}" if not to_kebab_case(controller_name).startswith(
    #             '/') else to_kebab_case(controller_name),
    #         tags=[name]
    #     ),
    #     list(map(lambda elem: register_action(router, *elem),
    #         filter(lambda nf: python_action_mask.match(nf[0]), inspect.getmembers(cls, inspect.isfunction)))),
    #     app.include_router(router),
    #     cls
    # )
    controller_routers = [(name, cls, create_routers(name)) for name, cls in all_controllers]
    for name, cls, routers in controller_routers:
        actions = filter(lambda nf: python_action_mask.match(nf[0]), inspect.getmembers(cls, inspect.isfunction))
        for router in routers:
            for action in actions:
                print(action)
                register_action(router, action[0], action[1])
            app_instance.include_router(router)


    return 1

# if __name__ == "__main__":
bootstrap_controllers(app)