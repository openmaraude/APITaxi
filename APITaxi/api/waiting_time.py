from ..extensions import redis_store
from . import api
from ..descriptors.waiting_time import waiting_time_model, waiting_time_response
from APITaxi_utils.reqparse import DataJSONParser
from flask_restplus import Resource
from flask_security import login_required, roles_accepted

ns_waiting_time = api.namespace(
    'waiting_time',
     description='Waiting time at airport'
)

@ns_waiting_time.route('/roissy/', endpoint='waiting_time')
class WaitingTime(Resource):

    @api.expect(waiting_time_model, validate=True)
    @api.marshal_with(waiting_time_response)
    @login_required
    @roles_accepted('aeroport', 'admin')
    def put(self):
        parser = DataJSONParser()
        data = parser.get_data()[0]
        redis_store.hset(
            "waiting_time_roissy",
            "timestamp",
            data["timestamp"]
        )
        redis_store.hset(
            "waiting_time_roissy",
            "waiting_time",
            data["waiting_time"]
        )
        return self.get_data(), 200

    @login_required
    @roles_accepted('aeroport', 'admin', 'operateur', 'moteur')
    @api.marshal_with(waiting_time_response)
    def get(self):
        return self.get_data(), 200

    def get_data(self):
        data = redis_store.hgetall("waiting_time_roissy",)

        return {
            "data":[
                {
                    "waiting_time": data[b"waiting_time"].decode('utf-8'),
                    "timestamp": data[b"timestamp"].decode('utf-8')
                }
            ]
        }
