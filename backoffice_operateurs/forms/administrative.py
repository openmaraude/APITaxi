# -*- coding: utf8 -*-
from backoffice_operateurs.utils import ModelForm
from backoffice_operateurs.models import administrative
from wtforms import HiddenField, SubmitField

class ZUPCForm(ModelForm):
    class Meta:
        model = administrative.ZUPC

class ZUPCreateForm(ZUPCForm):
    submit = SubmitField(u'Créer')

class ZUPCUpdateForm(ZUPCForm):
    id = HiddenField()
    submit = SubmitField(u'Modifier')
