# -*- coding: utf-8 -*-
from flask import Blueprint, send_from_directory, current_app
from flask.ext.security import login_required, roles_accepted

mod = Blueprint('documents', __name__)

@mod.route('/documents/<path:filename>')
@login_required
@roles_accepted('admin')
def documents(filename):
    return send_from_directory(current_app.config['UPLOADED_DOCUMENTS_DEST'],
            filename)
