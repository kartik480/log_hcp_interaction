from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.db import SessionLocal
from app.models import (
    Interaction,
    InteractionAttendee,
    InteractionMaterial,
    InteractionRevision,
    InteractionSample,
)
from app.schemas.interaction import InteractionDraft, MaterialRef, SampleRef


def _to_draft(row: Interaction) -> InteractionDraft:
    return InteractionDraft(
        hcp_id=row.hcp_external_id,
        hcp_name=row.hcp_name,
        interaction_type=row.interaction_type,  # type: ignore[arg-type]
        occurred_at=row.occurred_at,
        attendees=[a.attendee_name for a in row.attendees],
        topics_discussed=row.topics_discussed or "",
        materials=[
            MaterialRef(catalog_id=m.catalog_id, name=m.name, quantity=m.quantity) for m in row.materials
        ],
        samples=[SampleRef(sku=s.sku, name=s.name, quantity=s.quantity) for s in row.samples],
        sentiment=row.sentiment,  # type: ignore[arg-type]
        outcomes=row.outcomes or "",
        follow_up_actions=row.follow_up_actions or "",
        ai_suggested_follow_ups=row.ai_suggested_follow_ups or [],
        summary=row.summary,
    )


def create_interaction(rep_id: str, draft: InteractionDraft, chat_transcript: list[dict]) -> dict:
    with SessionLocal() as db:
        interaction = Interaction(
            public_id=f"int-{uuid.uuid4().hex[:10]}",
            rep_id=rep_id,
            hcp_external_id=draft.hcp_id,
            hcp_name=draft.hcp_name,
            interaction_type=draft.interaction_type,
            occurred_at=draft.occurred_at,
            sentiment=draft.sentiment,
            summary=draft.summary,
            topics_discussed=draft.topics_discussed,
            outcomes=draft.outcomes,
            follow_up_actions=draft.follow_up_actions,
            ai_suggested_follow_ups=draft.ai_suggested_follow_ups,
            chat_transcript=chat_transcript,
            status="logged",
        )
        db.add(interaction)
        db.flush()

        for attendee in draft.attendees:
            db.add(InteractionAttendee(interaction_id=interaction.id, attendee_name=attendee))
        for material in draft.materials:
            db.add(
                InteractionMaterial(
                    interaction_id=interaction.id,
                    catalog_id=material.catalog_id,
                    name=material.name,
                    quantity=material.quantity,
                )
            )
        for sample in draft.samples:
            db.add(
                InteractionSample(
                    interaction_id=interaction.id,
                    sku=sample.sku,
                    name=sample.name,
                    quantity=sample.quantity,
                )
            )

        db.commit()
        db.refresh(interaction)
        created = interaction.created_at.isoformat() if interaction.created_at else ""
        return {"interaction_id": interaction.public_id, "created_at": created}


def get_interaction_by_public_id(public_id: str, db: Session | None = None) -> Interaction | None:
    owns_session = db is None
    if owns_session:
        db = SessionLocal()
    try:
        stmt = (
            select(Interaction)
            .where(Interaction.public_id == public_id)
            .options(
                selectinload(Interaction.attendees),
                selectinload(Interaction.materials),
                selectinload(Interaction.samples),
                selectinload(Interaction.revisions),
            )
        )
        return db.execute(stmt).scalar_one_or_none()
    finally:
        if owns_session:
            db.close()


def get_interaction_draft(public_id: str) -> InteractionDraft | None:
    row = get_interaction_by_public_id(public_id)
    if not row:
        return None
    return _to_draft(row)


def update_interaction(
    public_id: str,
    draft: InteractionDraft,
    reason: str,
    patch: dict,
    changed_by: str = "system",
) -> dict:
    with SessionLocal() as db:
        row = get_interaction_by_public_id(public_id, db=db)
        if not row:
            raise KeyError(public_id)

        row.hcp_external_id = draft.hcp_id
        row.hcp_name = draft.hcp_name
        row.interaction_type = draft.interaction_type
        row.occurred_at = draft.occurred_at
        row.sentiment = draft.sentiment
        row.summary = draft.summary
        row.topics_discussed = draft.topics_discussed
        row.outcomes = draft.outcomes
        row.follow_up_actions = draft.follow_up_actions
        row.ai_suggested_follow_ups = draft.ai_suggested_follow_ups

        row.attendees = [InteractionAttendee(attendee_name=a) for a in draft.attendees]
        row.materials = [
            InteractionMaterial(catalog_id=m.catalog_id, name=m.name, quantity=m.quantity) for m in draft.materials
        ]
        row.samples = [InteractionSample(sku=s.sku, name=s.name, quantity=s.quantity) for s in draft.samples]

        current_revision = db.execute(
            select(func.coalesce(func.max(InteractionRevision.revision_no), 0)).where(
                InteractionRevision.interaction_id == row.id
            )
        ).scalar_one()
        next_revision = int(current_revision) + 1
        db.add(
            InteractionRevision(
                interaction_id=row.id,
                revision_no=next_revision,
                changed_by=changed_by,
                change_reason=reason,
                diff_json=patch,
            )
        )
        db.commit()
        db.refresh(row)
        return {
            "interaction_id": row.public_id,
            "revision": next_revision,
            "draft": _to_draft(row).model_dump(mode="json"),
        }
