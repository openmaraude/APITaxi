"""Add one vehicle caracteristic per operator

Revision ID: 1ee1afe31462
Revises: b0eeeeb2671
Create Date: 2015-05-11 17:55:55.525520

"""

# revision identifiers, used by Alembic.
revision = '1ee1afe31462'
down_revision = 'b0eeeeb2671'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

sources_enum = postgresql.ENUM('form', 'api', name='sources', create_type=False)
vehicle_enum = postgresql.ENUM('sedan', 'mpv', 'station_wagon', 'normal', 
                  name='vehicle_enum', create_type=False)

def upgrade():
    conn = op.get_bind()
    sources_enum.create(conn, checkfirst=True)
    vehicle_enum.create(conn, checkfirst=True)
    model_table = op.create_table('model',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )

    map_model_id = dict()
    for r in conn.execute(sa.text('SELECT DISTINCT(model) from vehicle')):
        ins = conn.execute(model_table.insert().values(name=r[0]))
        map_model_id[r[0]] = ins.inserted_primary_key[0]

    constructor_table = op.create_table('constructor',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )

    map_constructor_id = dict()
    for r in conn.execute(sa.text('SELECT DISTINCT(constructor) from vehicle')):
        ins = conn.execute(constructor_table.insert().values(name=r[0]))
        map_constructor_id[r[0]] = ins.inserted_primary_key[0]

    vehicle_descriptions = op.create_table('vehicle_description',
    sa.Column('added_at', sa.DateTime(), nullable=True),
    sa.Column('added_via', sources_enum, nullable=False),
    sa.Column('source', sa.String(length=255), nullable=False),
    sa.Column('last_update_at', sa.DateTime(), nullable=True),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('model_id', sa.Integer(), nullable=True),
    sa.Column('constructor_id', sa.Integer(), nullable=True),
    sa.Column('model_year', sa.Integer(), nullable=True),
    sa.Column('engine', sa.String(length=80), nullable=True),
    sa.Column('horse_power', sa.Float(), nullable=True),
    sa.Column('relais', sa.Boolean(), nullable=True),
    sa.Column('horodateur', sa.String(length=255), nullable=True),
    sa.Column('taximetre', sa.String(length=255), nullable=True),
    sa.Column('date_dernier_ct', sa.Date(), nullable=True),
    sa.Column('date_validite_ct', sa.Date(), nullable=True),
    sa.Column('special_need_vehicle', sa.Boolean(), nullable=True),
    sa.Column('type_', vehicle_enum, nullable=True),
    sa.Column('luxury', sa.Boolean(), nullable=True),
    sa.Column('credit_card_accepted', sa.Boolean(), nullable=True),
    sa.Column('nfc_cc_accepted', sa.Boolean(), nullable=True),
    sa.Column('amex_accepted', sa.Boolean(), nullable=True),
    sa.Column('bank_check_accepted', sa.Boolean(), nullable=True),
    sa.Column('fresh_drink', sa.Boolean(), nullable=True),
    sa.Column('dvd_player', sa.Boolean(), nullable=True),
    sa.Column('tablet', sa.Boolean(), nullable=True),
    sa.Column('wifi', sa.Boolean(), nullable=True),
    sa.Column('baby_seat', sa.Boolean(), nullable=True),
    sa.Column('bike_accepted', sa.Boolean(), nullable=True),
    sa.Column('pet_accepted', sa.Boolean(), nullable=True),
    sa.Column('air_con', sa.Boolean(), nullable=True),
    sa.Column('electronic_toll', sa.Boolean(), nullable=True),
    sa.Column('gps', sa.Boolean(), nullable=True),
    sa.Column('cpam_conventionne', sa.Boolean(), nullable=True),
    sa.Column('every_destination', sa.Boolean(), nullable=True),
    sa.Column('color', sa.String(length=255), nullable=True),
    sa.Column('vehicle_id', sa.Integer(), nullable=True),
    sa.Column('added_by', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['added_by'], ['user.id'], ),
    sa.ForeignKeyConstraint(['constructor_id'], ['constructor.id'], ),
    sa.ForeignKeyConstraint(['model_id'], ['model.id'], ),
    sa.ForeignKeyConstraint(['vehicle_id'], ['vehicle.id'], ),
    sa.PrimaryKeyConstraint('id'),
    #We'll be erased
    sa.Column('licence_plate', sa.String())
    )

    print('ajout entries dans vehicle_descriptions')
    conn = op.get_bind()
    args = ['air_con', 'wifi', 'pet_accepted', 'luxury', 'fresh_drink',
            'tablet', 'every_destination', 'cpam_conventionne', 'bike_accepted',
            'nfc_cc_accepted', 'baby_seat', 'bank_check_accepted',
            'special_need_vehicle', 'credit_card_accepted', 'electronic_toll',
            'dvd_player', 'amex_accepted', 'gps', 'added_by', 'added_via',
            'source', 'model', 'constructor', 'licence_plate', 'model_year',
            'horse_power', 'engine', 'horodateur', 'taximetre',
            'date_dernier_ct', 'date_validite_ct']
    print('select')
    res = conn.execute(sa.text('SELECT {} FROM vehicle'.format(",".join(args))))
    results = res.fetchall()
    vehicles_characs = [dict([(args[i], r[i]) for i in range(0, len(args))]) for r in results]
    for v in vehicles_characs:
        v['model_id'] = map_model_id[v['model']]
        del v['model']
        v['constructor_id'] = map_constructor_id[v['constructor']]
        del v['constructor']

    print('bulk insert')
    op.bulk_insert(vehicle_descriptions, vehicles_characs)

    print('Create temp table')
    conn.execute(sa.text("""CREATE TEMP TABLE vehicle_temp AS 
                  SELECT DISTINCT(licence_plate) as licence_plate, min(id) as id
                  FROM vehicle GROUP BY licence_plate"""))

    print('Update ADS')
    conn.execute(sa.text("""UPDATE "ADS" set vehicle_id =
                    (SELECT vehicle_temp.id FROM vehicle
                     JOIN vehicle_temp 
                     ON vehicle_temp.licence_plate = vehicle.licence_plate
                     WHERE "ADS".vehicle_id = vehicle.id)"""))

    print('Update taxi')
    conn.execute(sa.text("""UPDATE taxi set vehicle_id =
                    (SELECT vehicle_temp.id FROM vehicle
                     JOIN vehicle_temp 
                     ON vehicle_temp.licence_plate = vehicle.licence_plate
                     WHERE taxi.vehicle_id = vehicle.id)"""))
    print('Update vehicle_description')
    conn.execute(sa.text("""UPDATE vehicle_description set vehicle_id =
                    (SELECT vehicle_temp.id FROM vehicle_temp
                     WHERE vehicle_temp.licence_plate = vehicle_description.licence_plate)"""))
    op.drop_constraint('taxi_vehicle_id_fkey', 'taxi')
    op.drop_constraint('ADS_vehicle_id_fkey', 'ADS')
    op.drop_constraint('vehicle_description_vehicle_id_fkey', 'vehicle_description')
    op.drop_column('vehicle_description', 'licence_plate')

    print('Delete duplicate')
    conn.execute(sa.text('TRUNCATE vehicle'))



    op.create_unique_constraint(None, 'vehicle', ['licence_plate'])
    op.drop_constraint('vehicle_added_by_fkey', 'vehicle', type_='foreignkey')
    op.drop_column('vehicle', 'air_con')
    op.drop_column('vehicle', 'horodateur')
    op.drop_column('vehicle', 'color')
    op.drop_column('vehicle', 'date_dernier_ct')
    op.drop_column('vehicle', 'date_validite_ct')
    op.drop_column('vehicle', 'credit_card_accepted')
    op.drop_column('vehicle', 'electronic_toll')
    op.drop_column('vehicle', 'fresh_drink')
    op.drop_column('vehicle', 'cpam_conventionne')
    op.drop_column('vehicle', 'added_via')
    op.drop_column('vehicle', 'dvd_player')
    op.drop_column('vehicle', 'taximetre')
    op.drop_column('vehicle', 'every_destination')
    op.drop_column('vehicle', 'source')
    op.drop_column('vehicle', 'nfc_cc_accepted')
    op.drop_column('vehicle', 'baby_seat')
    op.drop_column('vehicle', 'special_need_vehicle')
    op.drop_column('vehicle', 'amex_accepted')
    op.drop_column('vehicle', 'gps')
    op.drop_column('vehicle', 'engine')
    op.drop_column('vehicle', 'pet_accepted')
    op.drop_column('vehicle', 'relais')
    op.drop_column('vehicle', 'last_update_at')
    op.drop_column('vehicle', 'bank_check_accepted')
    op.drop_column('vehicle', 'luxury')
    op.drop_column('vehicle', 'horse_power')
    op.drop_column('vehicle', 'model_year')
    op.drop_column('vehicle', 'tablet')
    op.drop_column('vehicle', 'wifi')
    op.drop_column('vehicle', 'added_at')
    op.drop_column('vehicle', 'type_')
    op.drop_column('vehicle', 'added_by')
    op.drop_column('vehicle', 'constructor')
    op.drop_column('vehicle', 'bike_accepted')
    op.drop_column('vehicle', 'model')

    conn.execute(sa.text("""INSERT INTO vehicle 
                    (licence_plate, id)
                    SELECT licence_plate, id
                    FROM vehicle_temp"""))

    op.create_foreign_key('taxi_vehicle_id_fkey', 'taxi', 'vehicle',
            ['vehicle_id'], ['id'])
    op.create_foreign_key('ADS_vehicle_id_fkey', 'ADS', 'vehicle',
            ['vehicle_id'], ['id'])
    op.create_foreign_key('vehicle_description_vehicle_id_fkey',
            'vehicle_description', 'vehicle', ['vehicle_id'], ['id'])


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('vehicle', sa.Column('model', sa.VARCHAR(length=255), autoincrement=False, nullable=True))
    op.add_column('vehicle', sa.Column('bike_accepted', sa.BOOLEAN(), autoincrement=False, nullable=True))
    op.add_column('vehicle', sa.Column('constructor', sa.VARCHAR(length=255), autoincrement=False, nullable=True))
    op.add_column('vehicle', sa.Column('added_by', sa.INTEGER(), autoincrement=False, nullable=True))
    op.add_column('vehicle', sa.Column('type_', postgresql.ENUM('sedan', 'mpv', 'station_wagon', 'normal', name='vehicle_type_enum'), autoincrement=False, nullable=True))
    op.add_column('vehicle', sa.Column('added_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True))
    op.add_column('vehicle', sa.Column('wifi', sa.BOOLEAN(), autoincrement=False, nullable=True))
    op.add_column('vehicle', sa.Column('tablet', sa.BOOLEAN(), autoincrement=False, nullable=True))
    op.add_column('vehicle', sa.Column('model_year', sa.INTEGER(), autoincrement=False, nullable=True))
    op.add_column('vehicle', sa.Column('horse_power', postgresql.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True))
    op.add_column('vehicle', sa.Column('luxury', sa.BOOLEAN(), autoincrement=False, nullable=True))
    op.add_column('vehicle', sa.Column('bank_check_accepted', sa.BOOLEAN(), autoincrement=False, nullable=True))
    op.add_column('vehicle', sa.Column('last_update_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True))
    op.add_column('vehicle', sa.Column('relais', sa.BOOLEAN(), autoincrement=False, nullable=True))
    op.add_column('vehicle', sa.Column('pet_accepted', sa.BOOLEAN(), autoincrement=False, nullable=True))
    op.add_column('vehicle', sa.Column('engine', sa.VARCHAR(length=80), autoincrement=False, nullable=True))
    op.add_column('vehicle', sa.Column('gps', sa.BOOLEAN(), autoincrement=False, nullable=True))
    op.add_column('vehicle', sa.Column('amex_accepted', sa.BOOLEAN(), autoincrement=False, nullable=True))
    op.add_column('vehicle', sa.Column('special_need_vehicle', sa.BOOLEAN(), autoincrement=False, nullable=True))
    op.add_column('vehicle', sa.Column('baby_seat', sa.BOOLEAN(), autoincrement=False, nullable=True))
    op.add_column('vehicle', sa.Column('nfc_cc_accepted', sa.BOOLEAN(), autoincrement=False, nullable=True))
    op.add_column('vehicle', sa.Column('source', sa.VARCHAR(length=255), autoincrement=False, nullable=False))
    op.add_column('vehicle', sa.Column('every_destination', sa.BOOLEAN(), autoincrement=False, nullable=True))
    op.add_column('vehicle', sa.Column('taximetre', sa.VARCHAR(length=255), autoincrement=False, nullable=True))
    op.add_column('vehicle', sa.Column('dvd_player', sa.BOOLEAN(), autoincrement=False, nullable=True))
    op.add_column('vehicle', sa.Column('added_via', postgresql.ENUM('form', 'api', name='sources_enum'), autoincrement=False, nullable=False))
    op.add_column('vehicle', sa.Column('cpam_conventionne', sa.BOOLEAN(), autoincrement=False, nullable=True))
    op.add_column('vehicle', sa.Column('fresh_drink', sa.BOOLEAN(), autoincrement=False, nullable=True))
    op.add_column('vehicle', sa.Column('electronic_toll', sa.BOOLEAN(), autoincrement=False, nullable=True))
    op.add_column('vehicle', sa.Column('credit_card_accepted', sa.BOOLEAN(), autoincrement=False, nullable=True))
    op.add_column('vehicle', sa.Column('date_validite_ct', sa.DATE(), autoincrement=False, nullable=True))
    op.add_column('vehicle', sa.Column('date_dernier_ct', sa.DATE(), autoincrement=False, nullable=True))
    op.add_column('vehicle', sa.Column('color', sa.VARCHAR(length=255), autoincrement=False, nullable=True))
    op.add_column('vehicle', sa.Column('horodateur', sa.VARCHAR(length=255), autoincrement=False, nullable=True))
    op.add_column('vehicle', sa.Column('air_con', sa.BOOLEAN(), autoincrement=False, nullable=True))
    op.create_foreign_key('vehicle_added_by_fkey', 'vehicle', 'user', ['added_by'], ['id'])
    op.drop_constraint('vehicle_licence_plate_key', 'vehicle', type_='unique')
    op.alter_column('ADS', 'added_via',
               existing_type=postgresql.ENUM('form', 'api', name='via'),
               nullable=True)
    op.drop_table('vehicle_description')
    op.drop_table('constructor')
    op.drop_table('model')
    ### end Alembic commands ###
