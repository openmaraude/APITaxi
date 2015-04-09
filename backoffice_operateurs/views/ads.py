# -*- coding: utf8 -*-
from backoffice_operateurs import db
from backoffice_operateurs.forms.taxis import ADSCreateForm, ADSUpdateForm
from backoffice_operateurs.models import taxis as taxis_models
from flask import Blueprint, render_template, request, redirect, url_for, abort
from backoffice_operateurs.utils import create_obj_from_json
from flask import render_template, request, redirect, url_for, abort, jsonify
from flask.ext.security import login_required, current_user
from datetime import datetime


mod = Blueprint('ads', __name__)

def ads_list():
    if not taxis_models.ADS.can_be_listed_by(current_user):
        abort(403)
    q = taxis_models.ADS.query
    if not current_user.has_role('admin'):
        q.filter_by(added_by=current_user.id)
    page = int(request.args.get('page')) if 'page' in request.args else 1
    return render_template('lists/ads.html',
        ads_list=q.paginate(page))

def ads_create_api():
    json = request.get_json()
    if "ads" not in json:
        abort(400)
    new_ads = None
    try:
        new_ads = create_obj_from_json(taxis_models.ADS,
            json['ads'])
    except KeyError as e:
        print "Error :",e
        abort(400)
    db.session.add(new_ads)
    db.session.commit()
    return jsonify(new_ads.as_dict())

def ads_details(immatriculation, numero):
    filters = {
            "numero": numero,
            "immatriculation": immatriculation
            }
    ads = taxis_models.ADS.query.filter_by(**filters).all()
    if not ads:
        abort(404)
    ads = ads[0]
    d = taxis_models.ADS.__dict__
    keys_to_show = ads.showable_fields(current_user)
    is_valid_key = lambda k: hasattr(k, "info") and k.info.has_key("label") and k.info['label'] and k.key in keys_to_show
    #@TODO: make it dependent of the user's role
    if request.content_type == "application/json":
        return jsonify({(k[0], getattr(ads, k[0])) for k in d.iteritems() if is_valid_key(k[1])})
    return render_template("details/ads.html",
            ads=[(k[1].info["label"], getattr(ads, k[0])) for k in d.iteritems() if is_valid_key(k[1])])


@mod.route('/ads', methods=['GET', 'POST'])
@mod.route('/ads/', methods=['GET', 'POST'])
@login_required
def ads():
    if request.method == 'GET':
        if request.args.has_key("immatriculation")\
                and request.args.has_key("numero"):
            return ads_details(request.args.get("immatriculation"),
                    request.args.get("numero"))
        else:
            return ads_list()
    elif request.method == 'POST':
        return ads_create_api()
    abort(405)


@mod.route('/ads/form', methods=['GET', 'POST'])
@login_required
def ads_form():
    ads = zupc = form = None
    if request.args.get("id"):
        ads = taxis_models.ADS.query.get(request.args.get("id"))
        if not ads:
            abort(404)
        if not ads.can_be_edited_by(current_user)
            abort(403)
        form = ADSUpdateForm(obj=ads, zupc=ads.ZUPC.nom)
    else:
        form = ADSCreateForm()
    if request.method == "POST":
        if not ads and form.validate():
            ads = taxis_models.ADS()
            form.populate_obj(ads)
            db.session.add(ads)
            db.session.commit()
            return redirect(url_for('ads.ads'))
        elif ads:
            ads.last_update_at = datetime.now().isoformat()
            form.populate_obj(ads)
            if form.validate():
                db.session.commit()
                return redirect(url_for('ads.ads'))
    return render_template('forms/ads.html', form=form)

@mod.route('/ads/delete')
@login_required
def ads_delete():
    if not request.args.get("id"):
        abort(404)
    ads = taxis_models.ADS.query.get(request.args.get("id"))
    if not ads:
        abort(404)
    if not ads.can_be_deleted_by(current_user):
        abort(403)
    db.session.delete(ads)
    db.session.commit()
    return redirect(url_for("ads.ads"))
