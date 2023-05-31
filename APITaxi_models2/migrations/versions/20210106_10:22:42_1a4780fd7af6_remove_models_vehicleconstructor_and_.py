"""Remove models VehicleConstructor and VehicleModel

Revision ID: 1a4780fd7af6
Revises: ef391413f7a0
Create Date: 2021-01-06 10:22:42.397621

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1a4780fd7af6'
down_revision = 'ef391413f7a0'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    # Store all models
    models = {}
    for model_id, name in conn.execute(sa.text('SELECT id, name FROM model')):
        models[model_id] = name

    # Store all constructors
    constructors = {}
    for constructor_id, name in conn.execute(sa.text('SELECT id, name FROM constructor')):
        constructors[constructor_id] = name

    # Create new columns "constructor" and "model"
    op.add_column('vehicle_description', sa.Column('constructor', sa.String(), server_default='', nullable=False))
    op.add_column('vehicle_description', sa.Column('model', sa.String(), server_default='', nullable=False))

    # Fill the new columns with the values stored in "model" and "constructor"
    for obj_id, model_id, constructor_id in conn.execute(sa.text(
        'SELECT id, model_id, constructor_id FROM vehicle_description'
    )):
        conn.execute(sa.text(
            'UPDATE vehicle_description SET model = %s, constructor = %s WHERE id = %s',
            models.get(model_id, ''),
            constructors.get(constructor_id, ''),
            obj_id
        ))

    # Remove tables model and constructor
    op.drop_constraint('vehicle_description_model_id_fkey', 'vehicle_description', type_='foreignkey')
    op.drop_constraint('vehicle_description_constructor_id_fkey', 'vehicle_description', type_='foreignkey')

    op.drop_column('vehicle_description', 'constructor_id')
    op.drop_column('vehicle_description', 'model_id')

    op.drop_table('constructor')
    op.drop_table('model')


def downgrade():
    op.add_column(
        'vehicle_description',
        sa.Column('model_id', sa.INTEGER(), autoincrement=False, nullable=True)
    )
    op.add_column(
        'vehicle_description',
        sa.Column('constructor_id', sa.INTEGER(), autoincrement=False, nullable=True)
    )

    op.create_table('model',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('name', sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.PrimaryKeyConstraint('id', name='model_pkey'),
        sa.UniqueConstraint('name', name='model_name_key')
    )
    op.create_table('constructor',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('name', sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.PrimaryKeyConstraint('id', name='constructor_pkey'),
        sa.UniqueConstraint('name', name='constructor_name_key')
    )

    op.create_foreign_key(
        'vehicle_description_constructor_id_fkey',
        'vehicle_description', 'constructor',
        ['constructor_id'], ['id']
    )
    op.create_foreign_key(
        'vehicle_description_model_id_fkey',
        'vehicle_description', 'model',
        ['model_id'], ['id']
    )

    conn = op.get_bind()

    models = {}
    for model, in conn.execute(sa.text('SELECT DISTINCT(model) FROM vehicle_description')):
        if not model:
            continue
        model_id = conn.execute(
            'INSERT INTO model(name) VALUES(%s) RETURNING id', model
        ).fetchone()[0]
        models[model] = model_id

    constructors = {}
    for constructor, in conn.execute(sa.text('SELECT DISTINCT(constructor) FROM vehicle_description')):
        if not constructor:
            continue
        constructor_id = conn.execute(sa.text(
            'INSERT INTO constructor(name) VALUES(%s) RETURNING id', constructor
        )).fetchone()[0]
        constructors[constructor] = constructor_id

    for obj_id, model, constructor in conn.execute(
        'SELECT id, model, constructor FROM vehicle_description'
    ):
        conn.execute(
            'UPDATE vehicle_description SET model_id = %s, constructor_id = %s WHERE id = %s',
            models[model] if model else None,
            constructors[constructor] if constructor else None,
            obj_id
        )

    op.drop_column('vehicle_description', 'model')
    op.drop_column('vehicle_description', 'constructor')
