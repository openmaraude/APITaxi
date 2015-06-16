# -*- coding: utf-8 -*-
from flask import Blueprint, render_template
from flask.ext.security import current_user

mod = Blueprint('documentation_operateur', __name__)

@mod.route('/documentation/operateur')
def doc_index():
    return render_template('documentation/operateur.html',
                 apikey=current_user.apikey  if current_user else 'token')
