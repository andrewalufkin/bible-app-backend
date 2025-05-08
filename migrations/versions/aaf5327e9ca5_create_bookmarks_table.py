"""create_bookmarks_table

Revision ID: aaf5327e9ca5
Revises: 692b8c7c02f2
Create Date: 2025-05-08 00:02:45.429663

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql # Import postgresql for UUID type


# revision identifiers, used by Alembic.
revision: str = 'aaf5327e9ca5'
down_revision: Union[str, None] = '692b8c7c02f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('bookmarks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('book', sa.String(length=100), nullable=False),
        sa.Column('chapter', sa.Integer(), nullable=False),
        sa.Column('verse', sa.Integer(), nullable=False),
        sa.Column('text_preview', sa.String(length=255), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_bookmarks_id'), 'bookmarks', ['id'], unique=False)
    op.create_index(op.f('ix_bookmarks_user_id'), 'bookmarks', ['user_id'], unique=False)
    op.create_index(op.f('ix_bookmarks_book'), 'bookmarks', ['book'], unique=False)
    op.create_index(op.f('ix_bookmarks_chapter'), 'bookmarks', ['chapter'], unique=False)
    op.create_index(op.f('ix_bookmarks_verse'), 'bookmarks', ['verse'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_bookmarks_verse'), table_name='bookmarks')
    op.drop_index(op.f('ix_bookmarks_chapter'), table_name='bookmarks')
    op.drop_index(op.f('ix_bookmarks_book'), table_name='bookmarks')
    op.drop_index(op.f('ix_bookmarks_user_id'), table_name='bookmarks')
    op.drop_index(op.f('ix_bookmarks_id'), table_name='bookmarks')
    op.drop_table('bookmarks')
