# -*- coding: utf-8 -*-
from flask.ext.wtf import Form
from wtforms_alchemy import model_form_factory
from flask import current_app

BaseModelForm = model_form_factory(Form)

class ModelForm(BaseModelForm):

    @classmethod
    def get_session(self):
        return current_app.extensions['sqlalchemy'].db.session
