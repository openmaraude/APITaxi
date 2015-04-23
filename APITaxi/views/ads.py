# -*- coding: utf8 -*-
from .. import db, api, ns_administrative
from ..forms.taxis import ADSForm, VehicleForm, ADSCreateForm, ADSUpdateForm
from ..models import taxis as taxis_models
from ..utils import create_obj_from_json, request_wants_json
from flask import Blueprint, render_template, request, redirect, url_for
from flask import render_template, request, redirect, url_for, abort, jsonify
from flask.ext.security import login_required, current_user, roles_accepted
from datetime import datetime
from flask_restful import Resource, reqparse, abort
from flask.ext.restplus import fields

mod = Blueprint('ads', __name__)
ads_model = api.model('ads_model', taxis_models.ADS.marshall_obj(), as_list=True)

ads_details = api.model('ads_details', taxis_models.ADS.marshall_obj(True, filter_id=True))
ads_nested = api.model('ads', {"ads": fields.Nested(ads_details)})

@ns_administrative.route('ads/', endpoint="ads")
class ADS(Resource):

    parser = reqparse.RequestParser()
    parser.add_argument('numero', type=int, help=u"Numero de l'ADS")
    parser.add_argument('insee', type=str, help=u"Code INSEE de la commune d\'attribution de l'ADS")

    @api.doc(parser=parser, responses={200: ('ADS', ads_model)})
    @login_required
    def get(self):
        args = self.__class__.parser.parse_args()
        if args["numero"] and args["insee"]:
            return self.ads_details(args.get("numero"), args.get("insee"))
        else:
            return self.ads_list()

    def ads_list(self):
        if request_wants_json():
            abort(501)
        if not taxis_models.ADS.can_be_listed_by(current_user):
            abort(403)
        q = taxis_models.ADS.query
        if not current_user.has_role('admin'):
            q.filter_by(added_by=current_user.id)
        page = int(request.args.get('page')) if 'page' in request.args else 1
        return render_template('lists/ads.html',
            ads_list=q.paginate(page))

    def ads_details(self, numero, insee):
        filters = {
                "numero": numero,
                "insee": insee
                }
        ads = taxis_models.ADS.query.filter_by(**filters).all()
        if not ads:
            abort(404, "Unable to find this couple INSEE/numero")
        ads = ads[0]
        d = taxis_models.ADS.__dict__
        keys_to_show = ads.showable_fields(current_user)
        is_valid_key = lambda k: hasattr(k, "info") and k.info.has_key("label")\
                                 and k.info['label'] and k.key in keys_to_show
        #@TODO: make it dependent of the user's role
        if request_wants_json():
            return jsonify({(k[0], getattr(ads, k[0])) for k in d.iteritems() if is_valid_key(k[1])})
        return render_template("details/ads.html",
                ads=[(k[1].info["label"], getattr(ads, k[0])) for k in d.iteritems() if is_valid_key(k[1])])


    @api.doc(responses={404:'Resource not found',
        403:'You\'re not authorized to view it'})
    @api.expect(ads_nested)
    @login_required
    @roles_accepted('admin', 'operateur')
    def post(self):
        json = request.get_json()
        if "ads" not in json:
            abort(400)
        if not taxis_models.Vehicle.query.get(json['ads']['vehicle_id']):
            abort(400, message="Unable to find a vehicle with the given id")
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


@mod.route('/ads/form', methods=['GET', 'POST'])
@login_required
def ads_form():
    ads = form = None
    if request.args.get("id"):
        ads = taxis_models.ADS.query.get(request.args.get("id"))
        if not ads:
            abort(404)
        if not ads.can_be_edited_by(current_user):
            abort(403)
        ads.vehicle = ads.vehicle or taxis_models.Vehicle()
        form = ADSUpdateForm()
        form.ads.form = ADSForm(obj=ads)
        if ads.vehicle:
            form.vehicle.form = VehicleForm(obj=ads.vehicle)
    else:
        form = ADSCreateForm()
    if request.method == "POST":
        if not ads and form.validate():
            vehicle = taxis_models.Vehicle()
            form.vehicle.form.populate_obj(vehicle)
            db.session.add(vehicle)
            db.session.commit()
            ads = taxis_models.ADS()
            ads.vehicle_id = vehicle.id
            form.ads.form.populate_obj(ads)
            db.session.add(ads)
            db.session.commit()
            return redirect(url_for('ads'))
        elif ads:
            ads.last_update_at = datetime.now().isoformat()
            form.ads.form.populate_obj(ads)
            form.vehicle.form.populate_obj(ads.vehicle)
            if form.validate():
                db.session.commit()
                return redirect(url_for('ads'))
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
