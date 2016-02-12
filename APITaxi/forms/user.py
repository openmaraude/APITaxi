# -*- coding: utf-8 -*-
from APITaxi_utils.model_form import ModelForm
from ..models import security
from wtforms import HiddenField, SubmitField
from wtforms.fields import FormField
from wtforms_alchemy import ModelFormField
from wtforms.widgets import ListWidget
from wtforms.ext.sqlalchemy.fields import QuerySelectField
from flask_wtf.file import FileField, FileAllowed
from ..extensions import images


class UserFormRaw(ModelForm):
    class Meta:
        model = security.User
        exclude = ['password', 'email', 'active', 'apikey', 'confirmed_at']

class UserForm(UserFormRaw):
    logo = FileField('image', validators=[
        FileAllowed(images, 'Images only!')
    ])
    submit = SubmitField(u'Modifier')
