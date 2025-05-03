from http import HTTPStatus

from fastapi import Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime

from app.repositories import crud
from app.repositories.app_passwords import get_passwords_of_user, create_password, delete_password
from app.repositories.auth import get_current_user, get_db, basic_auth
from app.schemas import schemas
from app.utils import templates, get_context


class UsersController:
    @staticmethod
    def PostRegisterAction(user: schemas.UserCreate, db: Session = Depends(get_db)):
        """
        @method post
        @response_model User
        """
        db_user = crud.get_user_by_username(db, username=user.username)
        if db_user:
            raise HTTPException(status_code=400, detail="Имя пользователя уже используется")
        db_user = crud.get_user_by_email(db, email=str(user.email))
        if db_user:
            raise HTTPException(status_code=400, detail="Email уже зарегистрирован")
        return crud.create_user(db=db, user=user)

    @staticmethod
    def GetUsersMeAction(current_user: schemas.UserResponse = Depends(get_current_user)):
        """
        @method get
        @response_model UserResponse
        """
        return current_user

    @staticmethod
    def GetRegisterPageAction(request: Request):
        """
        @method get
        @response_model HTMLResponse
        """
        return templates.TemplateResponse("register.html", get_context(request))

    @staticmethod
    def GetUploadPageAction(request: Request):
        """
        @method get
        @response_model HTMLResponse
        """
        return templates.TemplateResponse("upload.html", get_context(request))

    @staticmethod
    def GetLoginPageAction(request: Request):
        """
        @method get
        @response_model HTMLResponse
        """
        return templates.TemplateResponse("login.html", get_context(request))

    @staticmethod
    def GetLogoutPageAction():
        """
        @method get
        @response_model RedirectResponse
        """
        response = RedirectResponse(url="/", status_code=303)
        response.delete_cookie(key="access_token")
        return response

    @staticmethod
    def GetIndexPageAction(request: Request):
        """
        @method get
        @response_model HTMLResponse
        """
        return templates.TemplateResponse("index.html", get_context(request))
    
    @staticmethod
    def GetPanelPasswordAction(request: Request, current_user: schemas.UserResponse = Depends(get_current_user), db: Session = Depends(get_db)):
        """
        @method get
        @response_model HTMLResponse
        """

        data = get_passwords_of_user(db, current_user.id)
        print(data)
        return templates.TemplateResponse(request=request, name="panelpass.html", context={"passwords": data} | get_context(request))

    @staticmethod
    def GetCreatePasswordAction(request: Request, passname: str, current_user: schemas.UserResponse = Depends(get_current_user), db: Session = Depends(get_db)):
        """
        @method get
        @response_model HTMLResponse
        """
        data = create_password(db, current_user.id, passname)
        return templates.TemplateResponse(request=request, name="createpassword.html", context=get_context(request) | {"data": data})

    @staticmethod
    def DeletePasswordAction(request: Request, id: int,
                                current_user: schemas.UserResponse = Depends(get_current_user),
                                db: Session = Depends(get_db)):
        """
        @method get
        @response_model HTMLResponse
        """
        data = delete_password(db, current_user.id, id)
        if not data:
            raise HTTPException(status_code=HTTPStatus.FORBIDDEN, detail="Access Denied")
        return HTMLResponse(status_code=HTTPStatus.NO_CONTENT)

    @staticmethod
    def GetTestPassAuthAction(request: Request, auth: str = Depends(basic_auth)):
        """
        @method get
        @response_model JSONResponse
        """
        return {"name_password": auth}

    def __str__(self):
        return f"{self.__class__.__name__} работает для вас <3"