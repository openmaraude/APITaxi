#coding: utf-8

from flask_security.forms import LoginForm as BaseLoginForm
from wtforms import StringField

class LoginForm(BaseLoginForm):
     email = StringField('Username')
