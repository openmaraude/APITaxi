# -*- coding: utf-8 -*-
from .forms.taxis import (ADSForm, VehicleForm, ADSCreateForm, ADSUpdateForm,
                          VehicleDescriptionForm)
from APITaxi_models import (taxis as taxis_models, vehicle as vehicle_models,
        administrative as administrative_models)
from APITaxi_utils.populate_obj import create_obj_from_json
from APITaxi_utils.request_wants_json import request_wants_json
from flask import (Blueprint, render_template, request, redirect, url_for,
                   abort, jsonify, current_app)
from flask.ext.security import login_required, current_user, roles_accepted
from datetime import datetime
from flask.ext.restplus import fields, abort, Resource, reqparse, marshal
from APITaxi_utils.slack import slack
from APITaxi_utils.resource_metadata import ResourceMetadata

mod = Blueprint('ads', __name__)

@mod.route('/ads/_view')
@login_required
@roles_accepted('admin', 'operateur', 'prefecture', 'stats')
def get_ads_list():
    if request_wants_json():
        abort(501, message="You can't ask for JSON")
    parser = reqparse.RequestParser()
    parser.add_argument('numero', type=unicode, help=u"Numero de l'ADS", required=False,
                        location='values')
    parser.add_argument('insee', type=unicode,
            help=u"Code INSEE de la commune d\'attribution de l'ADS", required=False,
                    location='values')
    args = self.parser.parse_args()
    if args["numero"] and args["insee"]:
        return ads_details(args.get("numero"), args.get("insee"))
    else:
        return ads_list()

def ads_list():
    if not taxis_models.ADS.can_be_listed_by(current_user):
        if current_user.has_role('stats'):
            return self.metadata()
        abort(403, message="You're not allowed to see this page")
    q = taxis_models.ADS.query
    if not current_user.has_role('admin') and not current_user.has_role('prefecture'):
        q = q.filter_by(added_by=current_user.id)
    page = int(request.args.get('page')) if 'page' in request.args else 1
    return render_template('lists/ads.html',
        ads_list=q.paginate(page) if q else None)

def ads_details(numero, insee):
    filters = {
            "numero": str(numero),
            "insee": str(insee)
            }
    ads = taxis_models.ADS.query.filter_by(**filters).all()
    if not ads:
        abort(404, error="Unable to find this couple INSEE/numero")
    ads = ads[0]
    d = taxis_models.ADS.__dict__
    keys_to_show = ads.showable_fields(current_user)
    is_valid_key = lambda k: hasattr(k, "info") and k.info.has_key("label")\
                             and k.info['label'] and k.key in keys_to_show
    return render_template("details/ads.html",
            ads=[(k[1].info["label"],
                getattr(ads, k[0])) for k in d.iteritems() if is_valid_key(k[1])])


@mod.route('/ads/form', methods=['GET', 'POST'])
@login_required
@roles_accepted('admin', 'operateur', 'prefecture')
def ads_form():
    ads = form = None
    if request.args.get("id"):
        ads = taxis_models.ADS.query.get(request.args.get("id"))
        if not ads:
            abort(404, message="Unable to find the ADS")
        if not ads.can_be_edited_by(current_user):
            abort(403, message="You're not allowed to edit this ADS")
        form = ADSUpdateForm()
        form.ads.form = ADSForm(obj=ads)
        if ads.vehicle:
            form.vehicle.form = VehicleForm(obj=ads.vehicle)
            form.vehicle_description.form = VehicleDescriptionForm(
                    obj=ads.vehicle.description)
    else:
        form = ADSCreateForm()
    if request.method == "POST":
        if not form.validate():
            return render_template('forms/ads.html', form=form)
        if not ads:
            ads = taxis_models.ADS(form.vehicle.form.data['licence_plate'])
        if not ads.vehicle.description:
            ads.vehicle.descriptions.append(vehicle_models.VehicleDescription(
                vehicle_id=ads.vehicle.id, added_by=current_user.id))
        else:
            ads.last_update_at = datetime.now().isoformat()
        zupc = administrative_models.ZUPC.query\
                .filter_by(insee=form.ads.insee.data).first()
        if zupc is None:
            abort(400, message="Unable to find a ZUPC for insee: {}".format(
                ads.insee))
        ads.zupc = administrative_models.ZUPC.query.get(zupc.parent_id)
        ads.zupc_id = ads.zupc.id
        try:
            form.ads.form.populate_obj(ads)
        except AssertionError:
            abort(400, message='Bad owner type')
        form.vehicle.form.populate_obj(ads.vehicle)
        form.vehicle_description.form.populate_obj(ads.vehicle.description)
        current_app.extensions['sqlalchemy'].db.session.add(ads)
        current_app.extensions['sqlalchemy'].db.session.commit()
        return redirect(url_for('api.ads'))
    return render_template('forms/ads.html', form=form)


@mod.route('/ads/delete')
@login_required
@roles_accepted('admin', 'operateur', 'prefecture')
def ads_delete():
    if not request.args.get("id"):
        abort(404, message="You need to specify an id")
    ads = taxis_models.ADS.query.get(request.args.get("id"))
    if not ads:
        abort(404, message="Unable to find this ADS")
    if not ads.can_be_deleted_by(current_user):
        abort(403, message="You're not allowed to delete this ADS")
    db = current_app.extensions['sqlalchemy'].db
    db.session.delete(ads)
    #We need to delete attached taxis
    for taxi in db.session.query(taxis_models.Taxi).filter_by(ads_id=ads.id):
        db.session.delete(taxi)
    db.session.commit()
    return redirect(url_for("api.ads"))
