"""Add description on operateur

Revision ID: 3bcda5bdca8c
Revises: 3ce723f8065a
Create Date: 2015-06-04 14:39:04.182338

"""

# revision identifiers, used by Alembic.
revision = '3bcda5bdca8c'
down_revision = '3ce723f8065a'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.create_table('logo',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('size', sa.String(), nullable=True),
        sa.Column('format_', sa.String(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.add_column('user', sa.Column('commercial_name', sa.String(), nullable=True))
    op.add_column('user', sa.Column('phone_number', sa.String(), nullable=True))


def downgrade():
    op.drop_column('user', 'phone_number')
    op.drop_column('user', 'commercial_name')
    op.drop_table('logo')
