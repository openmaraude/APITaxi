# -*- coding: utf8 -*-
from .. import db
from ..api import api
from . import ns_administrative
from ..forms.taxis import ADSForm, VehicleForm, ADSCreateForm, ADSUpdateForm
from ..models import taxis as taxis_models
from ..utils import create_obj_from_json, request_wants_json
from flask import (Blueprint, render_template, request, redirect, url_for,
                   render_template, request, redirect, url_for, abort, jsonify,
                   current_app)
from flask.ext.security import login_required, current_user, roles_accepted
from datetime import datetime
from flask.ext.restplus import fields, abort, Resource, reqparse
from ..utils.make_model import make_model

mod = Blueprint('ads', __name__)

ads_model = make_model('taxis', 'ADS')
ads_expect = make_model('taxis', 'ADS', True, filter_id=True)
ads_post = make_model('taxis', 'ADS', True)


@ns_administrative.route('ads/', endpoint="ads")
class ADS(Resource):

    parser = reqparse.RequestParser()
    parser.add_argument('numero', type=str, help=u"Numero de l'ADS")
    parser.add_argument('insee', type=str, help=u"Code INSEE de la commune d\'attribution de l'ADS")

    @login_required
    @roles_accepted('admin', 'operateur')
    @api.hide
    @api.doc(parser=parser, responses={200: ('ADS', ads_model)})
    def get(self):
        args = self.__class__.parser.parse_args()
        if args["numero"] and args["insee"]:
            return self.ads_details(args.get("numero"), args.get("insee"))
        else:
            return self.ads_list()

    def ads_list(self):
        if request_wants_json():
            abort(501, message="You need to ask for JSON")
        if not taxis_models.ADS.can_be_listed_by(current_user):
            abort(403, message="You're not allowed to see this page")
        q = taxis_models.ADS.query
        if not current_user.has_role('admin'):
            q.filter_by(added_by=current_user.id)
        page = int(request.args.get('page')) if 'page' in request.args else 1
        return render_template('lists/ads.html',
            ads_list=q.paginate(page))

    def ads_details(self, numero, insee):
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
        #@TODO: make it dependent of the user's role
        if request_wants_json():
            return jsonify({(k[0], getattr(ads, k[0])) for k in d.iteritems() if is_valid_key(k[1])})
        return render_template("details/ads.html",
                ads=[(k[1].info["label"], getattr(ads, k[0])) for k in d.iteritems() if is_valid_key(k[1])])


    @login_required
    @roles_accepted('admin', 'operateur')
    @api.doc(responses={404:'Resource not found',
        403:'You\'re not authorized to view it'})
    @api.expect(ads_expect)
    @api.marshal_with(ads_post)
    def post(self):
        json = request.get_json()
        if "data" not in json:
            abort(400, message="No data field in request")
        if len(json['data']) > 250:
            abort(413, message="You can only pass 250 objects")
        new_ads = []
        for ads in json['data']:
            if ads['vehicle_id'] and\
              not taxis_models.Vehicle.query.get(ads['vehicle_id']):
                abort(400, message="Unable to find a vehicle with the id: {}"\
                        .format(ads['vehicle_id']))
            try:
                new_ads.append(create_obj_from_json(taxis_models.ADS, ads))
            except KeyError as e:
                abort(400, message="Missing key: "+str(e))
            db.session.add(new_ads[-1])
        db.session.commit()

        return {"data": new_ads}, 201


@mod.route('/ads/form', methods=['GET', 'POST'])
@login_required
@roles_accepted('admin', 'operateur')
def ads_form():
    ads = form = None
    if request.args.get("id"):
        ads = taxis_models.ADS.query.get(request.args.get("id"))
        if not ads:
            abort(404, message="Unable to find the ADS")
        if not ads.can_be_edited_by(current_user):
            abort(403, message="You're not allowed to edit this ADS")
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
@roles_accepted('admin', 'operateur')
def ads_delete():
    if not request.args.get("id"):
        abort(404, message="You need to specify an id")
    ads = taxis_models.ADS.query.get(request.args.get("id"))
    if not ads:
        abort(404, message="Unable to find this ADS")
    if not ads.can_be_deleted_by(current_user):
        abort(403, message="You're not allowed to delete this ADS")
    db.session.delete(ads)
    db.session.commit()
    return redirect(url_for("ads.ads"))
