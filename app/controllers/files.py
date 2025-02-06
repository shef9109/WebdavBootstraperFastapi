import io
import logging

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from starlette.responses import RedirectResponse

from app.models import models
from app.resources.auth import get_current_user
from app.utils import templates, get_context  # Импортируем новую функцию
from webdav.client import get_webdav_client, WEBDAV_OPTIONS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["files"]
)

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.resources import crud
from app.resources.auth import create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES, get_db
from app.resources.crud import verify_password

router = APIRouter(
    tags=["auth"],
)

class FilesController:
    @staticmethod
    def FileAction(response: Response, form_data: OAuth2PasswordRequestForm = Depends(),
                           db: Session = Depends(get_db)):
        user = crud.get_user_by_username(db, username=form_data.username)
        if not user or not verify_password(form_data.password, user.hashed_password):
            raise HTTPException(status_code=400, detail="Неправильные имя пользователя или пароль")
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.username}, expires_delta=access_token_expires
        )
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=False,
            samesite="lax",
            max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )
        return {"access_token": access_token, "token_type": "bearer"}
    def __str__(self):
        return f"{self.__class__.__name__} working for you <3"


@router.post("/token/")
def login_for_access_token(response: Response, form_data: OAuth2PasswordRequestForm = Depends(),
                           db: Session = Depends(get_db)):
    user = crud.get_user_by_username(db, username=form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Неправильные имя пользователя или пароль")
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request):
    return templates.TemplateResponse("upload.html", get_context(request))


@router.get("/files", response_class=HTMLResponse)
async def list_files(request: Request, current_user: models.User = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    client = get_webdav_client()
    try:
        remote_path = f"/{current_user.username}/"
        client.mkdir(remote_path)
        files = client.list(remote_path)
        files = [f for f in files if not client.is_dir(remote_path + f)]
        file_names = [f.split('/')[-1] for f in files]
        return templates.TemplateResponse("files.html", get_context(request, file_names))
    except Exception as e:
        logger.error(f"Ошибка при получении списка файлов для пользователя {current_user.username}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка при получении списка файлов: {str(e)}")


@router.post("/upload/")
async def upload_file(file: UploadFile = File(...), current_user: models.User = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    client = get_webdav_client()
    try:
        file_contents = await file.read()
        remote_path = f"/{current_user.username}/{file.filename}"
        client.mkdir(f"/{current_user.username}/")
        file_stream = io.BytesIO(file_contents)
        client.upload_to(file_stream, remote_path)
        logger.info(f"Пользователь {current_user.username} загрузил файл {file.filename}")
        return {"filename": file.filename, "path": remote_path,
                "info": f"File '{file.filename}' uploaded successfully."}
    except Exception as e:
        logger.error(f"Ошибка при загрузке файла {file.filename} пользователем {current_user.username}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка при загрузке файла: {str(e)}")


@router.get("/files/{filename}", response_class=FileResponse)
async def get_file(filename: str, current_user: models.User = Depends(get_current_user)):
    return RedirectResponse(url=f"{WEBDAV_OPTIONS['webdav_hostname']}{current_user.username}/{filename}")


@router.delete("/files/{filename}")
async def delete_file(filename: str, current_user: models.User = Depends(get_current_user)):
    client = get_webdav_client()

    try:
        remote_path = f"/{current_user.username}/{filename}"
        if not client.check(remote_path):
            logger.warning(f"Файл {filename} для пользователя {current_user.username} не найден.")
            raise HTTPException(status_code=404, detail="Файл не найден.")
        client.clean(remote_path)
        logger.info(f"Пользователь {current_user.username} удалил файл {filename}")
        return JSONResponse(content={"info": f"Файл '{filename}' успешно удален."})
    except Exception as e:
        logger.error(f"Ошибка при удалении файла {filename} пользователем {current_user.username}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка при удалении файла: {str(e)}")
