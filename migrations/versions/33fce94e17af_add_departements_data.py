# -*- coding: utf8 -*-
"""Add departements data

Revision ID: 33fce94e17af
Revises: 4a6b378729be
Create Date: 2015-03-26 17:42:22.833751

"""

# revision identifiers, used by Alembic.
revision = '33fce94e17af'
down_revision = '4a6b378729be'

from alembic import op
import sqlalchemy as sa


def upgrade():
    departement = sa.sql.table('departement',
        sa.sql.column("numero", sa.String),
        sa.sql.column("nom", sa.String))

    op.bulk_insert(departement, [
        {"numero": "01", "nom": u"Ain"},
        {"numero": "02", "nom": u"Aisne"},
        {"numero": "03", "nom": u"Allier"},
        {"numero": "04", "nom": u"Alpes-de-Haute-Provence"},
        {"numero": "05", "nom": u"Hautes-Alpes"},
        {"numero": "06", "nom": u"Alpes-Maritimes"},
        {"numero": "07", "nom": u"Ardèche"},
        {"numero": "08", "nom": u"Ardennes"},
        {"numero": "09", "nom": u"Ariège"},
        {"numero": "10", "nom": u"Aube"},
        {"numero": "11", "nom": u"Aude"},
        {"numero": "12", "nom": u"Aveyron"},
        {"numero": "13", "nom": u"Bouches-du-Rhône"},
        {"numero": "14", "nom": u"Calvados"},
        {"numero": "15", "nom": u"Cantal"},
        {"numero": "16", "nom": u"Charente"},
        {"numero": "17", "nom": u"Charente-Maritime"},
        {"numero": "18", "nom": u"Cher"},
        {"numero": "19", "nom": u"Corrèze"},
        {"numero": "2A", "nom": u"Corse-du-Sud"},
        {"numero": "2B", "nom": u"Haute-Corse"},
        {"numero": "21", "nom": u"Côte-d'Or"},
        {"numero": "22", "nom": u"Côtes-d'Armor"},
        {"numero": "23", "nom": u"Creuse"},
        {"numero": "24", "nom": u"Dordogne"},
        {"numero": "25", "nom": u"Doubs"},
        {"numero": "26", "nom": u"Drôme"},
        {"numero": "27", "nom": u"Eure"},
        {"numero": "28", "nom": u"Eure-et-Loir"},
        {"numero": "29", "nom": u"Finistère"},
        {"numero": "30", "nom": u"Gard"},
        {"numero": "31", "nom": u"Haute-Garonne"},
        {"numero": "32", "nom": u"Gers"},
        {"numero": "33", "nom": u"Gironde"},
        {"numero": "34", "nom": u"Hérault"},
        {"numero": "35", "nom": u"Ille-et-Vilaine"},
        {"numero": "36", "nom": u"Indre"},
        {"numero": "37", "nom": u"Indre-et-Loire"},
        {"numero": "38", "nom": u"Isère"},
        {"numero": "39", "nom": u"Jura"},
        {"numero": "40", "nom": u"Landes"},
        {"numero": "41", "nom": u"Loir-et-Cher"},
        {"numero": "42", "nom": u"Loire"},
        {"numero": "43", "nom": u"Haute-Loire"},
        {"numero": "44", "nom": u"Loire-Atlantique"},
        {"numero": "45", "nom": u"Loiret"},
        {"numero": "46", "nom": u"Lot"},
        {"numero": "47", "nom": u"Lot-et-Garonne"},
        {"numero": "48", "nom": u"Lozère"},
        {"numero": "49", "nom": u"Maine-et-Loire"},
        {"numero": "50", "nom": u"Manche"},
        {"numero": "51", "nom": u"Marne"},
        {"numero": "52", "nom": u"Haute-Marne"},
        {"numero": "53", "nom": u"Mayenne"},
        {"numero": "54", "nom": u"Meurthe-et-Moselle"},
        {"numero": "55", "nom": u"Meuse"},
        {"numero": "56", "nom": u"Morbihan"},
        {"numero": "57", "nom": u"Moselle"},
        {"numero": "58", "nom": u"Nièvre"},
        {"numero": "59", "nom": u"Nord"},
        {"numero": "60", "nom": u"Oise"},
        {"numero": "61", "nom": u"Orne"},
        {"numero": "62", "nom": u"Pas-de-Calais"},
        {"numero": "63", "nom": u"Puy-de-Dôme"},
        {"numero": "64", "nom": u"Pyrénées-Atlantiques"},
        {"numero": "65", "nom": u"Hautes-Pyrénées"},
        {"numero": "66", "nom": u"Pyrénées-Orientales"},
        {"numero": "67", "nom": u"Bas-Rhin"},
        {"numero": "68", "nom": u"Haut-Rhin"},
        {"numero": "69", "nom": u"Rhône"},
        {"numero": "70", "nom": u"Haute-Saône"},
        {"numero": "71", "nom": u"Saône-et-Loire"},
        {"numero": "72", "nom": u"Sarthe"},
        {"numero": "73", "nom": u"Savoie"},
        {"numero": "74", "nom": u"Haute-Savoie"},
        {"numero": "75", "nom": u"Paris"},
        {"numero": "76", "nom": u"Seine-Maritime"},
        {"numero": "77", "nom": u"Seine-et-Marne"},
        {"numero": "78", "nom": u"Yvelines"},
        {"numero": "79", "nom": u"Deux-Sèvres"},
        {"numero": "80", "nom": u"Somme"},
        {"numero": "81", "nom": u"Tarn"},
        {"numero": "82", "nom": u"Tarn-et-Garonne"},
        {"numero": "83", "nom": u"Var"},
        {"numero": "84", "nom": u"Vaucluse"},
        {"numero": "85", "nom": u"Vendée"},
        {"numero": "86", "nom": u"Vienne"},
        {"numero": "87", "nom": u"Haute-Vienne"},
        {"numero": "88", "nom": u"Vosges"},
        {"numero": "89", "nom": u"Yonne"},
        {"numero": "90", "nom": u"Territoire de Belfort"},
        {"numero": "91", "nom": u"Essonne"},
        {"numero": "92", "nom": u"Hauts-de-Seine"},
        {"numero": "93", "nom": u"Seine-Saint-Denis"},
        {"numero": "94", "nom": u"Val-de-Marne"},
        {"numero": "95", "nom": u"Val-d'Oise"},
        {"numero": "971", "nom": u"Guadeloupe"},
        {"numero": "972", "nom": u"Martinique"},
        {"numero": "973", "nom": u"Guyane"},
        {"numero": "974", "nom": u"La Réunion"},
        {"numero": "976", "nom": u"Mayotte"},
    ])


def downgrade():
    pass
