import itertools
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.schemas.interaction import InteractionDraft


@dataclass
class StoredInteraction:
    id: str
    rep_id: str
    draft: InteractionDraft
    chat_transcript: list[dict]
    created_at: str
    revisions: list[dict] = field(default_factory=list)


class InteractionStore:
    """In-memory persistence for local development. Swap for SQLAlchemy + Postgres."""

    def __init__(self) -> None:
        self._items: dict[str, StoredInteraction] = {}
        self._id_seq = itertools.count(1)

    def create(self, rep_id: str, draft: InteractionDraft, chat_transcript: list[dict]) -> StoredInteraction:
        iid = f"int-{next(self._id_seq)}"
        now = datetime.now(timezone.utc).isoformat()
        row = StoredInteraction(
            id=iid,
            rep_id=rep_id,
            draft=draft,
            chat_transcript=list(chat_transcript),
            created_at=now,
            revisions=[],
        )
        self._items[iid] = row
        return row

    def get(self, interaction_id: str) -> StoredInteraction | None:
        return self._items.get(interaction_id)

    def update(
        self,
        interaction_id: str,
        draft: InteractionDraft,
        reason: str,
        patch: dict,
    ) -> StoredInteraction:
        row = self._items[interaction_id]
        rev = len(row.revisions) + 1
        row.revisions.append(
            {
                "revision": rev,
                "at": datetime.now(timezone.utc).isoformat(),
                "reason": reason,
                "patch": patch,
            }
        )
        row.draft = draft
        self._items[interaction_id] = row
        return row


store = InteractionStore()


def draft_to_dict(d: InteractionDraft) -> dict:
    return json.loads(d.model_dump_json())
