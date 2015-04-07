# -*- coding: utf8 -*-
from backoffice_operateurs import db
from backoffice_operateurs.models import administrative as administrative_models
from backoffice_operateurs.forms import administrative as administrative_forms
from flask.ext.security import login_required
from flask import Blueprint, request, render_template, redirect, jsonify, url_for

mod = Blueprint('zupc', __name__)

@mod.route('/zupc')
@mod.route('/zupc/')
@login_required
def zupc_list():
    page = int(request.args.get('page')) if 'page' in request.args else 1
    return render_template('lists/zupc.html',
        zupc_list=administrative_models.ZUPC.query.paginate(page))


@mod.route('/zupc/create', methods=['GET', 'POST'])
@login_required
def zupc_create():
    form = administrative_forms.ZUPCreateForm()
    if request.method == "POST" and form.validate():
        zupc = administrative_models.ZUPC()
        form.populate_obj(zupc)
        db.session.add(zupc)
        db.session.commit()
        return redirect(url_for('zupc_list'))
    return render_template('forms/zupc.html', form=form, form_method="POST")

@mod.route('/zupc/update', methods=['GET', 'POST'])
@login_required
def zupc_update():
    if not request.args.get("id"):
        abort(404)
    zupc = administrative_models.ZUPC.query.get(request.args.get("id"))
    if not zupc:
        abort(404)
    form = administrative_forms.ZUPCUpdateForm(form_data={"zupc":ads.ZUPC.nom}, obj=ads)
    if request.method == "POST":
        form.populate_obj(zupc)
        if form.validate():
            db.session.commit()
            return redirect(url_for('zupc_list'))

    return render_template('forms/ads.html', form=form,
        form_method="POST", submit_value="Modifier")


@mod.route('/zupc/delete')
@login_required
def zupc_delete():
    if not request.args.get("id"):
        abort(404)
    zupc = administrative_models.ZUPC.query.get(request.args.get("id"))
    if not zupc:
        abort(404)
    db.session.delete(zupc)
    db.session.commit()
    return redirect(url_for("zupc_list"))


@mod.route('/zupc/autocomplete')
def zupc_autocomplete():
    #@TODO: have some identification here?
    term = request.args.get('q')
    like = "%{}%".format(term)
    app.logger.info(term)
    app.logger.info(like)

    response = administrative_models.ZUPC.query.filter(
            administrative_models.ZUPC.nom.ilike(like)).all()
    return jsonify(suggestions=map(lambda zupc:{'name': zupc.nom, 'id': int(zupc.id)},
                                        response))

