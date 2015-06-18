# -*- coding: utf-8 -*-
from flask import Blueprint, render_template
from flask.ext.security import current_user

mod = Blueprint('documentation', __name__)

@mod.route('/documentation')
@mod.route('/documentation/index')
def doc_index():
    return render_template('documentation/index.html',
                 apikey='token' if current_user.is_anonymous else current_user.apikey)
