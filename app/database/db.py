from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DATABASE_URL = "sqlite:///./app.db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    __table_args__ = {'extend_existing': True}
    __abstract__ = True

    def __repr__(self):
        return "<{name} ({fields})>".format(name=self.__class__.__name__,
                                            fields=self.__dict__)

