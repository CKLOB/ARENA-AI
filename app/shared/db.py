from functools import lru_cache
import os
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


DEFAULT_DATABASE_URL = "postgresql+psycopg://mlflow:mlflow@localhost:5432/arena_ai"


class Base(DeclarativeBase):
    pass


def get_database_url() -> str:
    return os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)


@lru_cache
def get_engine():
    return create_engine(get_database_url(), pool_pre_ping=True)


@lru_cache
def get_session_local():
    return sessionmaker(autocommit=False, autoflush=False, bind=get_engine())


def get_db() -> Generator[Session, None, None]:
    db = get_session_local()()
    try:
        yield db
    finally:
        db.close()
