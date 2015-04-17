# -*- coding: utf8 -*-
from ..utils import ModelForm, HistoryMixin
from ..models import taxis
from ..forms import administrative
from wtforms import HiddenField, SubmitField, StringField, FormField

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


class ConducteurForm(ModelForm):
    class Meta:
        model = taxis.Conducteur
        exclude = ['added_at', 'added_via', 'source', 'last_update_at']


class ConducteurCreateForm(ConducteurForm):
    submit = SubmitField(u'Créer')


class ConducteurUpdateForm(ConducteurForm):
    id = HiddenField()
    submit = SubmitField(u'Modifier')
