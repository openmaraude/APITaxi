# -*- coding: utf8 -*-
from flask.ext.restplus import fields as basefields

class Date(basefields.BaseField):
    __schema_type__ = 'date'
    __schema_format__ = None

    def schema(self):
        return {
            'type': self.__schema_type__,
            'format': self.__schema_format__,
            'title': self.title,
            'description': self.description,
            'readOnly': self.readonly,
        }

    def format(self):
        return self.isoformat()

    def output(self, key, value):
        if isinstance(value, dict):
            return value[key].isoformat()
        else:
            return getattr(value, key).isoformat()
