# -*- coding: utf-8 -*-
from ..extensions import db, documents, index_zupc
from ..api import api
from . import ns_administrative
from ..forms.taxis import (ADSForm, VehicleForm, ADSCreateForm, ADSUpdateForm,
                          VehicleDescriptionForm)
from ..models import (taxis as taxis_models, vehicle as vehicle_models,
        administrative as administrative_models)
from ..utils import create_obj_from_json, request_wants_json
from flask import (Blueprint, render_template, request, redirect, url_for,
                   render_template, request, redirect, url_for, abort, jsonify,
                   current_app)
from flask.ext.security import login_required, current_user, roles_accepted
from datetime import datetime
from flask.ext.restplus import fields, abort, Resource, reqparse, marshal
from ..utils.make_model import make_model
from ..utils.slack import slack
from ..utils.cache_refresh import cache_refresh

mod = Blueprint('ads', __name__)

ads_model = make_model('taxis', 'ADS')
ads_expect = make_model('taxis', 'ADS', True, filter_id=True)
ads_post = make_model('taxis', 'ADS', True)


@ns_administrative.route('ads/', endpoint="ads")
class ADS(Resource):

    parser = reqparse.RequestParser()
    parser.add_argument('numero', type=unicode, help=u"Numero de l'ADS")
    parser.add_argument('insee', type=unicode,
            help=u"Code INSEE de la commune d\'attribution de l'ADS")

    @login_required
    @roles_accepted('admin', 'operateur', 'prefecture')
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
        if not current_user.has_role('admin') and not current_user.has_role('prefecture'):
            q = q.filter_by(added_by=current_user.id)
        page = int(request.args.get('page')) if 'page' in request.args else 1
        return render_template('lists/ads.html',
            ads_list=q.paginate(page) if q else None)

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
            return jsonify({(k[0],
                getattr(ads, k[0])) for k in d.iteritems() if is_valid_key(k[1])})
        return render_template("details/ads.html",
                ads=[(k[1].info["label"],
                    getattr(ads, k[0])) for k in d.iteritems() if is_valid_key(k[1])])


    @login_required
    @roles_accepted('admin', 'operateur', 'prefecture')
    @api.doc(responses={404:'Resource not found',
        403:'You\'re not authorized to view it'})
    @api.expect(ads_expect)
    @api.response(200, 'Success', ads_post)
    @index_zupc.reinit()
    def post(self):
        if request_wants_json():
            return self.post_json()
        elif 'file' in request.files:
            filename = "ads-{}-{}.csv".format(current_user.email,
                    str(datetime.now()))
            documents.save(request.files['file'], name=filename)
            slacker = slack()
            if slacker:
                slacker.chat.post_message('#taxis',
                'Un nouveau fichier ADS a été envoyé par {}. {}'.format(
                    current_user.email, url_for('documents.documents',
                        filename=filename, _external=True)))
            return "OK"
        abort(400, message="File is not present!")

    def post_json(self):
        json = request.get_json()
        if "data" not in json:
            abort(400, message="No data field in request")
        if len(json['data']) > 250:
            abort(413, message="You can only pass 250 objects")
        edited_ads_id = []
        new_ads = []
        for ads in json['data']:
            if ads['vehicle_id'] and\
              not taxis_models.Vehicle.query.get(ads['vehicle_id']):
                abort(400, message="Unable to find a vehicle with the id: {}"\
                        .format(ads['vehicle_id']))
            try:
                ads_db = create_obj_from_json(taxis_models.ADS, ads)
            except KeyError as e:
                abort(400, message="Missing key: "+str(e))
            except AssertionError as e:
                abort(400, message='Bad owner_type value, can be: {}'.format(
                    taxis_models.owner_type_enum
                    ))
            zupc = administrative_models.ZUPC.query.filter_by(insee=ads_db.insee).first()
            if zupc is None:
                abort(400, message="Unable to find a ZUPC for insee: {}".format(
                    ads_db.insee))
            ads_db.zupc_id = zupc.parent_id
            db.session.add(ads_db)
            if ads_db.id:
                edited_ads_id.append(ads.id)
            new_ads.append(ads)
        if edited_ads_id:
            cache_refresh(db.session(), {'func': taxis_models.refresh_taxi,
                'kwargs': {'ads': edited_ads_id}})
        db.session.commit()
        return marshal({"data": new_ads}, ads_post), 201



@mod.route('/ads/form', methods=['GET', 'POST'])
@login_required
@roles_accepted('admin', 'operateur', 'prefecture')
@index_zupc.reinit()
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
            form.vehicle_description.form = VehicleDescriptionForm(obj=ads.vehicle.description)
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
        db.session.add(ads)
        if ads.id:
            cache_refresh(db.session(),
                    {'func': taxis_models.refresh_taxi,
                       'kwargs': {'ads':ads.id}})
        db.session.commit()
        return redirect(url_for('api.ads'))
    return render_template('forms/ads.html', form=form)


@mod.route('/ads/delete')
@login_required
@roles_accepted('admin', 'operateur', 'prefecture')
@index_zupc.reinit()
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
