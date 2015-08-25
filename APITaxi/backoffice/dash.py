#coding: utf-8
from flask import Blueprint, render_template
from flask.ext.login import login_required, current_user
from APITaxi.models.administrative import ZUPC
from APITaxi.models.taxis import ADS
from APITaxi.extensions import db

mod = Blueprint('dash_bo', __name__)

@mod.route('/dash')
@login_required
def dashboard():
    zupc_parent_id = set()
    zupc_parent = []
    query = db.session.query(ADS.zupc_id)
    if not current_user.has_role('admin'):
        query.filter_by(added_by = current_user.id)
    for zupc_tuple in query.distinct():
        if not zupc_tuple.zupc_id or zupc_tuple.zupc_id in zupc_parent_id:
            continue
        zupc = ZUPC.get(zupc_tuple.zupc_id)
        if not zupc or zupc.parent.id in zupc_parent_id:
            continue
        zupc_parent.append({"insee": zupc.parent.insee, "name": zupc.parent.nom})
        zupc_parent_id.add(zupc.parent.id)

    return render_template('dash.html', apikey=current_user.apikey, zupc_list=zupc_parent)
