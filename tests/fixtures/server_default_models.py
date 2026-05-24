import datetime
import uuid

from sqlalchemy import ARRAY, Boolean, DateTime, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class AiPersonality(Base):
    __tablename__ = "ai_personality"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID, primary_key=True)

    # NOT NULL + scalar server_default -> materialized literal, type kept narrow
    autopilot_pause_minutes: Mapped[int] = mapped_column(
        Integer, server_default=text("10")
    )
    # NOT NULL + function server_default -> optional
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=text("now()")
    )
    # NOT NULL + scalar bool server_default
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    # NOT NULL + scalar string server_default (with a trailing Postgres cast)
    tone: Mapped[str] = mapped_column(String, server_default=text("'concise'::text"))
    # NOT NULL + ORM-side scalar default
    retry_count: Mapped[int] = mapped_column(Integer, default=3)
    # plain NOT NULL, no default -> stays required
    display_name: Mapped[str] = mapped_column(String)
    # nullable -> unchanged
    notes: Mapped[str | None] = mapped_column(String, nullable=True)
    # NOT NULL JSONB with '{}'::jsonb default: parsed literal is the str "{}",
    # but the field's Python type is dict-shaped. Must NOT materialize as a
    # str default; falls back to optional/None.
    data: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    # NOT NULL ARRAY with '{}'::text[] default: same shape mismatch.
    tags: Mapped[list] = mapped_column(
        ARRAY(Text), server_default=text("'{}'::text[]")
    )
