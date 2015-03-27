# -*- coding: utf8 -*-
from backoffice_operateurs.utils import ModelForm
from backoffice_operateurs.models import taxis
from wtforms import HiddenField, SubmitField

class ADSForm(ModelForm):
    class Meta:
        model = taxis.ADS

class ADSCreateForm(ADSForm):
    submit = SubmitField(u'Créer')

class ADSUpdateForm(ADSForm):
    id = HiddenField()
    submit = SubmitField(label="Modifier")

class ConducteurForm(ModelForm):
    class Meta:
        model = taxis.Conducteur

class ConducteurCreateForm(ConducteurForm):
    submit = SubmitField(u'Créer')

class ConducteurUpdateForm(ConducteurForm):
    id = HiddenField()
    submit = SubmitField(u'Modifier')
