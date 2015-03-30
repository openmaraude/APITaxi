# -*- coding: utf8 -*-
from backoffice_operateurs.utils import ModelForm
from backoffice_operateurs.models import taxis
from backoffice_operateurs.forms import administrative
from wtforms import HiddenField, SubmitField, TextField

def get_zupc(id_):
    return taxis.ADS.query.filer_by(id=id_)

class ADSForm(ModelForm):
    class Meta:
        model = taxis.ADS
    ZUPC_autocomplete = TextField(u'ZUPC', id='zupc_autocomplete')
    ZUPC_id = HiddenField('ZUPC_id', id='ZUPC_id')

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
