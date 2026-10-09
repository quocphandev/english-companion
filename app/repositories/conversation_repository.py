"""Database queries for profiles, conversations, messages and corrections.

Methods only add/flush; committing (ending the transaction) is the service's job.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Conversation, Correction, Message, Profile
from app.schemas.ai import TurnReply


class ConversationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_or_create_default_profile(self) -> Profile:
        """Single-user app: use the first profile, creating it if missing."""
        profile = self._session.scalar(select(Profile).order_by(Profile.id).limit(1))
        if profile is None:
            profile = Profile()
            self._session.add(profile)
            self._session.flush()
        return profile

    def create_conversation(self, profile_id: int, topic: str) -> Conversation:
        conversation = Conversation(profile_id=profile_id, topic=topic)
        self._session.add(conversation)
        self._session.flush()
        return conversation

    def get_conversation(self, conversation_id: int) -> Conversation | None:
        return self._session.get(Conversation, conversation_id)

    def list_conversations(self) -> list[Conversation]:
        """All conversations, newest first."""
        return list(
            self._session.scalars(
                select(Conversation).order_by(
                    Conversation.created_at.desc(), Conversation.id.desc()
                )
            )
        )

    def list_messages(self, conversation_id: int) -> list[Message]:
        """All messages of a conversation, oldest first, with corrections loaded."""
        return list(
            self._session.scalars(
                select(Message)
                .where(Message.conversation_id == conversation_id)
                # Load all corrections in one extra query instead of one per message.
                .options(selectinload(Message.corrections))
                .order_by(Message.created_at, Message.id)
            )
        )

    def find_message_by_request_id(self, request_id: str) -> Message | None:
        return self._session.scalar(
            select(Message).where(Message.request_id == request_id)
        )

    def add_user_message(
        self, conversation_id: int, request_id: str, text: str, input_mode: str
    ) -> Message:
        """Insert a pending user turn. Raises IntegrityError if request_id exists."""
        message = Message(
            conversation_id=conversation_id,
            role="user",
            original_text=text,
            input_mode=input_mode,
            status="pending",
            request_id=request_id,
        )
        self._session.add(message)
        self._session.flush()
        return message

    def list_recent_turns(self, conversation_id: int, limit: int) -> list[Message]:
        """Latest succeeded messages of one conversation, oldest first."""
        newest_first = self._session.scalars(
            select(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.status == "succeeded",
            )
            .order_by(Message.created_at.desc(), Message.id.desc())
            .limit(limit)
        ).all()
        return list(reversed(newest_first))

    def get_reply(self, user_message_id: int) -> Message | None:
        return self._session.scalar(
            select(Message).where(Message.reply_to_message_id == user_message_id)
        )

    def add_reply(
        self, user_message: Message, reply: TurnReply, prompt_version: str
    ) -> Message:
        """Store the assistant reply and its corrections; mark the user turn done."""
        assistant_message = Message(
            conversation_id=user_message.conversation_id,
            role="assistant",
            original_text=reply.reply_en,
            status="succeeded",
            reply_to_message_id=user_message.id,
        )
        self._session.add(assistant_message)
        user_message.corrections.extend(
            Correction(
                category=item.category,
                original_span=item.original_span,
                corrected_text=item.corrected_text,
                explanation_vi=item.explanation_vi,
                prompt_version=prompt_version,
            )
            for item in reply.corrections
        )
        user_message.status = "succeeded"
        self._session.flush()
        return assistant_message
