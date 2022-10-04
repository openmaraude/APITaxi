"""unique roles

Revision ID: b7987048ab8e
Revises: 5001a09d73d3
Create Date: 2022-10-04 09:06:10.362089

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'b7987048ab8e'
down_revision = '5001a09d73d3'
branch_labels = None
depends_on = None


def upgrade():
    op.create_unique_constraint('unique_roles', 'roles_users', ['user_id', 'role_id'])


def downgrade():
    op.drop_constraint('unique_roles', 'roles_users', type_='unique')
