# -*- coding: utf8 -*-
from ..utils import ModelForm
from ..models import taxis, administrative
from wtforms import HiddenField, SubmitField, StringField, FormField
from wtforms.ext.sqlalchemy.fields import QuerySelectField


class VehicleForm(ModelForm):
    def __init__(self, *args, **kwargs):
        kwargs['csrf_enabled'] = False
        super(ModelForm, self).__init__(*args, **kwargs)
    class Meta:
        model = taxis.Vehicle
        exclude = ['added_at', 'added_via', 'source', 'last_update_at']


class ADSForm(ModelForm):
    def __init__(self, *args, **kwargs):
        kwargs['csrf_enabled'] = False
        super(ModelForm, self).__init__(*args, **kwargs)
    class Meta:
        model = taxis.ADS
        exclude = ['added_at', 'added_via', 'source', 'last_update_at']

class ADSFormVehicle(ModelForm):
    vehicle = FormField(VehicleForm)
    ads = FormField(ADSForm)

class ADSCreateForm(ADSFormVehicle):
    submit = SubmitField(u'Créer')


class ADSUpdateForm(ADSFormVehicle):
    id = HiddenField()
    submit = SubmitField("Modifier")


def departements():
    return administrative.Departement.query.all()

class ConducteurForm(ModelForm):
    class Meta:
        model = taxis.Conducteur
        exclude = ['added_at', 'added_via', 'source', 'last_update_at']

    departement = QuerySelectField(query_factory=departements, get_label='nom')


class ConducteurCreateForm(ConducteurForm):
    submit = SubmitField(u'Créer')


class ConducteurUpdateForm(ConducteurForm):
    id = HiddenField()
    submit = SubmitField(u'Modifier')
