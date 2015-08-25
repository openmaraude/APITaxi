# -*- coding: utf-8 -*-
from flask.ext.restplus import Resource
from flask import jsonify
class ResourceMetadata(Resource):
    def metadata(self):
        total_result = self.model.query.count()
        meta = {'total_result': total_result}
        return jsonify(meta)
