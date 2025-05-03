from sqlalchemy.orm import Session
from sqlalchemy import delete
from passlib.context import CryptContext
import secrets
import string

from app.schemas import schemas
from app.models.models import AppPasswords

alphabet = string.ascii_letters + string.digits

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_passwords_of_user(db: Session, user_id: int):
    passwords = db.query(AppPasswords).filter(AppPasswords.user_id == user_id).all()
    passwords = [schemas.AppPasswords.model_validate(row) for row in passwords]
    return passwords 


def create_password(db: Session, user_id: int, passname: str):
    password = ''.join(secrets.choice(alphabet) for i in range(12))
    hashed_password = pwd_context.hash(password)
    db_pass = AppPasswords(
        user_id=user_id,
        name_password=passname,
        hashed_password=hashed_password
    )
    db.add(db_pass)
    db.commit()
    db.refresh(db_pass)
    return schemas.CreatePass(id=db_pass.id, name_password=db_pass.name_password, created_at=db_pass.created_at, password=password)

def delete_password(db: Session, user_id: int, row_id: int) -> bool:
    res = db.execute(delete(AppPasswords).where(AppPasswords.user_id==user_id).where(AppPasswords.id == row_id)).rowcount
    db.commit()
    return res == 1
