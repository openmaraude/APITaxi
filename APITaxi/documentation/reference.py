# -*- coding: utf-8 -*-
from flask import Blueprint, render_template

mod = Blueprint('documentation_reference', __name__)

@mod.route('/documentation/reference')
def doc_reference():
    return render_template('documentation/reference.html')
