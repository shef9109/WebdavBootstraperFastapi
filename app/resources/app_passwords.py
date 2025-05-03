from sqlalchemy.orm import Session
from app.schemas import schemas

from app.models.models import AppPasswords

def get_passwords_of_user(db: Session, user_id: int):
    passwords = db.query(AppPasswords).filter(AppPasswords.user_id == user_id).all()
    passwords = [schemas.AppPasswords.model_validate(row) for row in passwords]
    return passwords 