# -*- coding: utf-8 -*-
from flask import Blueprint, render_template
from flask.ext.security import current_user

mod = Blueprint('documentation_moteur', __name__)

@mod.route('/documentation/moteur')
def doc_moteur():
    return render_template('documentation/moteur.html',
                 apikey='token' if current_user.is_anonymous else current_user.apikey)
