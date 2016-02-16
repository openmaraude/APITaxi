# -*- coding: utf-8 -*-
from ..extensions import documents
from ..api import api
from . import ns_administrative
from ..forms.taxis import DriverCreateForm, DriverUpdateForm
from ..models import taxis as taxis_models, administrative as administrative_models
from ..descriptors.drivers import driver_fields, driver_details_expect
from APITaxi_utils.populate_obj import create_obj_from_json
from APITaxi_utils.request_wants_json import request_wants_json
from flask import Blueprint, render_template, request, redirect, url_for, current_app
from flask.ext.security import login_required, current_user, roles_accepted
from datetime import datetime
from flask.ext.restplus import fields, Resource, reqparse, abort, marshal
from APITaxi_utils.slack import slack as slacker
from APITaxi_utils.resource_metadata import ResourceMetadata

mod = Blueprint('drivers', __name__)

@ns_administrative.route('drivers/')
class Drivers(ResourceMetadata):
    model = taxis_models.Driver

    @login_required
    @roles_accepted('admin', 'operateur', 'prefecture')
    @api.expect(driver_details_expect)
    @api.response(200, 'Success', driver_fields)
    def post(self):
        if 'file' in request.files:
            filename = "conducteurs-{}-{}.csv".format(current_user.email,
                    str(datetime.now()))
            documents.save(request.files['file'], name=filename)
            slack = slacker()
            if slack:
                slack.chat.post_message(current_app.config['SLACK_CHANNEL'],
                'Un nouveau fichier conducteurs a été envoyé par {}. {}'.format(
                    current_user.email, url_for('documents.documents',
                        filename=filename, _external=True)))
            return "OK"
        if request_wants_json():
            return self.post_json()
        abort(400, message="Unable to find file")


    def post_json(self):
        db = current_app.extensions['sqlalchemy'].db
        json = request.get_json()
        if "data" not in json:
            abort(400, message="You need data a data object")
        if len(json['data']) > 250:
            abort(413, message="You've reach the limits of 250 objects")
        edited_drivers_id = []
        new_drivers = []
        for driver in json['data']:
            departement = None
            if 'numero' in driver['departement']:
                departement = administrative_models.Departement.\
                    filter_by_or_404(numero=driver['departement']['numero'])
            elif 'nom' in driver['departement']:
                departement = administrative_models.Departement.\
                    filter_by_or_404(nom=driver['departement']['nom'])
            try:
                driver_obj = create_obj_from_json(taxis_models.Driver, driver)
                driver_obj.departement_id = departement.id
            except KeyError as e:
                abort(400, message="Key error")
            db.session.add(driver_obj)
            if driver_obj.id:
                edited_drivers_id.append(driver_obj.id)
            new_drivers.append(driver_obj)
        db.session.commit()
        return marshal({'data': new_drivers}, driver_fields), 201

    @api.hide
    @login_required
    @roles_accepted('admin', 'operateur', 'prefecture', 'stats')
    def get(self):
        if not taxis_models.Driver.can_be_listed_by(current_user):
            if current_user.has_role('stats'):
                return self.metadata()
            abort(403, message="You can't list drivers")
        page = int(request.args.get('page')) if 'page' in request.args else 1
        q = taxis_models.Driver.query
        if not current_user.has_role('admin') and not current_user.has_role('prefecture'):
            q = q.filter_by(added_by=current_user.id)
        return render_template('lists/drivers.html',
            driver_list=q.paginate(page))


@mod.route('/drivers/form', methods=['GET', 'POST'])
@login_required
@roles_accepted('admin', 'operateur', 'prefecture')
def driver_form():
    db = current_app.extensions['sqlalchemy'].db
    form = None
    if request.args.get("id"):
        driver = taxis_models.Driver.query.get(request.args.get("id"))
        if not driver:
            abort(404, message="Unable to find driver")
        if not driver.can_be_edited_by(current_user):
            abort(403, message="You can't edit this driver")
        form = DriverUpdateForm(obj=driver)
    else:
        form = DriverCreateForm()
    if request.method == "POST":
        if request.args.get("id"):
            driver.last_update_at = datetime.now().isoformat()
            form.populate_obj(driver)
            if form.validate():
                db.session.commit()
                return redirect(url_for('api.drivers'))
        else:
            driver = taxis_models.Driver()
            form.populate_obj(driver)
            db.session.add(driver)
            db.session.commit()
            return redirect(url_for('api.drivers'))
    return render_template('forms/driver.html', form=form,
        form_method="POST", submit_value="Modifier")


@mod.route('/drivers/delete')
@roles_accepted('admin', 'operateur', 'prefecture')
@login_required
def driver_delete():
    db = current_app.extensions['sqlalchemy'].db
    if not request.args.get("id"):
        abort(404, message="An id is required")
    driver = taxis_models.Driver.query.get(request.args.get("id"))
    if not driver:
        abort(404, message="Unable to find the driver")
    if not driver.can_be_deleted_by(current_user):
        abort(403, message="You're not allowed to delete this driver")
    #We need to delete attached taxis
    for taxi in db.session.query(taxis_models.Taxi).filter_by(driver_id=driver.id):
        db.session.delete(taxi)
    db.session.delete(driver)
    db.session.commit()
    return redirect(url_for('api.administrative_drivers'))
