"""Fill ZUPC new fields

Revision ID: 49da8bf913fb
Revises: ee481a0870c6
Create Date: 2021-02-03 08:47:04.960369

"""
import uuid
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '49da8bf913fb'
down_revision = 'ee481a0870c6'
branch_labels = None
depends_on = None


def upgrade():
    # Needed so it doesn't take hours
    op.create_index('zupc_parent_id_idx', 'ZUPC', ['parent_id'])
    print('Index created')

    conn = op.get_bind()

    for i, (zupc_pk,) in enumerate(conn.execute(sa.text('SELECT id FROM "ZUPC" WHERE parent_id = id'))):  # Mind the comma
        if i % 1000 == 0:
            print(int(i / 36706 * 100), end='% ', flush=True)
        # Generate a disposable ZUPC unique identifier
        conn.execute(sa.text('UPDATE "ZUPC" set zupc_id=:zupc_id WHERE id=:id', {'zupc_id': str(uuid.uuid4()), 'id': zupc_pk}))
        # Allowed towns
        conn.execute(sa.text('INSERT INTO town_zupc SELECT id, :zupc_pk FROM town WHERE insee IN (SELECT insee FROM "ZUPC" WHERE parent_id=:zupc_pk)', {
            'zupc_pk': zupc_pk
        }))

    print('100%')


def downgrade():
    op.drop_index('zupc_parent_id_idx')
    op.execute(sa.text('DELETE FROM town_zupc'))
