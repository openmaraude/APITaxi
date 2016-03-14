# -*- coding: utf-8 -*-
from .forms.taxis import DriverCreateForm, DriverUpdateForm
from APITaxi_models import taxis as taxis_models, administrative as administrative_models
from APITaxi_utils.populate_obj import create_obj_from_json
from APITaxi_utils.request_wants_json import request_wants_json
from flask import Blueprint, render_template, request, redirect, url_for, current_app
from flask.ext.security import login_required, current_user, roles_accepted
from datetime import datetime
from flask.ext.restplus import fields, Resource, reqparse, abort, marshal
from APITaxi_utils.slack import slack as slacker
from APITaxi_utils.resource_metadata import ResourceMetadata

mod = Blueprint('drivers', __name__)

@mod.route('/drivers/_view')
@login_required
@roles_accepted('admin', 'operateur', 'prefecture', 'stats')
def drivers_view(self):
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
                current_app.extensions['sqlalchemy'].db.session.commit()
                return redirect(url_for('api.drivers'))
        else:
            driver = taxis_models.Driver()
            form.populate_obj(driver)
            db.session.add(driver)
            db.session.commit()

            cur = db.session.connection().connection.cursor()
            cur.execute("""
                UPDATE taxi set driver_id = %s WHERE driver_id IN (
                    SELECT id FROM driver WHERE professional_licence = '%s'
                    AND departement_id = %s
                )""",
                (driver.id, driver.professional_licence, driver.departement_id)
            )

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
    for taxi in current_app.extensions['sqlalchemy'].db.session\
            .query(taxis_models.Taxi).filter_by(driver_id=driver.id):
        current_app.extensions['sqlalchemy'].db.session.delete(taxi)
    current_app.extensions['sqlalchemy'].db.session.delete(driver)
    current_app.extensions['sqlalchemy'].db.session.commit()
    return redirect(url_for('api.administrative_drivers'))
