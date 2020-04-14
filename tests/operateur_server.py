""" This simple API simulates a simple operateur API useful for tests.

Context:

Our unittests are run with circleci. Tests from hail_tests.py create hails,
which generate tasks executed by the worker running in background. The worker
needs to query an operateur API.

Refer to .circleci/config.yml to get the commands executed to run the
background worker and this API.

Note: We should probably mock everything instead. With such complicated setup,
it is impossible to run unittests locally, outside of circleci.
"""


from flask import Flask, request, abort, current_app, g
from flask_restplus import Api, Resource

app = Flask(__name__)
api = Api(app)


class Pong(Resource):
    def post(self):
       for h in request.headers.keys():
           current_app.logger.info("{}: {}".format(h, request.headers.get(h)))
       json = request.get_json()
       if not 'data' in json or len(json['data']) != 1 or 'status' not in json['data'][0]:
           abort(400)
       json['data'][0]['status'] = 'received_by_taxi'
       json['data'][0]['taxi_phone_number'] = 'aaa'
       g.last_hail_id = json['data'][0]['id']
       return json, 201


class PongAPIKEY(Resource):
    def post(self):
       apikey = request.headers.get('X-API-KEY', None)
       if not apikey:
           abort(400)
       if apikey != 'xxx':
            abort(403)
       json = request.get_json()
       if not 'data' in json or len(json['data']) != 1 or 'status' not in json['data'][0]:
           abort(400)
       json['data'][0]['status'] = 'received_by_taxi'
       json['data'][0]['taxi_phone_number'] = 'aaa'
       return json, 201


class PongEmpty(Resource):
    def post(self):
        return {}, 201


class PongEmptyTaxi(Resource):
    def post(self):
        return {'data': [{}]}, 201


api.add_resource(Pong, '/hail/')
api.add_resource(PongAPIKEY, '/hail_apikey/')
api.add_resource(PongEmpty, '/hail_empty/')
api.add_resource(PongEmptyTaxi, '/hail_empty_taxi/')

if __name__ == '__main__':
    app.run(debug=True, port=5001)
