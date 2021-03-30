"""Make zupc_id unique

Revision ID: 4f97b4438c18
Revises: 5d28367f8ffe
Create Date: 2021-03-30 08:10:05.183104

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4f97b4438c18'
down_revision = '5d28367f8ffe'
branch_labels = None
depends_on = None


def upgrade():
    op.create_unique_constraint(None, 'ZUPC', ['zupc_id'])


def downgrade():
    op.drop_constraint(None, 'ZUPC', type_='unique')
