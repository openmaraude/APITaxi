"""Drop ZUPC.departement

Revision ID: a3df227b3e08
Revises: 84a9553cd9ed
Create Date: 2021-02-01 16:14:25.765554

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a3df227b3e08'
down_revision = '84a9553cd9ed'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint('zupc_departement_id_fkey', 'ZUPC', type_='foreignkey')
    op.drop_column('ZUPC', 'departement_id')


def downgrade():
    op.add_column('ZUPC', sa.Column('departement_id', sa.INTEGER(), autoincrement=False, nullable=True))
    op.create_foreign_key('zupc_departement_id_fkey', 'ZUPC', 'departement', ['departement_id'], ['id'])
