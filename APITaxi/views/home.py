# -*- coding: utf8 -*-
from backoffice_operateurs import  db
from flask import Blueprint, render_template, request, redirect, url_for, abort
from flask.ext.security import login_required

mod = Blueprint('home', __name__)

@mod.route('/')
@login_required
def home():
    return render_template('base.html')


