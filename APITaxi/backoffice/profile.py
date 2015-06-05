# -*- coding: utf-8 -*-
from .. import db
from ..models import security as security_models
from ..forms.user import UserForm
from flask.ext.security import login_required, roles_accepted, current_user
from flask import (Blueprint, request, render_template, redirect, jsonify,
                   url_for, abort, current_app, send_file)
from werkzeug import secure_filename
import os
from flask_wtf import Form
from flask_wtf.file import FileField
import uuid
from PIL import Image


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
        db.session.commit()
        return redirect(url_for('profile.profile_form'))
    return render_template('forms/profile.html', form=form,
        form_method="POST", submit_value="Modifier")

@mod.route('/user/<int:user_id>/images/<src>')
def profile_images(user_id, src):
    logo = security_models.Logo.query.get(src)
    if not logo:
        abort(404)
    if not logo.user_id == user_id:
        abort(404)
    return send_file(os.path.join(current_app.config['UPLOADED_IMAGES_DEST'],
        logo.id))
