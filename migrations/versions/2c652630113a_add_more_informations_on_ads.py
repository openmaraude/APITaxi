"""Add more informations on ADS

Revision ID: 2c652630113a
Revises: 27df69f29c56
Create Date: 2015-04-08 11:24:02.213755

"""

# revision identifiers, used by Alembic.
revision = '2c652630113a'
down_revision = '27df69f29c56'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

vehicle_type = postgresql.ENUM('sedan', 'mpv', 'station_wagon', 'normal',
        name='vehicle_type')

def upgrade():
    vehicle_type.create(op.get_bind())
    op.add_column('ADS', sa.Column('AC_vehicle', sa.Boolean(), nullable=False))
    op.add_column('ADS', sa.Column('amex_accepted', sa.Boolean(), nullable=False))
    op.add_column('ADS', sa.Column('baby_seat', sa.Boolean(), nullable=False))
    op.add_column('ADS', sa.Column('bank_check_accepted', sa.Boolean(), nullable=False))
    op.add_column('ADS', sa.Column('bike_accepted', sa.Boolean(), nullable=False))
    op.add_column('ADS', sa.Column('color', sa.String(length=255), nullable=False))
    op.add_column('ADS', sa.Column('conventionne', sa.Boolean(), nullable=False))
    op.add_column('ADS', sa.Column('credit_card_accepted', sa.Boolean(), nullable=False))
    op.add_column('ADS', sa.Column('dvd_player', sa.Boolean(), nullable=False))
    op.add_column('ADS', sa.Column('every_destination', sa.Boolean(), nullable=False))
    op.add_column('ADS', sa.Column('fresh_drink', sa.Boolean(), nullable=False))
    op.add_column('ADS', sa.Column('gps', sa.Boolean(), nullable=False))
    op.add_column('ADS', sa.Column('luxary', sa.Boolean(), nullable=False))
    op.add_column('ADS', sa.Column('nfc_cc_accepted', sa.Boolean(), nullable=False))
    op.add_column('ADS', sa.Column('pet_accepted', sa.Boolean(), nullable=False))
    op.add_column('ADS', sa.Column('snv', sa.Boolean(), nullable=False))
    op.add_column('ADS', sa.Column('telepeage', sa.Boolean(), nullable=False))
    op.add_column('ADS', sa.Column('type', vehicle_type, nullable=False))
    op.add_column('ADS', sa.Column('wifi', sa.Boolean(), nullable=False))


def downgrade():
    op.drop_column('ADS', 'wifi')
    op.drop_column('ADS', 'type')
    op.drop_column('ADS', 'telepeage')
    op.drop_column('ADS', 'snv')
    op.drop_column('ADS', 'pet_accepted')
    op.drop_column('ADS', 'nfc_cc_accepted')
    op.drop_column('ADS', 'luxary')
    op.drop_column('ADS', 'gps')
    op.drop_column('ADS', 'fresh_drink')
    op.drop_column('ADS', 'every_destination')
    op.drop_column('ADS', 'dvd_player')
    op.drop_column('ADS', 'credit_card_accepted')
    op.drop_column('ADS', 'conventionne')
    op.drop_column('ADS', 'color')
    op.drop_column('ADS', 'bike_accepted')
    op.drop_column('ADS', 'bank_check_accepted')
    op.drop_column('ADS', 'baby_seat')
    op.drop_column('ADS', 'amex_accepted')
    op.drop_column('ADS', 'AC_vehicle')
