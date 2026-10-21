from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Index, func
from sqlalchemy.orm import Mapped, mapped_column

from .. import Base


class User(Base):
    __tablename__ = "users"
    uuid: Mapped[UUID] = mapped_column(
        primary_key=True, default=uuid4
    )  # TODO: заменить на uuid7
    email: Mapped[str] = mapped_column(unique=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    __table_args__ = (Index("idx_uuid", "uuid", postgresql_using="hash"),)
