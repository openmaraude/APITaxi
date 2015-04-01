# -*- coding: utf8 -*-
from backoffice_operateurs import app, db
from backoffice_operateurs.forms import taxis as taxis_forms
from backoffice_operateurs.models import taxis as taxis_models
from flask import render_template, request, redirect, url_for, abort
from flask.ext.security import login_required
from wtforms import StringField


@app.route('/ads')
@app.route('/ads/')
@login_required
def ads_list():
    page = int(request.args.get('page')) if 'page' in request.args else 1
    return render_template('lists/ads.html',
        ads_list=taxis_models.ADS.query.paginate(page))


@app.route('/ads/create', methods=['GET', 'POST'])
@login_required
def ads_create():
    form = taxis_forms.ADSCreateForm()
    if request.method == "POST" and form.validate():
        ads = taxis_models.ADS()
        form.populate_obj(ads)
        db.session.add(ads)
        db.session.commit()
        return redirect(url_for('ads_list'))
    return render_template('forms/ads.html', form=form, form_method="POST")


@app.route('/ads/update', methods=['GET', 'POST'])
@login_required
def ads_update():
    if not request.args.get("id"):
        abort(404)
    ads = taxis_models.ADS.query.get(request.args.get("id"))
    if not ads:
        abort(404)
    form = taxis_forms.ADSUpdateForm(obj=ads, zupc=ads.ZUPC.nom)
    if request.method == "POST":
        form.populate_obj(ads)
        if form.validate():
            db.session.commit()
            return redirect(url_for('ads_list'))

    return render_template('forms/ads.html', form=form,
        form_method="POST")


@app.route('/ads/delete')
@login_required
def ads_delete():
    if not request.args.get("id"):
        abort(404)
    ads = taxis_models.ADS.query.get(request.args.get("id"))
    if not ads:
        abort(404)
    db.session.delete(ads)
    db.session.commit()
    return redirect(url_for("ads_list"))
