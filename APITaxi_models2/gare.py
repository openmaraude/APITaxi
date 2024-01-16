"""
https://ressources.data.sncf.com/explore/dataset/referentiel-gares-voyageurs/
"""
from geoalchemy2 import Geography

from . import db


class GareVoyageur(db.Model):
    def __repr__(self):
        return f'<Gare {self.code} ({self.gare_alias_libelle_noncontraint})>'

    code = db.Column(db.String, primary_key=True, doc="Code plate-forme")
    code_gare = db.Column(db.String, doc="Code gare")  # Pas unique
    uic_code = db.Column(db.String, doc="Code UIC")
    dtfinval = db.Column(db.Date, doc="Date fin validité plateforme")
    alias_libelle_noncontraint = db.Column(db.String, doc="Intitulé plateforme")
    adresse_cp = db.Column(db.String, doc="Code postal")
    commune_code = db.Column(db.String, doc="Code Commune")
    commune_libellemin = db.Column(db.String, doc="Commune")
    departement_numero = db.Column(db.String, doc="Code département")
    departement_libellemin = db.Column(db.String, doc="Département")
    longitude_entreeprincipale_wgs84 = db.Column(db.String, doc="Longitude")
    latitude_entreeprincipale_wgs84 = db.Column(db.String, doc="Latitude")
    segmentdrg_libelle = db.Column(db.String, doc="Segment DRG")
    niveauservice_libelle = db.Column(db.String, doc="Niveau de service")
    rg_libelle = db.Column(db.String, doc="RG")
    gare_alias_libelle_noncontraint = db.Column(db.String, doc="Intitulé gare")
    gare_alias_libelle_fronton = db.Column(db.String, doc="Intitulé fronton de gare")
    gare_agencegc_libelle = db.Column(db.String, doc="Direction Territoriale Gare")
    gare_regionsncf_libelle = db.Column(db.String, doc="Région SNCF")
    gare_ug_libelle = db.Column(db.String, doc="Unité gare")
    gare_ut_libelle = db.Column(db.String, doc="UT")
    gare_nbpltf = db.Column(db.Integer, doc="Nbre plateformes")
    tvs = db.Column(db.String, doc="TVS")
    wgs_84 = db.Column(Geography(geometry_type='POINT', srid=4326))
    # Ajouté au schéma
    tgv = db.Column(db.Boolean, nullable=True)
