# -*- coding: utf-8 -*-
from flask import Blueprint, render_template, url_for as base_url_for
from flask.ext.security import current_user
from ..extensions import user_datastore
from ..models.taxis import Taxi
from functools import partial

mod = Blueprint('examples', __name__)


@mod.route('/documentation/examples')
def doc_index():
    if not current_user.is_anonymous:
        apikeys_operator = set()
        apikeys_moteur = set()
        if 'operateur' in current_user.roles:
            apikeys_operator.add(('your token', current_user.apikey))
        if 'moteur' in current_user.roles:
            apikeys_moteur.add(('your token', current_user.apikey))
        apikeys_operator.add(('neotaxi', user_datastore.find_user(email='neotaxi').apikey))
        apikeys_moteur.add(('neomap', user_datastore.find_user(email='neomap').apikey))
        taxis = Taxi.query.filter(Taxi.added_by==user_datastore.\
                    find_user(email='neotaxi').id).all()
    else:
        apikeys_operator = [('anonymous', 'token')]
        apikeys_moteur = [('anonymous', 'token')]
        taxis = []

    url_for = partial(base_url_for, _external=True)
    return render_template('documentation/examples.html',
                 apikeys_operator=apikeys_operator,
                 apikeys_moteur=apikeys_moteur,
                 taxis=taxis,
                 url_for=url_for)
