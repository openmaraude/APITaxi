"""remove customer.moteur_id

Revision ID: ac18f0f134d8
Revises: 1a4780fd7af6
Create Date: 2021-01-07 11:26:23.010872

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ac18f0f134d8'
down_revision = '1a4780fd7af6'
branch_labels = None
depends_on = None


def upgrade():
    # Remove hail_customer_id FOREIGN KEY (customer_id, added_by) REFERENCES customer(id, moteur_id)
    op.drop_constraint('hail_customer_id', 'hail', type_='foreignkey')

    # Remove column customer.moteur_id
    op.drop_column('customer', 'moteur_id')

    # Recreate customer primary key
    op.create_primary_key('customer_pkey', 'customer', ['id', 'added_by'])

    # Recreate hail foreign key
    op.create_foreign_key('hail_customer_id', 'hail', 'customer', ['customer_id', 'added_by'], ['id', 'added_by'])


def downgrade():
    # Create column customer.moteur_id
    op.add_column('customer', sa.Column('moteur_id', sa.INTEGER(), autoincrement=False, nullable=True))

    # Copy data from added_by
    conn = op.get_bind()
    conn.execute(sa.text('UPDATE customer SET moteur_id = added_by'))

    # Set moteur_id not nullable
    op.alter_column('customer', 'moteur_id', nullable=False)
    op.create_foreign_key(
        # PK name is not accurate, but that's how it has been named in the
        # past.
        'customer_primary_key',
        'customer',
        'user',
        ['moteur_id'],
        ['id']
    )

    # Drop hail_customer_id FOREIGN KEY (customer_id, added_by) REFERENCES customer(id, added_by)
    op.drop_constraint('hail_customer_id', 'hail', type_='foreignkey')

    # Drop customer primary key on (id, added_by) and replace with (id,
    # moteur_id)
    op.drop_constraint('customer_pkey', 'customer', type_='primary')
    op.create_primary_key('customer_pkey', 'customer', ['id', 'moteur_id'])

    # Create hail_customer_id
    op.create_foreign_key(
        'hail_customer_id',
        'hail',
        'customer',
        ['customer_id', 'added_by'],
        ['id', 'moteur_id']
    )
