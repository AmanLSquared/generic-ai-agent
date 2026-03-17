import uuid
from datetime import datetime
from sqlalchemy import Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from database import Base


class Dashboard(Base):
    __tablename__ = "dashboards"

    id: Mapped[str] = mapped_column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(Text, nullable=False)
    html: Mapped[str] = mapped_column(Text, nullable=False)
    json_schema: Mapped[str] = mapped_column(Text, nullable=False)
    embed_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    asana_workspace_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(Text, primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
