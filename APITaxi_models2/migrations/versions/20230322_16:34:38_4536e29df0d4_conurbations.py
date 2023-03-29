"""conurbations

Revision ID: 4536e29df0d4
Revises: 43685d1824b7
Create Date: 2023-03-22 16:34:38.417188

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '4536e29df0d4'
down_revision = '43685d1824b7'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('conurbation',
        sa.Column('added_at', sa.DateTime(), nullable=False),
        sa.Column('added_via', postgresql.ENUM('form', 'api', name='via', create_type=False), nullable=False),
        sa.Column('source', sa.String(length=255), nullable=False),
        sa.Column('last_update_at', sa.DateTime(), nullable=True),
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('members', postgresql.ARRAY(sa.String(length=5)), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Easier to register a few conurbations while I'm at it
    op.execute("""
    insert into conurbation (id, name, added_at, added_via, source, last_update_at, members) values
        ('lyon', 'Grand Lyon', now(), 'api', 'added_by', now(), '{69123,69003,69029,69033,69034,69040,69044,69046,69271,69063,69273,69068,69069,69071,69072,69275,69081,69276,69085,69087,69088,69089,69278,69091,69096,69100,69279,69116,69117,69127,69282,69283,69284,69142,69143,69149,69152,69153,69163,69286,69168,69191,69194,69202,69199,69204,69205,69207,69290,69233,69292,69293,69296,69244,69250,69256,69259,69260,69266}'),
        ('grenoble', 'Grenoble-Alpes Métropole', now(), 'api', 'added_by', now(), '{38185,38057,38059,38071,38068,38111,38126,38150,38151,38158,38169,38170,38179,38187,38188,38200,38229,38235,38258,38252,38271,38277,38279,38281,38309,38317,38325,38328,38364,38382,38388,38421,38423,38436,38445,38471,38472,38474,38478,38485,38486,38516,38524,38528,38529,38533,38540,38545,38562}'),
        ('rouen', 'Métropole Rouen Normandie', now(), 'api', 'added_by', now(), '{76540,76005,76020,76039,76056,76069,76088,76095,76108,76103,76116,76131,76157,76165,76178,76212,76216,76222,76231,76237,76273,76475,76282,76313,76319,76322,76350,76354,76366,76367,76377,76378,76391,76402,76410,76429,76436,76451,76448,76457,76464,76474,76484,76486,76497,76498,76513,76514,76536,76550,76558,76560,76561,76575,76591,76599,76614,76617,76631,76634,76636,76640,76608,76681,76682,76705,76709,76717,76750,76753,76759}');
    """)


def downgrade():
    op.drop_table('conurbation')
