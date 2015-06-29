# -*- coding: utf-8 -*-
from ..utils.model_form import ModelForm
from ..models import administrative
from wtforms import HiddenField, SubmitField
from wtforms.fields import FormField
from wtforms_alchemy import ModelFormField
from wtforms.widgets import ListWidget
from wtforms.ext.sqlalchemy.fields import QuerySelectField

def departements():
    return administrative.Departement.query.all()

class ZUPCSimpleForm(ModelForm):
    class Meta:
        skip_unknown_types = True
        model = administrative.ZUPC
    exclude = ['shape']

class ZUPCForm(ZUPCSimpleForm):
    departement = QuerySelectField(query_factory=departements, get_label='nom')


class ZUPCreateForm(ZUPCForm):
    submit = SubmitField(u'Créer')


class ZUPCUpdateForm(ZUPCForm):
    id = HiddenField()          
    submit = SubmitField(u'Modifier')


