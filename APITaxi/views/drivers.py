# -*- coding: utf8 -*-
from .. import db, api, ns_administrative
from ..forms.taxis import DriverCreateForm,\
        DriverUpdateForm
from ..models import taxis as taxis_models, administrative as administrative_models
from ..utils import create_obj_from_json
from flask import Blueprint, render_template, request, redirect, url_for, abort
from flask import render_template, request, redirect, url_for, jsonify,\
        current_app
from flask.ext.security import login_required, current_user, roles_accepted
from datetime import datetime
from flask_restful import Resource, abort
from flask.ext.restplus import fields
from ..utils.make_model import make_model


mod = Blueprint('drivers', __name__)

driver_fields = make_model('taxis', 'Driver')
driver_details_expect = make_model('taxis', 'Driver', filter_id=True)

@ns_administrative.route('drivers/')
class Drivers(Resource):

    @api.marshal_with(driver_fields)
    @api.expect(driver_details_expect)
    @login_required
    def post(self):
        json = request.get_json()
        if "data" not in json:
            current_app.logger.error("No data in json")
            abort(400)
        if len(json['data']) > 250:
            abort(413)
        new_drivers = []
        for driver in json['data']:
            if not administrative_models.Departement.query.get(driver['departement_id']):
                abort(400, message='Unable to find the *departement*')
            try:
                new_drivers.append(create_obj_from_json(taxis_models.Driver,
                    driver))
            except KeyError as e:
                current_app.logger.error("Key error in driver", e)
                abort(400)
            db.session.add(new_drivers[-1])
        db.session.commit()
        return {'data': new_drivers}

    @api.hide
    @login_required
    @roles_accepted(['admin', 'operateur'])
    def get(self):
        if not taxis_models.Driver.can_be_listed_by(current_user):
            abort(403)
        page = int(request.args.get('page')) if 'page' in request.args else 1
        q = taxis_models.Driver
        if not current_user.has_role('admin'):
            q.filter_by(added_by=current_user.id)
        return render_template('lists/drivers.html',
            driver_list=q.query.paginate(page))


@mod.route('/drivers/form', methods=['GET', 'POST'])
@login_required
@roles.accepted(['admin', 'operateur'])
def driver_form():
    form = None
    if request.args.get("id"):
        driver = taxis_models.Driver.query.get(request.args.get("id"))
        if not driver:
            abort(404)
        if not driver.can_be_edited_by(current_user):
            abort(403)
        form = DriverUpdateForm(obj=driver)
    else:
        form = DriverCreateForm()
    if request.method == "POST":
        if request.args.get("id"):
            driver.last_update_at = datetime.now().isoformat()
            form.populate_obj(driver)
            if form.validate():
                db.session.commit()
                return redirect(url_for('drivers'))
        else:
            driver = taxis_models.Driver()
            form.populate_obj(driver)
            db.session.add(driver)
            db.session.commit()
            return redirect(url_for('drivers'))
    return render_template('forms/driver.html', form=form,
        form_method="POST", submit_value="Modifier")


@mod.route('/drivers/delete')
@roles.accepted(['admin', 'operateur'])
@login_required
def driver_delete():
    if not request.args.get("id"):
        abort(404)
    driver = taxis_models.Driver.query.get(request.args.get("id"))
    if not driver:
        abort(404)
    if not driver.can_be_deleted_by(current_user):
        abort(403)
    db.session.delete(driver)
    db.session.commit()
    return redirect(url_for('drivers'))
