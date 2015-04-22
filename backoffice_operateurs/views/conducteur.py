# -*- coding: utf8 -*-
from .. import db, api, ns_administrative
from ..forms.taxis import ConducteurCreateForm,\
        ConducteurUpdateForm
from ..models import taxis as taxis_models, administrative as administrative_models
from ..utils import create_obj_from_json
from flask import Blueprint, render_template, request, redirect, url_for, abort
from flask import render_template, request, redirect, url_for, jsonify,\
        current_app
from flask.ext.security import login_required, current_user
from datetime import datetime
from flask_restful import Resource, abort
from flask.ext.restplus import fields


mod = Blueprint('conducteur', __name__)

conducteur_details = api.model('conducteur_details', taxis_models.Conducteur.marshall_obj())
conducteur_model = api.model('conducteur', {"conducteur": fields.Nested(conducteur_details)})

conducteur_details_expect = api.model('conducteur_details_expect',
                                      taxis_models.Conducteur.marshall_obj(filter_id=True))
conducteur_model_expect = api.model('conducteur_model_expect',
                                    {"conducteur": fields.Nested(conducteur_details_expect)})

@ns_administrative.route('conducteurs/')
class Conducteur(Resource):

    @api.marshal_with(conducteur_model)
    @api.expect(conducteur_model_expect)
    @login_required
    def post(self):
        json = request.get_json()
        if "conducteur" not in json:
            current_app.logger.error("No conducteur in json")
            abort(400)
        if not administrative_models.Departement.query.get(json['conducteur']['departement_id']):
            abort(400, message='Unable to find the *departement*')
        new_conducteur = None
        try:
            new_conducteur = create_obj_from_json(taxis_models.Conducteur,
                json['conducteur'])
        except KeyError as e:
            current_app.logger.error("Key error in conducteur", e)
            abort(400)
        db.session.add(new_conducteur)
        db.session.commit()
        return jsonify(new_conducteur.as_dict())

    @api.hide
    @login_required
    def get(self):
        if not taxis_models.Conducteur.can_be_listed_by(current_user):
            abort(403)
        page = int(request.args.get('page')) if 'page' in request.args else 1
        return render_template('lists/conducteurs.html',
            conducteur_list=taxis_models.Conducteur.query.paginate(page))


@mod.route('/conducteur/form', methods=['GET', 'POST'])
@login_required
def conducteur_form():
    form = None
    if request.args.get("id"):
        conducteur = taxis_models.Conducteur.query.get(request.args.get("id"))
        if not conducteur:
            abort(404)
        if not conducteur.can_be_edited_by(current_user):
            abort(403)
        form = ConducteurUpdateForm(obj=conducteur)
    else:
        form = ConducteurCreateForm()
    if request.method == "POST":
        if request.args.get("id"):
            conducteur.last_update_at = datetime.now().isoformat()
            form.populate_obj(conducteur)
            if form.validate():
                db.session.commit()
                return redirect(url_for('conducteur.conducteurs'))
        else:
            conducteur = taxis_models.Conducteur()
            form.populate_obj(conducteur)
            db.session.add(conducteur)
            db.session.commit()
            return redirect(url_for('conducteur.conducteurs'))
    return render_template('forms/conducteur.html', form=form,
        form_method="POST", submit_value="Modifier")


@mod.route('/conducteur/delete')
@login_required
def conducteur_delete():
    if not request.args.get("id"):
        abort(404)
    conducteur = taxis_models.Conducteur.query.get(request.args.get("id"))
    if not conducteur:
        abort(404)
    if not conducteur.can_be_deleted_by(current_user):
        abort(403)
    db.session.delete(conducteur)
    db.session.commit()
    return redirect(url_for("conducteur.conducteurs"))
