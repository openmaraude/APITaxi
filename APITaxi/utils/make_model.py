# -*- coding: utf8 -*-
from .. import api
import importlib
from flask.ext.restplus import fields as basefields

def make_model(filename, model_name, *args, **kwargs):
    module = importlib.import_module(".".join(['APITaxi', 'models', filename]))
    model = getattr(module, model_name)
    list_names = [filename, model_name]
    list_names.extend(map(lambda i: str(i), args))
    list_names.extend(map(lambda (k, v): k + "_" + str(v), kwargs.items()))
    register_name = "_".join(list_names)
    details = api.model(register_name + "_details",
                        model.marshall_obj(*args, **kwargs))
    return api.model(register_name,
        {"data": basefields.List(basefields.Nested(details))})
