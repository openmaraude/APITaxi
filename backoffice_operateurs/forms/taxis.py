# -*- coding: utf8 -*-
from backoffice_operateurs.utils import ModelForm, HistoryMixin
from backoffice_operateurs.models import taxis
from backoffice_operateurs.forms import administrative
from wtforms import HiddenField, SubmitField, StringField


def get_zupc(id_):
    return taxis.ADS.query.filter_by(id=id_)


class ADSForm(ModelForm):
    class Meta:
        model = taxis.ADS
        exclude = HistoryMixin.to_exclude()

    zupc = StringField(u'ZUPC', id='zupc')
    ZUPC_id = HiddenField('ZUPC_id', id='ZUPC_id')


class ADSCreateForm(ADSForm):
    submit = SubmitField(u'Créer')


class ADSUpdateForm(ADSForm):
    id = HiddenField()
    submit = SubmitField("Modifier")


class ConducteurForm(ModelForm):
    class Meta:
        model = taxis.Conducteur
        exclude = HistoryMixin.to_exclude()


class ConducteurCreateForm(ConducteurForm):
    submit = SubmitField(u'Créer')


class ConducteurUpdateForm(ConducteurForm):
    id = HiddenField()
    submit = SubmitField(u'Modifier')
