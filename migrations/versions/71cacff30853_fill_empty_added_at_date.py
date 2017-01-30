"""Fill empty added_at date

Revision ID: 71cacff30853
Revises: d26b4a2cc2ef
Create Date: 2016-04-04 16:43:45.040889

"""

# revision identifiers, used by Alembic.
revision = '71cacff30853'
down_revision = 'd26b4a2cc2ef'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from APITaxi_models.hail import Customer, Hail
from APITaxi_models.taxis import ADS, Driver, Taxi
from APITaxi_models.security import Role, User
from APITaxi_models.vehicle import Vehicle, VehicleDescription
import APITaxi_models as models
from datetime import datetime

def upgrade():
    for m in [models.Departement, models.ZUPC, Customer, Hail, ADS, Driver, Taxi, Role, User,
            Vehicle, VehicleDescription]:
        if not hasattr(m, 'added_at'):
            continue
        table = m.__table__
        op.execute(table.update().where(table.c.added_at == None)\
                .values({'added_at': datetime(2015,1,1)}))



def downgrade():
    pass
