from sqlalchemy import Column, Integer, String, ForeignKey, TIMESTAMP, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from typing import List, Optional

from app.database.db import Base
from app.utilis.filesystem import FileSystem


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    #otp_secret = Column(String, nullable=True)
    passwords: Mapped[Optional[List["AppPasswords"]]] = relationship()

class AppPasswords(Base):
    __tablename__ = "app_passwords"
    
    id:Mapped[int] = mapped_column(primary_key=True)
    user_id:Mapped[int] = mapped_column(ForeignKey('users.id'))
    hashed_password:Mapped[str]
    name_password:Mapped[str]
    created_at:Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())

class FileSystem(Base):
    __tablename__ = "files"

    fname:Mapped[str] = mapped_column(primary_key=True)
    vpath:Mapped[str]
    member_type: Mapped[int]
    parent: Mapped[Optional[str]] = mapped_column(ForeignKey('files.fname', ondelete='CASCADE'))
    owner_id:Mapped[int] = mapped_column(ForeignKey('users.id'))
    created_at:Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    updated_at:Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())

    children: Mapped[Optional[List["FileSystem"]]] = relationship("FileSystem", cascade="all, delete", lazy="noload", passive_deletes=True, uselist=True)
