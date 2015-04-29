# -*- coding: utf8 -*-
from ..api import api
import importlib
from flask.ext.restplus import fields as basefields

def make_model(filename, model_name, *args, **kwargs):
    module = importlib.import_module(".".join(['APITaxi', 'models', filename]))
    model = getattr(module, model_name)
    list_names = [filename, model_name]
    list_names.extend(map(lambda i: str(i), args))
    list_names.extend(map(lambda (k, v): k + "_" + str(v), kwargs.items()))
    register_name = "_".join(list_names)
    #@TODO: gros hack degueu, il faudra que cette fonction soit une méthode de classe des models
    details_dict = model.marshall_obj(*args, **kwargs)
    if 'operateur_id' in details_dict:
        del details_dict['operateur_id']
        details_dict['operateur'] = basefields.String(attribute='operateur.email')
    if 'departement_id' in details_dict:
        del details_dict['departement_id']
        details_dict['departement'] = basefields.String(attribute='departement.numero')
    details = api.model(register_name + "_details", details_dict)
    return api.model(register_name,
        {"data": basefields.List(basefields.Nested(details))})
