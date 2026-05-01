from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Interaction(Base):
    __tablename__ = "interaction"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    rep_id: Mapped[str] = mapped_column(String(100), index=True)
    hcp_external_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    hcp_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    interaction_type: Mapped[str] = mapped_column(String(32), default="meeting")
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sentiment: Mapped[str] = mapped_column(String(20), default="neutral")
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    topics_discussed: Mapped[str] = mapped_column(Text, default="")
    outcomes: Mapped[str] = mapped_column(Text, default="")
    follow_up_actions: Mapped[str] = mapped_column(Text, default="")
    ai_suggested_follow_ups: Mapped[list[str]] = mapped_column(JSON, default=list)
    chat_transcript: Mapped[list[dict]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(20), default="logged")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    attendees: Mapped[list["InteractionAttendee"]] = relationship(
        cascade="all, delete-orphan", back_populates="interaction"
    )
    materials: Mapped[list["InteractionMaterial"]] = relationship(
        cascade="all, delete-orphan", back_populates="interaction"
    )
    samples: Mapped[list["InteractionSample"]] = relationship(
        cascade="all, delete-orphan", back_populates="interaction"
    )
    revisions: Mapped[list["InteractionRevision"]] = relationship(
        cascade="all, delete-orphan", back_populates="interaction"
    )


class InteractionAttendee(Base):
    __tablename__ = "interaction_attendee"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    interaction_id: Mapped[int] = mapped_column(ForeignKey("interaction.id", ondelete="CASCADE"), index=True)
    attendee_name: Mapped[str] = mapped_column(String(255))

    interaction: Mapped[Interaction] = relationship(back_populates="attendees")


class InteractionMaterial(Base):
    __tablename__ = "interaction_material"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    interaction_id: Mapped[int] = mapped_column(ForeignKey("interaction.id", ondelete="CASCADE"), index=True)
    catalog_id: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(255))
    quantity: Mapped[int] = mapped_column(Integer, default=1)

    interaction: Mapped[Interaction] = relationship(back_populates="materials")


class InteractionSample(Base):
    __tablename__ = "interaction_sample"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    interaction_id: Mapped[int] = mapped_column(ForeignKey("interaction.id", ondelete="CASCADE"), index=True)
    sku: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(255))
    quantity: Mapped[int] = mapped_column(Integer, default=1)

    interaction: Mapped[Interaction] = relationship(back_populates="samples")


class InteractionRevision(Base):
    __tablename__ = "interaction_revision"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    interaction_id: Mapped[int] = mapped_column(ForeignKey("interaction.id", ondelete="CASCADE"), index=True)
    revision_no: Mapped[int] = mapped_column(Integer)
    changed_by: Mapped[str] = mapped_column(String(100), default="system")
    change_reason: Mapped[str] = mapped_column(Text, default="")
    diff_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    interaction: Mapped[Interaction] = relationship(back_populates="revisions")
