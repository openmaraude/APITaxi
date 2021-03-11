import apispec
from flask import abort

from flask_security import current_user, login_required, roles_accepted

from APITaxi_models2.unittest.factories import UserFactory


def test_content_type(anonymous):
    for req in ('post', 'put', 'patch'):
        # Edition request, but content-type not set. It is set by middleware.
        resp = getattr(anonymous.client, req)('/whatever')
        assert resp.status_code == 400
        assert 'content-type' not in resp.json['errors'][''][0].lower()

        # Edition request, content-type contains a charset.
        resp = getattr(anonymous.client, req)('/whatever', headers={
            'Content-Type': 'application/json; charset=utf-8'
        })
        assert resp.status_code == 400
        assert 'content-type' not in resp.json['errors'][''][0].lower()

        # Edition request, invalid content-type.
        resp = getattr(anonymous.client, req)('/whatever', headers={
            'Content-Type': 'text/html'
        })
        assert resp.status_code == 400
        assert 'content-type' in resp.json['errors'][''][0].lower()

        # Edition request, content-type OK but no data
        resp = getattr(anonymous.client, req)('/whatever', headers={
            'Content-Type': 'application/json'
        })
        assert resp.status_code == 400
        assert 'content-type' not in resp.json['errors'][''][0].lower()
        assert 'valid json' in resp.json['errors'][''][0].lower()

        # Edition request, content-type OK but data not valid JSON
        resp = getattr(anonymous.client, req)('/whatever', data='{{{{', headers={
            'Content-Type': 'application/json'
        })
        assert resp.status_code == 400
        assert 'content-type' not in resp.json['errors'][''][0].lower()
        assert 'valid json' in resp.json['errors'][''][0].lower()


def test_errors_handlers(app, anonymous):
    @app.route('/abort_403')
    def abort_403():
        abort(403)

    @app.route('/roles_403')
    @roles_accepted('xxxx')
    def roles_403():
        return ''

    @app.route('/login_401')
    @login_required
    def login_401():
        return ''

    @app.route('/error_500')
    def error_500():
        abort(500)

    @app.route('/edit')
    def edit():
        return 'ok'

    @app.route('/get_only', methods=['GET'])
    def get_only():
        return 'ok'

    # Request for view calling flask.abort(403)
    resp = anonymous.client.get('/abort_403')
    assert resp.status_code == 403
    assert len(resp.json['errors'].get('', [])) == 1
    assert 'permissions' in resp.json['errors'][''][0]

    # Request for view with not enough permissions
    resp = anonymous.client.get('/roles_403')
    assert resp.status_code == 403
    assert len(resp.json['errors'].get('', [])) == 1
    assert 'permissions' in resp.json['errors'][''][0]

    # Request for non-existing view
    resp = anonymous.client.get('/doesnotexist')
    assert resp.status_code == 404
    assert len(resp.json['errors'].get('url', [])) == 1
    assert 'not found' in resp.json['errors']['url'][0]

    # Login required, X-Api-Key not provided
    resp = anonymous.client.get('/login_401')
    assert resp.status_code == 401
    assert len(resp.json['errors'].get('', [])) == 1
    assert resp.json['errors'][''][0] == 'Header X-Api-Key required.'

    # Login required, invalid X-Api-Key
    resp = anonymous.client.get('/login_401', headers={'X-Api-Key': 'xxx'})
    assert resp.status_code == 401
    assert len(resp.json['errors'].get('', [])) == 1
    assert resp.json['errors'][''][0] == 'Header X-Api-Key not valid.'

    # HTTP/405 invalid method type
    resp = anonymous.client.post('/get_only', json={})
    assert resp.status_code == 405
    assert len(resp.json['errors']['url']) == 1

    # HTTP/500 for uncaught exception
    resp = anonymous.client.get('/error_500')
    assert resp.status_code == 500
    assert len(resp.json['errors'].get('', [])) == 1
    assert 'Internal server error' in resp.json['errors'][''][0]


def test_logas(app, admin, operateur):
    """User can set X-Logas with the email of the account to login. User needs
    to be administrator or the manager of the logas account."""

    @app.route('/', methods=['GET'])
    @login_required
    def root():
        return {'user': current_user.email}

    resp = admin.client.get('/')
    assert resp.status_code == 200
    assert resp.json['user'] == admin.user.email

    resp = operateur.client.get('/')
    assert resp.status_code == 200
    assert resp.json['user'] == operateur.user.email

    resp = admin.client.get('/', headers={'X-Logas': operateur.user.email})
    assert resp.status_code == 200
    assert resp.json['user'] == operateur.user.email

    resp = operateur.client.get('/', headers={'X-Logas': admin.user.email})
    assert resp.status_code == 401
    assert resp.json['errors'][''][0] == 'Header X-Api-Key and/or X-Logas not valid.'

    new_user = UserFactory(manager=operateur.user)

    resp = operateur.client.get('/', headers={'X-Logas': new_user.email})
    assert resp.status_code == 200


def test_api_spec(app):
    """Ensure swagger documentation follows openapi specifications."""
    apispec.utils.validate_spec(app.apispec)
