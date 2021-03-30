"""Missing migration to users

Revision ID: 5d28367f8ffe
Revises: 565f85bb1366
Create Date: 2021-03-30 08:06:41.789768

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5d28367f8ffe'
down_revision = '565f85bb1366'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('roles_users', 'role_id',
                    existing_type=sa.INTEGER(),
                    nullable=False)
    op.alter_column('roles_users', 'user_id',
                    existing_type=sa.INTEGER(),
                    nullable=False)


def downgrade():
    op.alter_column('roles_users', 'user_id',
                    existing_type=sa.INTEGER(),
                    nullable=True)
    op.alter_column('roles_users', 'role_id',
                    existing_type=sa.INTEGER(),
                    nullable=True)
