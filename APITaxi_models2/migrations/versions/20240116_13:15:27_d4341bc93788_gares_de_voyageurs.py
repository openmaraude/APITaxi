"""Gares de voyageurs

Revision ID: d4341bc93788
Revises: 5eacbba5d046
Create Date: 2024-01-16 13:15:27.724855

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import geoalchemy2

# revision identifiers, used by Alembic.
revision = 'd4341bc93788'
down_revision = '5eacbba5d046'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('gare_voyageur',
        sa.Column('code', sa.String(), nullable=False),
        sa.Column('code_gare', sa.String(), nullable=True),
        sa.Column('uic_code', sa.String(), nullable=True),
        sa.Column('dtfinval', sa.Date(), nullable=True),
        sa.Column('alias_libelle_noncontraint', sa.String(), nullable=True),
        sa.Column('adresse_cp', sa.String(), nullable=True),
        sa.Column('commune_code', sa.String(), nullable=True),
        sa.Column('commune_libellemin', sa.String(), nullable=True),
        sa.Column('departement_numero', sa.String(), nullable=True),
        sa.Column('departement_libellemin', sa.String(), nullable=True),
        sa.Column('longitude_entreeprincipale_wgs84', sa.String(), nullable=True),
        sa.Column('latitude_entreeprincipale_wgs84', sa.String(), nullable=True),
        sa.Column('segmentdrg_libelle', sa.String(), nullable=True),
        sa.Column('niveauservice_libelle', sa.String(), nullable=True),
        sa.Column('rg_libelle', sa.String(), nullable=True),
        sa.Column('gare_alias_libelle_noncontraint', sa.String(), nullable=True),
        sa.Column('gare_alias_libelle_fronton', sa.String(), nullable=True),
        sa.Column('gare_agencegc_libelle', sa.String(), nullable=True),
        sa.Column('gare_regionsncf_libelle', sa.String(), nullable=True),
        sa.Column('gare_ug_libelle', sa.String(), nullable=True),
        sa.Column('gare_ut_libelle', sa.String(), nullable=True),
        sa.Column('gare_nbpltf', sa.Integer(), nullable=True),
        sa.Column('tvs', sa.String(), nullable=True),
        sa.Column('wgs_84', geoalchemy2.types.Geography(geometry_type='POINT', srid=4326, from_text='ST_GeogFromText', name='geography'), nullable=True),
        sa.Column('tgv', sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint('code'),
        sa.UniqueConstraint('code_gare')
    )


def downgrade():
    op.drop_table('gare_voyageur')
