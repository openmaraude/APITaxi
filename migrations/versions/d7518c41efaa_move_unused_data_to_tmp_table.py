"""Move unused data to tmp_table

Revision ID: d7518c41efaa
Revises: f8c0bde5d368
Create Date: 2019-11-22 11:28:02.036664

"""

# revision identifiers, used by Alembic.
revision = 'd7518c41efaa'
down_revision = 'f8c0bde5d368'

from alembic import op
import sqlalchemy as sa


def upgrade():
    conn = op.get_bind()

    conn.execute(
        sa.text(
            """
            WITH archive AS(
                DELETE FROM "vehicle_description" WHERE vehicle_id IN
                 (
                     SELECT vehicle_id FROM vehicle_description
                     EXCEPT
                     SELECT vehicle_id FROM taxi
                 )
                RETURNING *
            )
            INSERT INTO tmp_vehicle_description SELECT * FROM archive
            """
        )
    )

    for table_name in ["ADS","vehicle",  "driver"]:
        conn.execute(
            sa.text(
                f"""
                    WITH archive AS(
                        DELETE FROM "{table_name}" WHERE id IN
                        (
                            SELECT id FROM {table_name}
                            EXCEPT
                            SELECT {table_name.lower()}_id FROM taxi
                        )
                        RETURNING *
                    )
                    INSERT INTO tmp_{table_name} SELECT * FROM archive
                """
            )
        )


def downgrade():
    conn = op.get_bind()

    for table_name in ["vehicle", "vehicle_description", "ADS", "driver"]:
        conn.execute(sa.text(f'INSERT INTO "{table_name}" SELECT * FROM "tmp_{table_name}"'))
        conn.execute(sa.text(f'DROP TABLE "tmp_{table_name}"'))
