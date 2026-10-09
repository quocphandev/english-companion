from datetime import timedelta

from sqlalchemy.orm import Session

from app.models import Conversation, Message, Profile


def test_create_conversation_with_message(db_session: Session) -> None:
    profile = Profile()
    conversation = Conversation(profile=profile, topic="coffee shop")
    message = Message(
        conversation=conversation,
        role="user",
        original_text="Yesterday I go to work.",
        request_id="req-001",
    )
    db_session.add(message)
    db_session.commit()
    # Drop cached objects so the asserts below read what the database stored.
    db_session.expire_all()

    saved = db_session.get(Conversation, conversation.id)

    assert saved is not None
    assert saved.status == "active"
    assert saved.profile.level == "A2"
    assert saved.created_at.utcoffset() == timedelta(0)
    assert [m.id for m in saved.messages] == [message.id]
    saved_message = saved.messages[0]
    assert saved_message.original_text == "Yesterday I go to work."
    assert saved_message.input_mode == "text"
    assert saved_message.status == "pending"
    assert saved_message.request_id == "req-001"
