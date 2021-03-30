# -*- coding: utf-8 -*-
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
        {"numero": "01", "nom": "Ain"},
        {"numero": "02", "nom": "Aisne"},
        {"numero": "03", "nom": "Allier"},
        {"numero": "04", "nom": "Alpes-de-Haute-Provence"},
        {"numero": "05", "nom": "Hautes-Alpes"},
        {"numero": "06", "nom": "Alpes-Maritimes"},
        {"numero": "07", "nom": "Ardèche"},
        {"numero": "08", "nom": "Ardennes"},
        {"numero": "09", "nom": "Ariège"},
        {"numero": "10", "nom": "Aube"},
        {"numero": "11", "nom": "Aude"},
        {"numero": "12", "nom": "Aveyron"},
        {"numero": "13", "nom": "Bouches-du-Rhône"},
        {"numero": "14", "nom": "Calvados"},
        {"numero": "15", "nom": "Cantal"},
        {"numero": "16", "nom": "Charente"},
        {"numero": "17", "nom": "Charente-Maritime"},
        {"numero": "18", "nom": "Cher"},
        {"numero": "19", "nom": "Corrèze"},
        {"numero": "2A", "nom": "Corse-du-Sud"},
        {"numero": "2B", "nom": "Haute-Corse"},
        {"numero": "21", "nom": "Côte-d'Or"},
        {"numero": "22", "nom": "Côtes-d'Armor"},
        {"numero": "23", "nom": "Creuse"},
        {"numero": "24", "nom": "Dordogne"},
        {"numero": "25", "nom": "Doubs"},
        {"numero": "26", "nom": "Drôme"},
        {"numero": "27", "nom": "Eure"},
        {"numero": "28", "nom": "Eure-et-Loir"},
        {"numero": "29", "nom": "Finistère"},
        {"numero": "30", "nom": "Gard"},
        {"numero": "31", "nom": "Haute-Garonne"},
        {"numero": "32", "nom": "Gers"},
        {"numero": "33", "nom": "Gironde"},
        {"numero": "34", "nom": "Hérault"},
        {"numero": "35", "nom": "Ille-et-Vilaine"},
        {"numero": "36", "nom": "Indre"},
        {"numero": "37", "nom": "Indre-et-Loire"},
        {"numero": "38", "nom": "Isère"},
        {"numero": "39", "nom": "Jura"},
        {"numero": "40", "nom": "Landes"},
        {"numero": "41", "nom": "Loir-et-Cher"},
        {"numero": "42", "nom": "Loire"},
        {"numero": "43", "nom": "Haute-Loire"},
        {"numero": "44", "nom": "Loire-Atlantique"},
        {"numero": "45", "nom": "Loiret"},
        {"numero": "46", "nom": "Lot"},
        {"numero": "47", "nom": "Lot-et-Garonne"},
        {"numero": "48", "nom": "Lozère"},
        {"numero": "49", "nom": "Maine-et-Loire"},
        {"numero": "50", "nom": "Manche"},
        {"numero": "51", "nom": "Marne"},
        {"numero": "52", "nom": "Haute-Marne"},
        {"numero": "53", "nom": "Mayenne"},
        {"numero": "54", "nom": "Meurthe-et-Moselle"},
        {"numero": "55", "nom": "Meuse"},
        {"numero": "56", "nom": "Morbihan"},
        {"numero": "57", "nom": "Moselle"},
        {"numero": "58", "nom": "Nièvre"},
        {"numero": "59", "nom": "Nord"},
        {"numero": "60", "nom": "Oise"},
        {"numero": "61", "nom": "Orne"},
        {"numero": "62", "nom": "Pas-de-Calais"},
        {"numero": "63", "nom": "Puy-de-Dôme"},
        {"numero": "64", "nom": "Pyrénées-Atlantiques"},
        {"numero": "65", "nom": "Hautes-Pyrénées"},
        {"numero": "66", "nom": "Pyrénées-Orientales"},
        {"numero": "67", "nom": "Bas-Rhin"},
        {"numero": "68", "nom": "Haut-Rhin"},
        {"numero": "69", "nom": "Rhône"},
        {"numero": "70", "nom": "Haute-Saône"},
        {"numero": "71", "nom": "Saône-et-Loire"},
        {"numero": "72", "nom": "Sarthe"},
        {"numero": "73", "nom": "Savoie"},
        {"numero": "74", "nom": "Haute-Savoie"},
        {"numero": "75", "nom": "Paris"},
        {"numero": "76", "nom": "Seine-Maritime"},
        {"numero": "77", "nom": "Seine-et-Marne"},
        {"numero": "78", "nom": "Yvelines"},
        {"numero": "79", "nom": "Deux-Sèvres"},
        {"numero": "80", "nom": "Somme"},
        {"numero": "81", "nom": "Tarn"},
        {"numero": "82", "nom": "Tarn-et-Garonne"},
        {"numero": "83", "nom": "Var"},
        {"numero": "84", "nom": "Vaucluse"},
        {"numero": "85", "nom": "Vendée"},
        {"numero": "86", "nom": "Vienne"},
        {"numero": "87", "nom": "Haute-Vienne"},
        {"numero": "88", "nom": "Vosges"},
        {"numero": "89", "nom": "Yonne"},
        {"numero": "90", "nom": "Territoire de Belfort"},
        {"numero": "91", "nom": "Essonne"},
        {"numero": "92", "nom": "Hauts-de-Seine"},
        {"numero": "93", "nom": "Seine-Saint-Denis"},
        {"numero": "94", "nom": "Val-de-Marne"},
        {"numero": "95", "nom": "Val-d'Oise"},
        {"numero": "971", "nom": "Guadeloupe"},
        {"numero": "972", "nom": "Martinique"},
        {"numero": "973", "nom": "Guyane"},
        {"numero": "974", "nom": "La Réunion"},
        {"numero": "976", "nom": "Mayotte"},
    ])


def downgrade():
    pass
