"""Create unique constraints

Revision ID: ef391413f7a0
Revises: 1980911fa00e
Create Date: 2020-12-24 16:28:35.918185

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ef391413f7a0'
down_revision = '1980911fa00e'
branch_labels = None
depends_on = None


def upgrade():
    op.create_unique_constraint('unique_ads', 'ADS', ['numero', 'insee', 'added_by'])
    op.create_unique_constraint('unique_driver', 'driver', ['departement_id', 'professional_licence', 'added_by'])
    op.create_unique_constraint('unique_taxi', 'taxi', ['vehicle_id', 'ads_id', 'driver_id', 'added_by'])
    op.create_unique_constraint('unique_vehicle', 'vehicle', ['licence_plate'])


def downgrade():
    op.drop_constraint('unique_vehicle', 'vehicle', type_='unique')
    op.drop_constraint('unique_taxi', 'taxi', type_='unique')
    op.drop_constraint('unique_driver', 'driver', type_='unique')
    op.drop_constraint('unique_ads', 'ADS', type_='unique')
