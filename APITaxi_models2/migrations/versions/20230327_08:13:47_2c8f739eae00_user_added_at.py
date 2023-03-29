"""user added_at

Revision ID: 2c8f739eae00
Revises: 4536e29df0d4
Create Date: 2023-03-27 08:13:47.741895

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import func
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '2c8f739eae00'
down_revision = '4536e29df0d4'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('user', sa.Column('added_at', sa.DateTime(), nullable=True))
    op.add_column('user', sa.Column('added_via', sa.Enum('form', 'api', name='sources'), nullable=True))
    op.add_column('user', sa.Column('source', sa.String(length=255), nullable=True))
    op.add_column('user', sa.Column('last_update_at', sa.DateTime(), nullable=True))

    op.execute("""update "user" set added_at=now(), added_via='api', source='create_user'""")

    op.alter_column('user', 'added_at', existing_type=postgresql.TIMESTAMP(), nullable=False)
    op.alter_column('user', 'added_via', existing_type=postgresql.ENUM('form', 'api', name='sources'), nullable=False) 
    op.alter_column('user', 'source', existing_type=sa.VARCHAR(length=255), nullable=False)


def downgrade():
    op.drop_column('user', 'last_update_at')
    op.drop_column('user', 'source')
    op.drop_column('user', 'added_via')
    op.drop_column('user', 'added_at')
