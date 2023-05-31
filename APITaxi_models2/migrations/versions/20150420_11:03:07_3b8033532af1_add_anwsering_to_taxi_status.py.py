"""Add anwsering to taxi_status

Revision ID: 3b8033532af1
Revises: 408130c68e5d
Create Date: 2015-04-20 11:03:07.871121

"""

# revision identifiers, used by Alembic.
revision = '3b8033532af1'
down_revision = '408130c68e5d'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
old_enum = sa.Enum('free', 'occupied', 'oncoming', 'off',
        name='status_taxi_enum')
new_enum = sa.Enum('free', 'answering', 'occupied', 'oncoming', 'off',
        name='status_taxi_enum')
tmp_enum = sa.Enum('free', 'answering', 'occupied', 'oncoming', 'off',
        name='_status_taxi_enum')
taxi = sa.sql.table('taxi',
                   sa.Column('status', new_enum, nullable=True))

def upgrade():
    tmp_enum.create(op.get_bind(), checkfirst=False)
    op.execute(sa.text('ALTER TABLE taxi ALTER COLUMN status TYPE _status_taxi_enum'
                           ' USING status::text::_status_taxi_enum'))
    old_enum.drop(op.get_bind(), checkfirst=False)
    new_enum.create(op.get_bind(), checkfirst=False)
    op.execute(sa.text('ALTER TABLE taxi ALTER COLUMN status TYPE status_taxi_enum'
                           ' USING status::text::status_taxi_enum'))
    tmp_enum.drop(op.get_bind(), checkfirst=False)

def downgrade():
    op.execute(taxi.update().where(taxi.c.status=='answering')
               .values(status='free'))
    tmp_enum.create(op.get_bind(), checkfirst=False)
    op.execute(sa.text('ALTER TABLE taxi ALTER COLUMN status TYPE _status_taxi_enum'
               ' USING status::text::_status_taxi_enum'))
    new_enum.drop(op.get_bind(), checkfirst=False)
    old_enum.create(op.get_bind(), checkfirst=False)
    op.execute(sa.text('ALTER TABLE taxi ALTER COLUMN status TYPE status_taxi_enum'
               ' USING status::text::status_taxi_enum'))
    tmp_enum.drop(op.get_bind(), checkfirst=False)
