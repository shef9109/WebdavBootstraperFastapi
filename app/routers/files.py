import os
from pathlib import Path

import aiofiles
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse

from app.models import models
from app.resources.auth import get_current_user
from app.utils import templates, get_context

router = APIRouter(
    tags=["files"]
)

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request):
    return templates.TemplateResponse("upload.html", get_context(request))


@router.get("/files", response_class=HTMLResponse)
async def list_files(request: Request, current_user: models.User = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    upload_dir = Path("uploads")
    if not upload_dir.exists():
        files = []
    else:
        files = [f.name for f in upload_dir.iterdir() if f.is_file()]

    return templates.TemplateResponse("files.html", get_context(request, files))


@router.post("/upload/")
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


@router.get("/files/{filename}", response_class=FileResponse)
async def get_file(filename: str, current_user: models.User = Depends(get_current_user)):
    file_location = UPLOAD_DIR / filename
    if file_location.exists() and file_location.is_file():
        return FileResponse(path=file_location, filename=filename)
    raise HTTPException(status_code=404, detail="Файл не найден.")


@router.delete("/files/{filename}")
async def delete_file(filename: str, current_user: models.User = Depends(get_current_user)):
    file_location = UPLOAD_DIR / filename
    if file_location.exists() and file_location.is_file():
        os.remove(file_location)
        return JSONResponse(content={"info": f"Файл '{filename}' успешно удален."})
    raise HTTPException(status_code=404, detail="Файл не найден.")
