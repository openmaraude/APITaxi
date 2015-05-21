# -*- coding: utf-8 -*-
from ..utils import ModelForm
from ..models import taxis, administrative, vehicle
from wtforms import HiddenField, SubmitField, StringField, FormField
from wtforms.ext.sqlalchemy.fields import QuerySelectField
from wtforms_alchemy import ModelFormField

class VehicleModelForm(ModelForm):
    def __init__(self, *args, **kwargs):
        kwargs['csrf_enabled'] = False
        super(ModelForm, self).__init__(*args, **kwargs)
    class Meta:
        model = vehicle.Model

class VehicleConstructorForm(ModelForm):
    def __init__(self, *args, **kwargs):
        kwargs['csrf_enabled'] = False
        super(ModelForm, self).__init__(*args, **kwargs)
    class Meta:
        model = vehicle.Constructor

class VehicleDescriptionForm(ModelForm):
    def __init__(self, *args, **kwargs):
        kwargs['csrf_enabled'] = False
        super(ModelForm, self).__init__(*args, **kwargs)
    class Meta:
        model = vehicle.VehicleDescription
        exclude = ['added_at', 'added_via', 'source', 'last_update_at']
    model = ModelFormField(VehicleModelForm)
    constructor = ModelFormField(VehicleConstructorForm)


class VehicleForm(ModelForm):
    def __init__(self, *args, **kwargs):
        kwargs['csrf_enabled'] = False
        super(ModelForm, self).__init__(*args, **kwargs)
    class Meta:
        model = taxis.Vehicle


class ADSForm(ModelForm):
    def __init__(self, *args, **kwargs):
        kwargs['csrf_enabled'] = False
        super(ModelForm, self).__init__(*args, **kwargs)
    class Meta:
        model = taxis.ADS
        exclude = ['added_at', 'added_via', 'source', 'last_update_at']

class ADSFormVehicle(ModelForm):
    vehicle = FormField(VehicleForm)
    vehicle_description = FormField(VehicleDescriptionForm)
    ads = FormField(ADSForm)

class ADSCreateForm(ADSFormVehicle):
    submit = SubmitField(u'Créer')


class ADSUpdateForm(ADSFormVehicle):
    id = HiddenField()
    submit = SubmitField("Modifier")


def departements():
    return administrative.Departement.query.all()

class DriverForm(ModelForm):
    class Meta:
        model = taxis.Driver
        exclude = ['added_at', 'added_via', 'source', 'last_update_at']

    departement = QuerySelectField(query_factory=departements, get_label='nom')


class DriverCreateForm(DriverForm):
    submit = SubmitField(u'Créer')


class DriverUpdateForm(DriverForm):
    id = HiddenField()
    submit = SubmitField(u'Modifier')
