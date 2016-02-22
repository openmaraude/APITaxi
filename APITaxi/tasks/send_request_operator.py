#coding: utf-8
from flask import current_app
from flask.ext.restplus import marshal
from APITaxi_models.hail import Hail
from ..descriptors.hail import hail_model
from ..extensions import celery
import requests, json

@celery.task()
def send_request_operator(hail_id, endpoint, operator_header_name,
        operator_api_key, operator_email):
    hail = Hail.cache.get(hail_id)
    if not hail:
        current_app.logger.error('Unable to find hail: {}'.format(hail_id))
        return False

    r = None
    try:
        headers = {'Content-Type': 'application/json',
                   'Accept': 'application/json'}
        if operator_header_name is not None and operator_header_name != '':
            headers[operator_header_name] = operator_api_key
        r = requests.post(endpoint,
                data=json.dumps(marshal({"data": [hail]}, hail_model)),
                headers=headers
        )
    except requests.exceptions.MissingSchema:
        pass
    if not r or r.status_code < 200 or r.status_code >= 300:
        hail.status = 'failure'
        current_app.extensions['sqlalchemy'].db.session.commit()
        current_app.logger.error("Unable to reach hail's endpoint {} of operator {}"\
            .format(endpoint, operator_email))
        return False
    r_json = None
    try:
        r_json = r.json()
    except ValueError:
        pass

    if r_json and 'data' in r_json and len(r_json['data']) == 1\
            and 'taxi_phone_number' in r_json['data'][0]:
        hail.taxi_phone_number = r_json['data'][0]['taxi_phone_number']

    hail.status = 'received_by_operator'
    current_app.extensions['sqlalchemy'].db.session.commit()
    return True
