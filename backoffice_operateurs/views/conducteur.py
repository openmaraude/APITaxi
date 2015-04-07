# -*- coding: utf8 -*-
from backoffice_operateurs import db
from backoffice_operateurs.forms.taxis import ConducteurCreateForm,\
        ConducteurUpdateForm
from backoffice_operateurs.models import taxis as taxis_models
from flask import Blueprint, render_template, request, redirect, url_for, abort
from flask import render_template, request, redirect, url_for, abort, jsonify,\
        current_app
from flask.ext.security import login_required
from backoffice_operateurs.utils import create_obj_from_json

mod = Blueprint('conducteur', __name__)

def conducteur_api_add():
    json = request.get_json()
    if "conducteur" not in json:
        current_app.logger.error("No conducteur in json")
        abort(400)
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


def conducteurs_list():
    page = int(request.args.get('page')) if 'page' in request.args else 1
    return render_template('lists/conducteurs.html',
        conducteur_list=taxis_models.Conducteur.query.paginate(page))


@mod.route('/conducteurs', methods=['GET', 'POST'])
@mod.route('/conducteurs/', methods=['GET', 'POST'])
@login_required
def conducteurs():
    if request.method == 'GET':
        return conducteurs_list()
    elif request.method == 'POST':
        return conducteur_api_add()
    abort(405)

@mod.route('/conducteur/form', methods=['GET', 'POST'])
@login_required
def conducteur_form():
    form = None
    if request.args.get("id"):
        conducteur = taxis_models.Conducteur.query.get(request.args.get("id"))
        if not conducteur:
            abort(404)
        form = ConducteurUpdateForm(obj=conducteur)
    else:
        form = ConducteurCreateForm()
    if request.method == "POST":
        if request.args.get("id"):
            conducteur.last_update_at = datetime.now().isoformat()
            form.populate_obj(conducteur)
            if form.validate():
                db.session.commit()
                return redirect(url_for('conducteurs'))
        else:
            conducteur = taxis_models.Conducteur()
            form.populate_obj(conducteur)
            db.session.add(conducteur)
            db.session.commit()
            return redirect(url_for('conducteurs'))
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
    db.session.delete(conducteur)
    db.session.commit()
    return redirect(url_for("conducteurs"))
