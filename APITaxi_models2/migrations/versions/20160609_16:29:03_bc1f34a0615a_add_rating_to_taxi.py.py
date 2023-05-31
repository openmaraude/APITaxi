"""Add rating to taxi

Revision ID: bc1f34a0615a
Revises: 71cacff30853
Create Date: 2016-06-09 16:29:03.021476

"""

# revision identifiers, used by Alembic.
revision = 'bc1f34a0615a'
down_revision = '71cacff30853'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.add_column('taxi', sa.Column('rating', sa.Float(), nullable=True))
    op.execute(sa.text('UPDATE taxi set rating=4.5;'))


def downgrade():
    op.drop_column('taxi', 'rating')
