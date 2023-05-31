"""Make strings not nullable (2)

Revision ID: 5b8d8ca36aeb
Revises: 5d164bbb4813
Create Date: 2021-06-14 13:57:26.772630

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5b8d8ca36aeb'
down_revision = '5d164bbb4813'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    conn.execute(sa.text('''update customer set phone_number = '' where phone_number is null'''))
    conn.execute(sa.text('''update hail set taxi_phone_number = '' where taxi_phone_number is null'''))
    conn.execute(sa.text('''update role set description = '' where description is null'''))
    conn.execute(sa.text('''update vehicle_description set color = '' where color is null'''))
    conn.execute(sa.text('''update vehicle_description set engine = '' where engine is null'''))
    conn.execute(sa.text('''update vehicle_description set horodateur = '' where horodateur is null'''))
    conn.execute(sa.text('''update vehicle_description set taximetre = '' where taximetre is null'''))

    op.alter_column('customer', 'phone_number',
                    existing_type=sa.VARCHAR(),
                    nullable=False)
    op.alter_column('hail', 'taxi_phone_number',
                    existing_type=sa.VARCHAR(),
                    server_default='',
                    nullable=False)
    op.alter_column('role', 'description',
                    existing_type=sa.VARCHAR(length=255),
                    server_default='',
                    nullable=False)
    op.alter_column('vehicle_description', 'color',
                    existing_type=sa.VARCHAR(length=255),
                    server_default='',
                    nullable=False)
    op.alter_column('vehicle_description', 'engine',
                    existing_type=sa.VARCHAR(length=80),
                    server_default='',
                    nullable=False)
    op.alter_column('vehicle_description', 'horodateur',
                    existing_type=sa.VARCHAR(length=255),
                    server_default='',
                    nullable=False)
    op.alter_column('vehicle_description', 'taximetre',
                    existing_type=sa.VARCHAR(length=255),
                    server_default='',
                    nullable=False)


def downgrade():
    op.alter_column('vehicle_description', 'taximetre',
                    existing_type=sa.VARCHAR(length=255),
                    nullable=True)
    op.alter_column('vehicle_description', 'horodateur',
                    existing_type=sa.VARCHAR(length=255),
                    nullable=True)
    op.alter_column('vehicle_description', 'engine',
                    existing_type=sa.VARCHAR(length=80),
                    nullable=True)
    op.alter_column('vehicle_description', 'color',
                    existing_type=sa.VARCHAR(length=255),
                    nullable=True)
    op.alter_column('role', 'description',
                    existing_type=sa.VARCHAR(length=255),
                    nullable=True)
    op.alter_column('hail', 'taxi_phone_number',
                    existing_type=sa.VARCHAR(),
                    nullable=True)
    op.alter_column('customer', 'phone_number',
                    existing_type=sa.VARCHAR(),
                    nullable=True)
