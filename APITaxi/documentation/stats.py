# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from collections import defaultdict
from dateutil.relativedelta import relativedelta
from sqlalchemy import func
from flask import Blueprint, render_template
from flask.ext.security import current_user
from flask.ext.restful import request
from ..extensions import user_datastore
from ..extensions import db
from ..models.taxis import Taxi, ADS
from ..models.hail import Hail
from ..models.administrative import ZUPC
from ..models.security import User

mod = Blueprint('stats', __name__)

@mod.route('/stats')
def stats_index():

    dep = request.args.get('dep', 0, type=int)

    return render_template('stats.html',
                           dep=dep,
                           nb_taxis=stats_taxis(dep),
                           taxis=list_active_taxis(dep),
                           nb_hails=stats_hails(dep),
                           hails=list_hails(dep)
                          )

def stats_taxis(dep):

    depattern = '{0:02d}%'.format(dep) if dep else '%'
    last_day = datetime.now() + timedelta(days=-1)
    last_6months = datetime.now() + relativedelta(months=-6)


    nb_taxis = []
    nb_active_taxis = []
    tab_nb_taxis = defaultdict(dict)

    if current_user.has_role('admin'):
        nb_taxis = db.session.query(Taxi.added_by,
                                    func.count(Taxi.id).label('ntaxis'),
                                    func.count('0').label('nactivetaxis')) \
                   .join(Taxi.ads) \
                   .filter(ADS.insee.like(depattern)) \
                   .filter(Taxi.last_update_at >= last_6months) \
                   .group_by(Taxi.added_by)

        nb_active_taxis = db.session.query(Taxi.added_by,
                                           func.count('0').label('ntaxis'),
                                           func.count(Taxi.id).label('nactivetaxis')) \
                          .join(Taxi.ads) \
                          .filter(ADS.insee.like(depattern)) \
                          .filter(Taxi.last_update_at >= last_day) \
                          .group_by(Taxi.added_by)
        for ta in nb_taxis:
            tab_nb_taxis[user_datastore.get_user(ta.added_by).commercial_name]['ntaxis'] = ta.ntaxis
        for ta in nb_active_taxis:
            tab_nb_taxis[user_datastore.get_user(ta.added_by).commercial_name]['nactivetaxis'] = ta.nactivetaxis

    elif current_user.has_role('operateur'):
        nb_taxis = db.session.query(Taxi.added_by,
                                    func.count(Taxi.id).label('ntaxis'),
                                    func.count('0').label('nactivetaxis')) \
                   .join(Taxi.ads) \
                   .filter(ADS.insee.like(depattern)) \
                   .filter(Taxi.last_update_at >= last_6months) \
                   .filter(Taxi.added_by == current_user.id) \
                   .group_by(Taxi.added_by)

        nb_active_taxis = db.session.query(Taxi.added_by,
                                           func.count('0').label('ntaxis'),
                                           func.count(Taxi.id).label('nactivetaxis')) \
                          .join(Taxi.ads) \
                          .filter(ADS.insee.like(depattern)) \
                          .filter(Taxi.last_update_at >= last_day) \
                          .filter(Taxi.added_by == current_user.id) \
                          .group_by(Taxi.added_by)
        for ta in nb_taxis:
            tab_nb_taxis[user_datastore.get_user(ta.added_by).commercial_name]['ntaxis'] = ta.ntaxis
        for ta in nb_active_taxis:
            tab_nb_taxis[user_datastore.get_user(ta.added_by).commercial_name]['nactivetaxis'] = ta.nactivetaxis

    if not tab_nb_taxis:
        nb_taxis = db.session.query(
                                    func.count(Taxi.id).label('ntaxis'),
                                    func.count('0').label('nactivetaxis')) \
                   .join(Taxi.ads) \
                   .filter(ADS.insee.like(depattern)) \
                   .filter(Taxi.last_update_at >= last_6months)

        nb_active_taxis = db.session.query(
                                           func.count('0').label('ntaxis'),
                                           func.count(Taxi.id).label('nactivetaxis')) \
                          .join(Taxi.ads) \
                          .filter(ADS.insee.like(depattern)) \
                          .filter(Taxi.last_update_at >= last_day)

        for ta in nb_taxis:
            tab_nb_taxis['Total']['ntaxis'] = ta.ntaxis
        for ta in nb_active_taxis:
            tab_nb_taxis['Total']['nactivetaxis'] = ta.nactivetaxis

    return tab_nb_taxis


def list_active_taxis(dep):

    depattern = '{0:02d}%'.format(dep) if dep else '%'
    last_day = datetime.now() + timedelta(days=-1)

    taxis = []

    if current_user.has_role('admin'):
        taxis = Taxi.query.join(User).join(Taxi.ads) \
                .filter(ADS.insee.like(depattern)) \
                .filter(Taxi.last_update_at >= last_day) \
                .order_by(Taxi.added_by) \
                .limit(20) \
                .all()

    elif current_user.has_role('operateur'):
        taxis = Taxi.query.join(Taxi.ads) \
                .filter(ADS.insee.like(depattern)) \
                .filter(Taxi.last_update_at >= last_day) \
                .filter(Taxi.added_by == current_user.id) \
                .limit(20) \
                .all()
    else:
         taxis = []

    tab_taxis = defaultdict(dict)
    for taxi in taxis:
        tab_taxis[taxi.id]['added_by'] = user_datastore.get_user(taxi.added_by).commercial_name
        tab_taxis[taxi.id]['ads.insee'] = taxi.ads.insee
        zupc = None
        zupc = ZUPC.query.filter_by(insee=taxi.ads.insee).order_by(ZUPC.id.desc()).first()
        if zupc:
            tab_taxis[taxi.id]['zupc.nom'] = zupc.nom
        else:
            tab_taxis[taxi.id]['zupc.nom'] = ''
        tab_taxis[taxi.id]['ads.numero'] = taxi.ads.numero
        tab_taxis[taxi.id]['driver.professional_licence'] = taxi.driver.professional_licence
        tab_taxis[taxi.id]['last_update_at'] = taxi.last_update_at

    return tab_taxis


def stats_hails(dep):

    depattern = '{0:02d}%'.format(dep) if dep else '%'

    last_day = datetime.now() + timedelta(days=-1)
    last_year = datetime.now() + relativedelta(months=-12)

    nb_hails_d = []
    nb_hails_ok_d = []
    nb_hails_y = []
    nb_hails_ok_y = []
    tab_nb_hails = defaultdict(dict)

    if current_user.has_role('admin'):

        nb_hails_d = db.session.query(Hail.operateur_id,
                                      func.count(Hail.id).label('nhails')) \
                     .join(Hail.taxi_relation) \
                     .join(Taxi.ads) \
                     .filter(ADS.insee.like(depattern)) \
                     .filter(Hail.creation_datetime >= last_day) \
                     .group_by(Hail.operateur_id)

        nb_hails_ok_d = db.session.query(Hail.operateur_id,
                                         func.count(Hail.id).label('nhails')) \
                        .join(Hail.taxi_relation) \
                        .join(Taxi.ads) \
                        .filter(ADS.insee.like(depattern)) \
                        .filter(Hail.creation_datetime >= last_day) \
                        .filter(Hail._status == 'accepted_by_customer') \
                        .group_by(Hail.operateur_id)

        nb_hails_y = db.session.query(Hail.operateur_id,
                                      func.count(Hail.id).label('nhails')) \
                     .join(Hail.taxi_relation) \
                     .join(Taxi.ads) \
                     .filter(ADS.insee.like(depattern)) \
                     .filter(Hail.creation_datetime >= last_year) \
                     .group_by(Hail.operateur_id)

        nb_hails_ok_y = db.session.query(Hail.operateur_id,
                                         func.count(Hail.id).label('nhails')) \
                        .join(Hail.taxi_relation) \
                        .join(Taxi.ads) \
                        .filter(ADS.insee.like(depattern)) \
                        .filter(Hail.creation_datetime >= last_year) \
                        .filter(Hail._status == 'accepted_by_customer') \
                        .group_by(Hail.operateur_id)

        for ha in nb_hails_d:
             tab_nb_hails[user_datastore.get_user(ha.operateur_id).commercial_name]['nhails_d'] = ha.nhails
        for ha in nb_hails_ok_d:
             tab_nb_hails[user_datastore.get_user(ha.operateur_id).commercial_name]['nhails_ok_d'] = ha.nhails
        for ha in nb_hails_y:
             tab_nb_hails[user_datastore.get_user(ha.operateur_id).commercial_name]['nhails_y'] = ha.nhails
        for ha in nb_hails_ok_y:
            tab_nb_hails[user_datastore.get_user(ha.operateur_id).commercial_name]['nhails_ok_y'] = ha.nhails

    elif current_user.has_role('operateur'):

        nb_hails_d = db.session.query(Hail.added_by,
                                      func.count(Hail.id).label('nhails')) \
                     .join(Hail.taxi_relation) \
                     .join(Taxi.ads) \
                     .filter(ADS.insee.like(depattern)) \
                     .filter(Hail.creation_datetime >= last_day) \
                     .filter(Hail.operateur_id == current_user.id) \
                     .group_by(Hail.added_by)

        nb_hails_ok_d = db.session.query(Hail.added_by,
                                         func.count(Hail.id).label('nhails')) \
                        .join(Hail.taxi_relation) \
                        .join(Taxi.ads) \
                        .filter(ADS.insee.like(depattern)) \
                        .filter(Hail.creation_datetime >= last_day) \
                        .filter(Hail._status == 'accepted_by_customer') \
                        .filter(Hail.operateur_id == current_user.id) \
                        .group_by(Hail.added_by)

        nb_hails_y = db.session.query(Hail.added_by,
                                      func.count(Hail.id).label('nhails')) \
                     .join(Hail.taxi_relation) \
                     .join(Taxi.ads) \
                     .filter(ADS.insee.like(depattern)) \
                     .filter(Hail.creation_datetime >= last_year) \
                     .filter(Hail.operateur_id == current_user.id) \
                     .group_by(Hail.added_by)

        nb_hails_ok_y = db.session.query(Hail.added_by,
                                         func.count(Hail.id).label('nhails')) \
                        .join(Hail.taxi_relation) \
                        .join(Taxi.ads) \
                        .filter(ADS.insee.like(depattern)) \
                        .filter(Hail.creation_datetime >= last_year) \
                        .filter(Hail._status == 'accepted_by_customer') \
                        .filter(Hail.operateur_id == current_user.id) \
                        .group_by(Hail.added_by)

        for ha in nb_hails_d:
             tab_nb_hails[user_datastore.get_user(ha.added_by).email]['nhails_d'] = ha.nhails
        for ha in nb_hails_ok_d:
             tab_nb_hails[user_datastore.get_user(ha.added_by).email]['nhails_ok_d'] = ha.nhails
        for ha in nb_hails_y:
             tab_nb_hails[user_datastore.get_user(ha.added_by).email]['nhails_y'] = ha.nhails
        for ha in nb_hails_ok_y:
             tab_nb_hails[user_datastore.get_user(ha.added_by).email]['nhails_ok_y'] = ha.nhails


    elif current_user.has_role('moteur'):

        nb_hails_d = db.session.query(Hail.operateur_id,
                                      func.count(Hail.id).label('nhails')) \
                     .join(Hail.taxi_relation) \
                     .join(Taxi.ads) \
                     .filter(ADS.insee.like(depattern)) \
                     .filter(Hail.creation_datetime >= last_day) \
                     .filter(Hail.added_by == current_user.id) \
                     .group_by(Hail.operateur_id)

        nb_hails_ok_d = db.session.query(Hail.operateur_id,
                                         func.count(Hail.id).label('nhails')) \
                        .join(Hail.taxi_relation) \
                        .join(Taxi.ads) \
                        .filter(ADS.insee.like(depattern)) \
                        .filter(Hail.creation_datetime >= last_day) \
                        .filter(Hail._status == 'accepted_by_customer') \
                        .filter(Hail.added_by == current_user.id) \
                        .group_by(Hail.operateur_id)

        nb_hails_y = db.session.query(Hail.operateur_id,
                                      func.count(Hail.id).label('nhails')) \
                     .join(Hail.taxi_relation) \
                     .join(Taxi.ads) \
                     .filter(ADS.insee.like(depattern)) \
                     .filter(Hail.creation_datetime >= last_year) \
                     .filter(Hail.added_by == current_user.id) \
                     .group_by(Hail.operateur_id)

        nb_hails_ok_y = db.session.query(Hail.operateur_id,
                                         func.count(Hail.id).label('nhails')) \
                        .join(Hail.taxi_relation) \
                        .join(Taxi.ads) \
                        .filter(ADS.insee.like(depattern)) \
                        .filter(Hail.creation_datetime >= last_year) \
                        .filter(Hail._status == 'accepted_by_customer') \
                        .filter(Hail.added_by == current_user.id) \
                        .group_by(Hail.operateur_id)

        for ha in nb_hails_d:
             tab_nb_hails[user_datastore.get_user(ha.operateur_id).commercial_name]['nhails_d'] = ha.nhails
        for ha in nb_hails_ok_d:
             tab_nb_hails[user_datastore.get_user(ha.operateur_id).commercial_name]['nhails_ok_d'] = ha.nhails
        for ha in nb_hails_y:
             tab_nb_hails[user_datastore.get_user(ha.operateur_id).commercial_name]['nhails_y'] = ha.nhails
        for ha in nb_hails_ok_y:
             tab_nb_hails[user_datastore.get_user(ha.operateur_id).commercial_name]['nhails_ok_y'] = ha.nhails


    if not tab_nb_hails:

        nb_hails_d = db.session.query(
                                      func.count(Hail.id).label('nhails')) \
                     .join(Hail.taxi_relation) \
                     .join(Taxi.ads) \
                     .filter(ADS.insee.like(depattern)) \
                     .filter(Hail.creation_datetime >= last_day)

        nb_hails_ok_d = db.session.query(
                                         func.count(Hail.id).label('nhails')) \
                        .join(Hail.taxi_relation) \
                        .join(Taxi.ads) \
                        .filter(ADS.insee.like(depattern)) \
                        .filter(Hail.creation_datetime >= last_day) \
                        .filter(Hail._status == 'accepted_by_customer')

        nb_hails_y = db.session.query(
                                      func.count(Hail.id).label('nhails')) \
                     .join(Hail.taxi_relation) \
                     .join(Taxi.ads) \
                     .filter(ADS.insee.like(depattern)) \
                     .filter(Hail.creation_datetime >= last_year)

        nb_hails_ok_y = db.session.query(
                                         func.count(Hail.id).label('nhails')) \
                        .join(Hail.taxi_relation) \
                        .join(Taxi.ads) \
                        .filter(ADS.insee.like(depattern)) \
                        .filter(Hail.creation_datetime >= last_year) \
                        .filter(Hail._status == 'accepted_by_customer')

        for ha in nb_hails_d:
            tab_nb_hails['Total']['nhails_d'] = ha.nhails
        for ha in nb_hails_ok_d:
            tab_nb_hails['Total']['nhails_ok_d'] = ha.nhails
        for ha in nb_hails_y:
            tab_nb_hails['Total']['nhails_y'] = ha.nhails
        for ha in nb_hails_ok_y:
            tab_nb_hails['Total']['nhails_ok_y'] = ha.nhails

    return tab_nb_hails


def list_hails(dep):

    depattern = '{0:02d}%'.format(dep) if dep else '%'
    hails = []

    last_year = datetime.now() + relativedelta(months=-12)


    if current_user.has_role('admin'):
        hails = db.session.query(Hail.operateur_id, Hail.added_by,
                                 Hail.creation_datetime, Hail.id,
                                 ADS.insee, ADS.numero, Hail._status) \
                     .join(Hail.taxi_relation) \
                     .join(Taxi.ads) \
                     .filter(ADS.insee.like(depattern)) \
                     .filter(Hail.creation_datetime >= last_year) \
                     .limit(100) \
                     .all()

    elif current_user.has_role('operateur'):
        hails = db.session.query(Hail.operateur_id, Hail.added_by,
                                 Hail.creation_datetime, Hail.id,
                                 ADS.insee, ADS.numero, Hail._status) \
                      .join(Hail.taxi_relation) \
                      .join(Taxi.ads) \
                      .filter(ADS.insee.like(depattern)) \
                      .filter(Hail.creation_datetime >= last_year) \
                      .filter(Hail.operateur_id == current_user.id) \
                      .limit(100) \
                      .all()

    elif current_user.has_role('moteur'):
        hails = db.session.query(Hail.operateur_id, Hail.added_by,
                                 Hail.creation_datetime, Hail.id,
                                 ADS.insee, ADS.numero, Hail._status) \
                      .join(Hail.taxi_relation) \
                      .join(Taxi.ads) \
                      .filter(ADS.insee.like(depattern)) \
                      .filter(Hail.creation_datetime >= last_year) \
                      .filter(Hail.added_by == current_user.id) \
                      .limit(100) \
                      .all()
    else:
        hails = []

    tab_hails = defaultdict(dict)
    for hail in hails:
        tab_hails[hail.id]['creation_datetime'] = hail.creation_datetime
        # tab_hails[hail.id]['added_by'] = user_datastore.get_user(hail.added_by).commercial_name
        tab_hails[hail.id]['added_by'] = user_datastore.get_user(hail.added_by).email
        tab_hails[hail.id]['operator'] = user_datastore.get_user(hail.operateur_id).commercial_name
        tab_hails[hail.id]['ads.insee'] = hail.insee
        zupc = None
        zupc = ZUPC.query.filter_by(insee=hail.insee).order_by(ZUPC.id.desc()).first()
        if zupc:
            tab_hails[hail.id]['zupc.nom'] = zupc.nom
        else:
            tab_hails[hail.id]['zupc.nom'] = ''
        tab_hails[hail.id]['ads.numero'] = hail.numero
        tab_hails[hail.id]['last_status'] = hail._status

    return tab_hails

