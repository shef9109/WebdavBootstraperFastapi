from fastapi import FastAPI, Request, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from jose import jwt
from starlette.staticfiles import StaticFiles
import os
import re
import inspect
import importlib

from app.resources import crud
from app.database.db import Base, engine
from app.resources.auth import SECRET_KEY, ALGORITHM
from app.resources.auth import get_db
from app.controllers import auth, users, files

python_controller_mask = re.compile(r'^(?P<Name>[^_]\w+)\.py$')
python_controller_class_mask = re.compile(r'^(?P<Name>[^_]\w+)Controller$')
python_action_mask = re.compile(r'^(?P<Name>[^_]\w+)Action$')
kebab_case_converter = re.compile(r'((?<=[a-z0-9])[A-Z]|(?!^)[A-Z](?=[a-z]))')


app = FastAPI(
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

def bootstrap_controllers():
    controller_files = os.listdir('app/controllers')
    controller_model_names = list(map(lambda f:python_controller_mask.match(f).group('Name'), filter(python_controller_mask.match, controller_files)))
    modules = __import__('app.controllers', fromlist=controller_model_names)
    controller_modules = {controller_module:getattr(modules, controller_module) for controller_module in controller_model_names}

    controller_classes = {}

    for module_name, module in controller_modules.items():
        for name, cls in inspect.getmembers(module, inspect.isclass):
            if controller_name := python_controller_class_mask.match(name):
                controller_prefix = to_kebab_case(controller_name.group('Name'))
                if not controller_prefix.startswith('/'):
                    controller_prefix = f'/{controller_prefix}'
                router = APIRouter(prefix=controller_prefix, tags=[name])
                controller_classes[name] = cls
                for func_name, func in inspect.getmembers(cls, inspect.isfunction):
                    if action_name := python_action_mask.match(func_name):
                        router.add_api_route(path=f'/{to_kebab_case(action_name.group('Name'))}', endpoint=func)
                        print((f'Модуль найден: {func_name} в контролере {name}'))
                        print(f'{to_kebab_case(controller_name.group('Name'))}/{to_kebab_case(action_name.group('Name'))}')
                app.include_router(router)
    return controller_classes

# if __name__ == "__main__":
bootstrap_controllers()