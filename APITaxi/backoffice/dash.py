#coding: utf-8
from flask import Blueprint, render_template
from flask.ext.login import login_required, current_user

mod = Blueprint('dash_bo', __name__)

@mod.route('/dash')
@login_required
def dashboard():
    return render_template('dash.html', apikey=current_user.apikey)
