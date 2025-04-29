from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Response, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic_xml import BaseXmlModel

from app.resources import crud
from app.resources.auth import (
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    get_db,
    generate_otp_secret,
    get_totp_uri,
    verify_otp_code,
    basic_auth,
)
from app.resources.crud import verify_password
from app.utils import templates, get_context
from app.utilis.response import XMLResponse

router = APIRouter(
    tags=["auth"],
)

class IndexController:

    response_model = HTMLResponse

    @staticmethod
    def TokenAction(response: Response, form_data: OAuth2PasswordRequestForm = Depends(),
                    db: Session = Depends(get_db)):
        """Method for handling login
        
        @response_model dict
        @method post
        """
        user = crud.get_user_by_username(db, username=form_data.username)
        if not user or not verify_password(form_data.password, user.hashed_password):
            return "Неправильные имя пользователя или пароль"
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
    
    @staticmethod
    def indexAction(request: Request):
        return templates.TemplateResponse("index.html", get_context(request))
    
    @staticmethod
    def registerAction(request: Request):
        return templates.TemplateResponse("register.html", get_context(request))

    @staticmethod
    def loginAction(request: Request):
        return templates.TemplateResponse("login.html", get_context(request))


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


@router.post("/otp/setup")
def otp_setup(user: Session = Depends(basic_auth), db: Session = Depends(get_db)):
    """Generate OTP secret and provisioning URI for user"""
    if user.otp_secret is None:
        secret = generate_otp_secret()
        user.otp_secret = secret
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        secret = user.otp_secret
    uri = get_totp_uri(secret, user.username)
    return {"otp_secret": secret, "otp_uri": uri}


@router.post("/otp/verify")
def otp_verify(code: str, user: Session = Depends(basic_auth)):
    """Verify OTP code"""
    if user.otp_secret is None:
        raise HTTPException(status_code=400, detail="OTP not setup for user")
    if verify_otp_code(user.otp_secret, code):
        return {"verified": True}
    else:
        raise HTTPException(status_code=400, detail="Invalid OTP code")
