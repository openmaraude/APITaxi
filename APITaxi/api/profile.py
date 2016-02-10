#coding: utf-8
from . import ns_administrative, api
from flask.ext.restplus import Resource, abort
from ..extensions import user_datastore

@ns_administrative.route('users/<int:user_id>')
class ProfileDetail(Resource):
    @api.marshal_with(model_user)
    def get(self, user_id):
        user = user_datastore.get_user(user_id)
        if not user:
            abort(404, message="Unable to find user")
        return {"data": [user]}, 200
