"""Add max distance to "ZUPC"

Revision ID: 986de51c9c9f
Revises: 3e54873a977a
Create Date: 2016-10-05 11:07:13.831909

"""

# revision identifiers, used by Alembic.
revision = '986de51c9c9f'
down_revision = '3e54873a977a'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.execute('CREATE TABLE "ZUPC_new" (LIKE "ZUPC" INCLUDING CONSTRAINTS);')
    op.execute('INSERT INTO "ZUPC_new" SELECT * FROM "ZUPC";')
    op.add_column('ZUPC_new', sa.Column('max_distance', sa.Integer(), nullable=True))
    op.execute('ALTER TABLE "ADS" DROP CONSTRAINT "fkey_zupc_ads"')
    op.execute('ALTER TABLE "ZUPC" DROP CONSTRAINT "zupc_parent_foreign_key"')
    op.execute('DROP TABLE "ZUPC"')
    op.execute('ALTER TABLE "ZUPC_new" RENAME TO "ZUPC";')
    op.execute("""
               ALTER TABLE "ZUPC" ADD PRIMARY KEY (id);
               CREATE INDEX zupc_shape_igx ON "ZUPC" USING GIST (shape);
               CLUSTER "ZUPC" USING zupc_shape_igx;
               CREATE INDEX zupc_shape_idx ON "ZUPC" USING GIST (shape);
               ALTER TABLE "ZUPC" ADD CONSTRAINT ZUPC_departement_id_fkey FOREIGN KEY (departement_id) REFERENCES departement (id) MATCH FULL;
               ALTER TABLE "ZUPC" ADD CONSTRAINT zupc_parent_foreign_key FOREIGN KEY (parent_id) REFERENCES "ZUPC" (id) MATCH FULL;
               ALTER TABLE "ADS" ADD CONSTRAINT fkey_zupc_ads FOREIGN KEY (zupc_id) REFERENCES "ZUPC" (id) MATCH FULL;
               """)


def downgrade():
    op.execute('CREATE TABLE "ZUPC_new" (LIKE "ZUPC" INCLUDING CONSTRAINTS);')
    op.execute('INSERT INTO "ZUPC_new" SELECT * FROM "ZUPC";')
    op.drop_column('ZUPC', 'max_distance')
    op.execute('ALTER TABLE "ADS" DROP CONSTRAINT "fkey_zupc_ads"')
    op.execute('ALTER TABLE "ZUPC" DROP CONSTRAINT "zupc_parent_foreign_key"')
    op.execute('DROP TABLE "ZUPC"')
    op.execute('ALTER TABLE "ZUPC_new" RENAME TO "ZUPC";')
    op.execute("""
               ALTER TABLE "ZUPC" ADD PRIMARY KEY (id);
               CREATE INDEX zupc_shape_igx ON "ZUPC" USING GIST (shape);
               CLUSTER "ZUPC" USING zupc_shape_igx;
               CREATE INDEX zupc_shape_idx ON "ZUPC" USING GIST (shape);
               ALTER TABLE "ZUPC" ADD CONSTRAINT ZUPC_departement_id_fkey FOREIGN KEY (departement_id) REFERENCES departement (id) MATCH FULL;
               ALTER TABLE "ZUPC" ADD CONSTRAINT zupc_parent_foreign_key FOREIGN KEY (parent_id) REFERENCES "ZUPC" (id) MATCH FULL;
               ALTER TABLE "ADS" ADD CONSTRAINT fkey_zupc_ads FOREIGN KEY (zupc_id) REFERENCES "ZUPC" (id) MATCH FULL;
               """)
