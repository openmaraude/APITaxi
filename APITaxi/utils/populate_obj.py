# -*- coding: utf-8 -*-
from . import HistoryMixin

def create_obj_from_json(cls, json_obj):
    keys = [k for k in cls.__table__.columns if k.name not in HistoryMixin.to_exclude()]
    required_keys = [k.name for k in keys if not k.nullable and not k.primary_key]
    for key in required_keys:
        if key not in json_obj or json_obj[key] is None:
            raise KeyError(key)
    new_obj = cls()
    for k in keys:
        name = k.name
        if name not in json_obj:
            continue
        setattr(new_obj, name, json_obj[name])
    return new_obj
