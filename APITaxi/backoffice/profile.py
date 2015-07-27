# -*- coding: utf-8 -*-
from .. import db
from ..api import api
from ..models import security as security_models
from ..forms.user import UserForm
from flask.ext.security import login_required, roles_accepted, current_user
from flask import (Blueprint, request, render_template, redirect, jsonify,
                   url_for, abort, current_app, send_file)
from ..utils import fields
from ..utils.refresh_db import cache_refresh
from flask.ext.restplus import fields as basefields, marshal_with, Resource
from werkzeug import secure_filename
import os
from flask_wtf import Form
from flask_wtf.file import FileField
import uuid
from PIL import Image
from . import ns_administrative

mod = Blueprint('profile', __name__)
@mod.route('/user/form', methods=['GET', 'POST'])
@login_required
def profile_form():
    form = None
    form = UserForm(obj=current_user)
    if not current_user.has_role('operateur') and not current_user.has_role('moteur'):
        del form._fields['commercial_name']
    if not current_user.has_role('operateur'):
        del form._fields['logo']
        del form._fields['hail_endpoint_staging']
        del form._fields['hail_endpoint_testing']
        del form._fields['hail_endpoint_production']
    if current_user.has_role('prefecture'):
        del form._fields['email_technical']
        del form._fields['phone_number_technical']
        form._fields['email_customer'].description = u'Adresse email de contact'
        form._fields['email_customer'].label.text = form._fields['email_customer'].description
        form._fields['phone_number_customer'].description = u'Numéro de téléphone de contact'
        form._fields['phone_number_customer'].label.text = \
                form._fields['phone_number_customer'].description

    if request.method == "POST" and form.validate():
        if current_user.has_role('operateur'):
            logo = form.logo
            operateur = security_models.User.query.get(current_user.id)
            if logo and logo.has_file():
                id_ = str(uuid.uuid4())
                file_dest = os.path.join(current_app.config['UPLOADED_IMAGES_DEST'],
                            id_)
                logo.data.save(file_dest)
                image = Image.open(file_dest)
                logo_db = security_models.Logo(id=id_, size=image.size,
                    format_=image.format, user_id=current_user.id)
                db.session.add(logo_db)
                operateur.logos.append(logo_db)
        form.populate_obj(operateur)
        cache_refresh(db.session.session_factory(),
                security_models.User.get_user, id_)
        cache_refresh(db.session.session_factory(),
                security_models.User.get_user_from_email, operateur.email)
        cache_refresh(db.session.session_factory(),
                security_models.User.get_user_from_api_key, operateur.api_key)
        db.session.commit()
        return redirect(url_for('profile.profile_form'))
    return render_template('forms/profile.html', form=form,
        form_method="POST", logos=current_user.logos, submit_value="Modifier",
        )

class LogoHref(basefields.Raw):
    def output(self, key, obj):
        return url_for('profile.image', user_id=obj.user_id, src=obj.id)

model_user = api.model("user", {
    'data': basefields.List(basefields.Nested(
        api.model("user_model",
            {
                "name": fields.String(attribute='commercial_name'),
                "logos": basefields.List(basefields.Nested(
                    api.model('logo_model', 
                        {'href': LogoHref,
                         'size' : fields.String,
                         'format': fields.String(attribute='format_'),
                        }
                        )
                    ))
            }
        )))
    })

@ns_administrative.route('users/<int:user_id>')
class ProfileDetail(Resource):
    @api.marshal_with(model_user)
    def get(self, user_id):
        user = security_models.User.query.get(user_id)
        if not user:
            abort(404, message="Unable to find user")
        return {"data": [user]}, 200

@mod.route('/user/<int:user_id>/images/<src>')
def image(user_id, src):
    logo = security_models.Logo.query.get(src)
    if not logo:
        abort(404, message="Unable to find the logo")
    if not logo.user_id == user_id:
        abort(404, message="Unable to find the logo")
    return send_file(os.path.join(current_app.config['UPLOADED_IMAGES_DEST'],
        logo.id))
