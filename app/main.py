from datetime import timedelta

from fastapi import FastAPI, HTTPException, UploadFile, File, Request, Depends, Response
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import aiofiles
import os
from fastapi.security import OAuth2PasswordRequestForm
from jose import jwt
from sqlalchemy.orm import Session
from fastapi import Form
from starlette.staticfiles import StaticFiles

from app.database.db import Base, engine, SessionLocal
import app.models.models as models
import app.resources.crud as crud
import app.schemas.schemas as schemas
import app.resources.auth as auth
from app.resources.auth import create_access_token, get_current_user
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# Создаем таблицы в базе данных
Base.metadata.create_all(bind=engine)

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

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


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Глобальная зависимость для передачи current_user в шаблоны
@app.middleware("http")
async def add_current_user(request: Request, call_next):
    try:
        token = request.cookies.get("access_token")
        if token:
            payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
            username: str | None = payload.get("sub")
            if username:
                db = SessionLocal()
                user = crud.get_user_by_username(db, username=username)
                request.state.current_user = user
                db.close()
            else:
                request.state.current_user = None
        else:
            request.state.current_user = None
    except Exception as e:
        request.state.current_user = None
    response = await call_next(request)
    return response


# Добавление current_user в контекст шаблонов
def get_context(request: Request, files: list = None):
    return {
        "request": request,
        "current_user": getattr(request.state, "current_user", None),
        "files": files
    }


@app.post("/register/", response_model=schemas.UserResponse)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Имя пользователя уже используется")
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email уже зарегистрирован")
    return crud.create_user(db=db, user=user)


@app.post("/token/")
def login_for_access_token(response: Response, form_data: OAuth2PasswordRequestForm = Depends(),
                           db: Session = Depends(get_db)):
    user = crud.get_user_by_username(db, username=form_data.username)
    if not user or not crud.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Неправильные имя пользователя или пароль")
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=auth.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    return {"access_token": access_token, "token_type": "bearer"}


# Пример защищенного маршрута
@app.get("/users/me/", response_model=schemas.UserResponse)
def read_users_me(current_user: schemas.UserResponse = Depends(get_current_user)):
    return current_user


@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", get_context(request))


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", get_context(request))


@app.get("/logout", response_class=HTMLResponse)
async def logout_page():
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie(key="access_token")
    return response


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", get_context(request))


@app.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request):
    return templates.TemplateResponse("upload.html", get_context(request))


@app.get("/files", response_class=HTMLResponse)
async def list_files(request: Request, current_user: models.User = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    if not UPLOAD_DIR.exists():
        files = []
    else:
        files = [f.name for f in UPLOAD_DIR.iterdir() if f.is_file()]

    return templates.TemplateResponse("files.html", get_context(request, files))


@app.post("/upload/")
async def upload_file(file: UploadFile = File(...), current_user: models.User = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    upload_dir = Path("uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)
    upload_path = upload_dir / file.filename

    try:
        async with aiofiles.open(upload_path, 'wb') as out_file:
            content = await file.read()
            await out_file.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to upload file.")

    return {"info": f"File '{file.filename}' uploaded successfully."}


@app.get("/files/{filename}", response_class=FileResponse)
async def get_file(filename: str, current_user: models.User = Depends(get_current_user)):
    file_location = UPLOAD_DIR / filename
    if file_location.exists():
        return file_location
    raise HTTPException(status_code=404, detail="Файл не найден.")


@app.delete("/files/{filename}")
async def delete_file(filename: str, current_user: models.User = Depends(get_current_user)):
    file_location = UPLOAD_DIR / filename
    if file_location.exists():
        os.remove(file_location)
        return JSONResponse(content={"info": f"Файл '{filename}' успешно удален."})
    raise HTTPException(status_code=404, detail="Файл не найден.")

