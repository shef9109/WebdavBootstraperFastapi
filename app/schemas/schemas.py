from pydantic import BaseModel, EmailStr, ConfigDict
from datetime import datetime

class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)

class UserBase(BaseModel):
    username: str
    email: EmailStr


class UserCreate(UserBase):
    password: str


class UserResponse(BaseSchema):
    id: int

class UserAuth(BaseSchema):
    id: int
    username: str
    passname: str

class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None

class AppPasswords(BaseSchema):
    id: int
    name_password: str
    created_at: datetime

class CreatePass(BaseSchema):
    id: int
    name_password: str
    created_at: datetime
    password: str

class FileInfo(BaseSchema):
    creationdate: str
    getlastmodified: str
    displayname: str
    getetag: str
    getcontentlength: int | None
    getcontenttype: str | None
    resourcetype: str | None

    ishidden: int | None
    isreadonly: int | None
    isroot: int | None
    iscollection: int | None

    getcontentlanguage: str | None = None