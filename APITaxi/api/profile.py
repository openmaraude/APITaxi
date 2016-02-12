#coding: utf-8
from . import ns_administrative, api
from flask.ext.restplus import Resource, abort, fields as basefields
from APITaxi_utils import fields
from ..extensions import user_datastore

class LogoHref(basefields.Raw):
    def output(self, key, obj):
        return url_for('profile.image', user_id=obj.user_id, src=obj.id)

model_user = api.model("user", {
    'data': fields.List(fields.Nested(
        api.model("user_model",
            {
                "name": fields.String(attribute='commercial_name'),
                "logos": fields.List(fields.Nested(
                    api.model('logo_model', 
                        {'href': LogoHref,
                         'size' : fields.String,
                         'format': fields.String(attribute='format_'),
                        }
                        )
                    ))
            }
        )))
    })

@ns_administrative.route('users/<int:user_id>')
class ProfileDetail(Resource):
    @api.marshal_with(model_user)
    def get(self, user_id):
        user = user_datastore.get_user(user_id)
        if not user:
            abort(404, message="Unable to find user")
        return {"data": [user]}, 200
