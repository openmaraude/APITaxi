"""Add more informations on ADS

Revision ID: 59e5faf237f8
Revises: 27df69f29c56
Create Date: 2015-04-08 16:34:22.387152

"""

# revision identifiers, used by Alembic.
revision = '59e5faf237f8'
down_revision = '27df69f29c56'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    vehicle_type = postgresql.ENUM('sedan', 'mpv', 'station_wagon', 'normal',
            name='vehicle_type')
    op.add_column('ADS', sa.Column('AC_vehicle', sa.Boolean(), nullable=True))
    op.add_column('ADS', sa.Column('amex_accepted', sa.Boolean(), nullable=True))
    op.add_column('ADS', sa.Column('baby_seat', sa.Boolean(), nullable=True))
    op.add_column('ADS', sa.Column('bank_check_accepted', sa.Boolean(), nullable=True))
    op.add_column('ADS', sa.Column('bike_accepted', sa.Boolean(), nullable=True))
    op.add_column('ADS', sa.Column('color', sa.String(length=255), nullable=True))
    op.add_column('ADS', sa.Column('conventionne', sa.Boolean(), nullable=True))
    op.add_column('ADS', sa.Column('credit_card_accepted', sa.Boolean(), nullable=True))
    op.add_column('ADS', sa.Column('dvd_player', sa.Boolean(), nullable=True))
    op.add_column('ADS', sa.Column('every_destination', sa.Boolean(), nullable=True))
    op.add_column('ADS', sa.Column('fresh_drink', sa.Boolean(), nullable=True))
    op.add_column('ADS', sa.Column('gps', sa.Boolean(), nullable=True))
    op.add_column('ADS', sa.Column('luxary', sa.Boolean(), nullable=True))
    op.add_column('ADS', sa.Column('nfc_cc_accepted', sa.Boolean(), nullable=True))
    op.add_column('ADS', sa.Column('pet_accepted', sa.Boolean(), nullable=True))
    op.add_column('ADS', sa.Column('snv', sa.Boolean(), nullable=True))
    op.add_column('ADS', sa.Column('telepeage', sa.Boolean(), nullable=True))
    op.add_column('ADS', sa.Column('type_', vehicle_type, nullable=True))
    op.add_column('ADS', sa.Column('wifi', sa.Boolean(), nullable=True))


def downgrade():
    op.drop_column('ADS', 'wifi')
    op.drop_column('ADS', 'type_')
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
