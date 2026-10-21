from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from auth_service.config import settings


class Base(DeclarativeBase):
    pass


url_db = settings.db.asyncurl
engine = create_async_engine(url_db, echo=False)

SessionMaker = async_sessionmaker(engine)
