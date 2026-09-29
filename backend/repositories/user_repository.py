from __future__ import annotations

import json
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.agent_run import AgentRun, ToolCall
from backend.models.conversation import Conversation, Message, SavedItem
from backend.models.user import User, UserPreference


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_or_create_user(self, user_id: uuid.UUID) -> User:
        user = self.db.get(User, user_id)
        if user is None:
            user = User(id=user_id)
            self.db.add(user)
            self.db.flush()
        return user

    def get_preferences(self, user_id: uuid.UUID) -> UserPreference | None:
        stmt = select(UserPreference).where(UserPreference.user_id == user_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def upsert_preferences(self, user_id: uuid.UUID, **fields) -> UserPreference:
        pref = self.get_preferences(user_id)
        if pref is None:
            pref = UserPreference(user_id=user_id)
            self.db.add(pref)
        for key, value in fields.items():
            if value is not None:
                setattr(pref, key, value)
        self.db.flush()
        return pref


class ConversationRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_or_create(self, conversation_id: uuid.UUID | None, user_id: uuid.UUID) -> Conversation:
        if conversation_id is not None:
            convo = self.db.get(Conversation, conversation_id)
            if convo is not None:
                return convo
        convo = Conversation(id=conversation_id or uuid.uuid4(), user_id=user_id)
        self.db.add(convo)
        self.db.flush()
        return convo

    def add_message(
        self,
        conversation_id: uuid.UUID,
        role: str,
        content: str,
        shown_item_ids: list[uuid.UUID] | None = None,
    ) -> Message:
        msg = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            shown_item_ids=json.dumps([str(i) for i in shown_item_ids]) if shown_item_ids else None,
        )
        self.db.add(msg)
        self.db.flush()
        return msg

    def recent_history(self, conversation_id: uuid.UUID, limit: int = 10) -> list[Message]:
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        return list(reversed(self.db.execute(stmt).scalars().all()))

    def last_shown_item_ids(self, conversation_id: uuid.UUID) -> list[uuid.UUID]:
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id, Message.shown_item_ids.is_not(None))
            .order_by(Message.created_at.desc())
            .limit(1)
        )
        msg = self.db.execute(stmt).scalars().first()
        if msg is None or not msg.shown_item_ids:
            return []
        return [uuid.UUID(i) for i in json.loads(msg.shown_item_ids)]


class SavedItemRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, user_id: uuid.UUID, menu_item_id: uuid.UUID) -> SavedItem:
        existing = self.db.execute(
            select(SavedItem).where(
                SavedItem.user_id == user_id, SavedItem.menu_item_id == menu_item_id
            )
        ).scalar_one_or_none()
        if existing:
            return existing
        saved = SavedItem(user_id=user_id, menu_item_id=menu_item_id)
        self.db.add(saved)
        self.db.flush()
        return saved

    def remove(self, saved_item_id: uuid.UUID) -> bool:
        saved = self.db.get(SavedItem, saved_item_id)
        if saved is None:
            return False
        self.db.delete(saved)
        return True

    def list_for_user(self, user_id: uuid.UUID) -> list[SavedItem]:
        stmt = select(SavedItem).where(SavedItem.user_id == user_id)
        return list(self.db.execute(stmt).scalars().all())


class AgentRunRepository:
    """Persists the audit trail required by the observability spec: every
    agent run and every tool call it made, with latencies and outcomes."""

    def __init__(self, db: Session):
        self.db = db

    def start_run(self, conversation_id: uuid.UUID, request_id: str, user_message: str) -> AgentRun:
        run = AgentRun(
            conversation_id=conversation_id,
            request_id=request_id,
            user_message=user_message,
            status="running",
        )
        self.db.add(run)
        self.db.flush()
        return run

    def finish_run(
        self,
        run: AgentRun,
        *,
        status: str,
        detected_intent: str | None = None,
        extracted_constraints: dict | None = None,
        total_latency_ms: float | None = None,
        llm_latency_ms: float | None = None,
        token_usage: dict | None = None,
        error_message: str | None = None,
    ) -> AgentRun:
        run.status = status
        run.detected_intent = detected_intent
        if extracted_constraints is not None:
            run.extracted_constraints_json = json.dumps(extracted_constraints, default=str)
        run.total_latency_ms = total_latency_ms
        run.llm_latency_ms = llm_latency_ms
        if token_usage is not None:
            run.llm_token_usage_json = json.dumps(token_usage)
        run.error_message = error_message
        self.db.flush()
        return run

    def get_last_search_constraints(self, conversation_id: uuid.UUID) -> dict | None:
        """Used for short-term-memory refinement: 'make it spicy' / 'which
        one is lighter' should inherit the constraints of the most recent
        search_food turn in this conversation, not start from scratch."""
        stmt = (
            select(AgentRun)
            .where(
                AgentRun.conversation_id == conversation_id,
                AgentRun.detected_intent == "search_food",
                AgentRun.status == "completed",
            )
            .order_by(AgentRun.created_at.desc())
            .limit(1)
        )
        run = self.db.execute(stmt).scalars().first()
        if run is None or not run.extracted_constraints_json:
            return None
        return json.loads(run.extracted_constraints_json)

    def record_tool_call(
        self,
        run_id: uuid.UUID,
        *,
        tool_name: str,
        arguments: dict,
        result_summary: dict | None,
        status: str,
        latency_ms: float | None,
        error_message: str | None = None,
    ) -> ToolCall:
        call = ToolCall(
            agent_run_id=run_id,
            tool_name=tool_name,
            arguments_json=json.dumps(arguments, default=str),
            result_summary_json=json.dumps(result_summary, default=str) if result_summary else None,
            status=status,
            latency_ms=latency_ms,
            error_message=error_message,
        )
        self.db.add(call)
        self.db.flush()
        return call
