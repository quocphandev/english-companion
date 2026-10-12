"""add conversation settings

Revision ID: 7060bde73b46
Revises: 2ee8aebf5926
Create Date: 2026-10-12 10:00:44.579183

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7060bde73b46"
down_revision: str | Sequence[str] | None = "2ee8aebf5926"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Store level and correction_mode on each conversation."""
    op.add_column(
        "conversations",
        sa.Column("level", sa.String(length=2), server_default="A2", nullable=False),
    )
    op.add_column(
        "conversations",
        sa.Column(
            "correction_mode",
            sa.String(length=20),
            server_default="learning",
            nullable=False,
        ),
    )
    # Autogenerate does not detect new CHECK constraints: added by hand.
    op.create_check_constraint(
        op.f("ck_conversations_level"),
        "conversations",
        "level IN ('A1', 'A2', 'B1', 'B2')",
    )
    op.create_check_constraint(
        op.f("ck_conversations_correction_mode"),
        "conversations",
        "correction_mode IN ('learning', 'conversation')",
    )
    # Existing conversations keep the settings they were using (stored on the profile).
    op.execute(
        """
        UPDATE conversations AS c
        SET level = p.level, correction_mode = p.correction_mode
        FROM profiles AS p
        WHERE c.profile_id = p.id
        """
    )


def downgrade() -> None:
    """Remove the per-conversation settings (the profile keeps its own)."""
    op.drop_constraint(
        op.f("ck_conversations_correction_mode"), "conversations", type_="check"
    )
    op.drop_constraint(op.f("ck_conversations_level"), "conversations", type_="check")
    op.drop_column("conversations", "correction_mode")
    op.drop_column("conversations", "level")
