# -*- coding: utf-8 -*-
from APITaxi_utils.model_form import ModelForm
from APITaxi_models import security
from wtforms import SubmitField
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
