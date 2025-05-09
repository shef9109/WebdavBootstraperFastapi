import re

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from jose import jwt
from starlette.staticfiles import StaticFiles

from app.database.db import Base, engine
from app.repositories import crud
from app.repositories.auth import SECRET_KEY, ALGORITHM
from app.repositories.auth import get_db
from app.utilis.bootstrap import bootstrap_controllers



app = FastAPI(
    debug=True,
    title="Webdav + Fastapi",
    version="1.0.0",
    docs_url=None,
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

# Локальный swagger
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title="My API",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        swagger_js_url="/static/swagger/swagger-ui-bundle.js",
        swagger_css_url="/static/swagger/swagger-ui.css",
        # swagger_favicon_url="/static/favicon-32x32.png",
    )


bootstrap_controllers(app)
