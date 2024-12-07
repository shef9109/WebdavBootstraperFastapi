from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from jose import jwt
from starlette.staticfiles import StaticFiles

import app.resources.crud as crud
from app.database.db import Base, engine
from app.resources.auth import SECRET_KEY, ALGORITHM
from app.resources.auth import get_db
from app.routers import auth, users, files

app = FastAPI(
    title="Мой FastAPI проект",
    description="Описание вашего проекта",
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
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Монтирование роутеров
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(files.router)


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
