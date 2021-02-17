"""Driver.departement not null

Revision ID: 81bab94157fc
Revises: 5887f860f0ee
Create Date: 2021-02-17 14:49:02.316367

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '81bab94157fc'
down_revision = '5887f860f0ee'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('driver', 'departement_id',
                    existing_type=sa.INTEGER(),
                    nullable=False)


def downgrade():
    op.alter_column('driver', 'departement_id',
                    existing_type=sa.INTEGER(),
                    nullable=True)
