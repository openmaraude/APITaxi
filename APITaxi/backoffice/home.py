# -*- coding: utf8 -*-
from flask import Blueprint, render_template, current_app
from flask.ext.security import login_required

mod = Blueprint('home_bo', __name__)

@mod.route('/')
@login_required
def home():
    return render_template('base.html')


