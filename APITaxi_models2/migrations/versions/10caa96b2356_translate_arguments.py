"""Translate arguments

Revision ID: 10caa96b2356
Revises: 44090569867
Create Date: 2015-04-24 10:12:47.322973

"""

# revision identifiers, used by Alembic.
revision = '10caa96b2356'
down_revision = '44090569867'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
owner_type_enum = sa.Enum('company', 'individual', name='owner_type_enum')
def upgrade():
    owner_type_enum.create(op.get_bind(), checkfirst=True)
    op.add_column('ADS', sa.Column('category', sa.String(), nullable=False))
    op.add_column('ADS', sa.Column('owner_name', sa.String(), nullable=False))
    op.add_column('ADS', sa.Column('owner_type', owner_type_enum , nullable=False))
    op.alter_column('ADS', 'numero', type_=sa.String(),
               existing_type=sa.INTEGER(),
               nullable=False)
    op.drop_column('ADS', 'personne')
    op.drop_column('ADS', 'artisan')
    op.drop_column('ADS', 'nom_societe')
    op.add_column('driver', sa.Column('birth_date', sa.Date(), nullable=True))
    op.add_column('driver', sa.Column('first_name', sa.String(length=255), nullable=False))
    op.add_column('driver', sa.Column('last_name', sa.String(length=255), nullable=False))
    op.add_column('driver', sa.Column('professional_licence', sa.String(), nullable=False))
    op.drop_column('driver', 'nom')
    op.drop_column('driver', 'carte_pro')
    op.drop_column('driver', 'date_naissance')
    op.drop_column('driver', 'prenom')
    op.add_column('vehicle', sa.Column('air_con', sa.Boolean(), nullable=True))
    op.add_column('vehicle', sa.Column('constructor', sa.String(length=255), nullable=True))
    op.add_column('vehicle', sa.Column('cpam_conventionne', sa.Boolean(), nullable=True))
    op.add_column('vehicle', sa.Column('electronic_toll', sa.Boolean(), nullable=True))
    op.add_column('vehicle', sa.Column('engine', sa.String(length=80), nullable=True))
    op.add_column('vehicle', sa.Column('horse_power', sa.Float(), nullable=True))
    op.add_column('vehicle', sa.Column('licence_plate', sa.String(length=80), nullable=False))
    op.add_column('vehicle', sa.Column('luxury', sa.Boolean(), nullable=True))
    op.add_column('vehicle', sa.Column('model', sa.String(length=255), nullable=True))
    op.add_column('vehicle', sa.Column('model_year', sa.Integer(), nullable=True))
    op.add_column('vehicle', sa.Column('special_need_vehicle', sa.Boolean(), nullable=True))
    op.add_column('vehicle', sa.Column('tablet', sa.Boolean(), nullable=True))
    op.drop_column('vehicle', 'snv')
    op.drop_column('vehicle', 'conventionne')
    op.drop_column('vehicle', 'pmr')
    op.drop_column('vehicle', 'immatriculation')
    op.drop_column('vehicle', 'luxary')
    op.drop_column('vehicle', 'telepeage')
    op.drop_column('vehicle', 'puissance')
    op.drop_column('vehicle', 'marque')
    op.drop_column('vehicle', 'AC_vehicle')
    op.drop_column('vehicle', 'annee')
    op.drop_column('vehicle', 'motorisation')
    op.drop_column('vehicle', 'modele')


def downgrade():
    op.add_column('vehicle', sa.Column('modele', sa.VARCHAR(length=255), autoincrement=False, nullable=True))
    op.add_column('vehicle', sa.Column('motorisation', sa.VARCHAR(length=80), autoincrement=False, nullable=True))
    op.add_column('vehicle', sa.Column('annee', sa.INTEGER(), autoincrement=False, nullable=True))
    op.add_column('vehicle', sa.Column('AC_vehicle', sa.BOOLEAN(), autoincrement=False, nullable=True))
    op.add_column('vehicle', sa.Column('marque', sa.VARCHAR(length=255), autoincrement=False, nullable=True))
    op.add_column('vehicle', sa.Column('puissance', postgresql.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True))
    op.add_column('vehicle', sa.Column('telepeage', sa.BOOLEAN(), autoincrement=False, nullable=True))
    op.add_column('vehicle', sa.Column('luxary', sa.BOOLEAN(), autoincrement=False, nullable=True))
    op.add_column('vehicle', sa.Column('immatriculation', sa.VARCHAR(length=80), autoincrement=False, nullable=False))
    op.add_column('vehicle', sa.Column('pmr', sa.BOOLEAN(), autoincrement=False, nullable=True))
    op.add_column('vehicle', sa.Column('conventionne', sa.BOOLEAN(), autoincrement=False, nullable=True))
    op.add_column('vehicle', sa.Column('snv', sa.BOOLEAN(), autoincrement=False, nullable=True))
    op.drop_column('vehicle', 'tablet')
    op.drop_column('vehicle', 'special_need_vehicle')
    op.drop_column('vehicle', 'model_year')
    op.drop_column('vehicle', 'model')
    op.drop_column('vehicle', 'luxury')
    op.drop_column('vehicle', 'licence_plate')
    op.drop_column('vehicle', 'horse_power')
    op.drop_column('vehicle', 'engine')
    op.drop_column('vehicle', 'electronic_toll')
    op.drop_column('vehicle', 'cpam_conventionne')
    op.drop_column('vehicle', 'constructor')
    op.drop_column('vehicle', 'air_con')
    op.add_column('driver', sa.Column('prenom', sa.VARCHAR(length=255), autoincrement=False, nullable=False))
    op.add_column('driver', sa.Column('date_naissance', sa.DATE(), autoincrement=False, nullable=True))
    op.add_column('driver', sa.Column('carte_pro', sa.VARCHAR(), autoincrement=False, nullable=False))
    op.add_column('driver', sa.Column('nom', sa.VARCHAR(length=255), autoincrement=False, nullable=False))
    op.drop_column('driver', 'professional_licence')
    op.drop_column('driver', 'last_name')
    op.drop_column('driver', 'first_name')
    op.drop_column('driver', 'birth_date')
    op.add_column('ADS', sa.Column('nom_societe', sa.VARCHAR(length=255), autoincrement=False, nullable=True))
    op.add_column('ADS', sa.Column('artisan', sa.VARCHAR(length=255), autoincrement=False, nullable=True))
    owner_type_enum.drop(op.get_bind())
    op.add_column('ADS', sa.Column('personne', sa.VARCHAR(length=255), autoincrement=False, nullable=True))
    op.alter_column('ADS', 'numero',
               existing_type=sa.INTEGER(),
               nullable=True)
    op.alter_column('ADS', 'added_via',
               existing_type=postgresql.ENUM('form', 'api', name='via'),
               nullable=True)
    op.drop_column('ADS', 'owner_type')
    op.drop_column('ADS', 'owner_name')
    op.drop_column('ADS', 'category')
    ### end Alembic commands ###
