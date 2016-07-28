# -*- coding: utf-8 -*-
from ..api import api
from flask_restplus import Resource
from flask_security import login_required, roles_required
from APITaxi_models.security import User

ns_users = api.namespace('users', description="Users API")

@ns_users.route('/', endpoint='users_lists')
class UsersResource(Resource):

    @login_required
    @roles_required('admin')
    def get(self):
        return {"data": [{"name": u.email, "apikey": u.apikey} for u in User.query.all()]}
