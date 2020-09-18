from flask import abort

from flask_security import login_required, roles_accepted


def test_content_type(anonymous):
    for req in ('post', 'put', 'patch'):
        # Edition request, but content-type not set
        resp = getattr(anonymous.client, req)('/whatever')
        assert resp.status_code == 400
        assert 'content-type' in resp.json['errors'][''][0].lower()

        # Edition request, content-type OK but no data
        resp = getattr(anonymous.client, req)('/whatever', headers={
            'Content-Type': 'application/json'
        })
        assert resp.status_code == 400
        assert 'valid json' in resp.json['errors'][''][0].lower()

        # Edition request, content-type OK but data not valid JSON
        resp = getattr(anonymous.client, req)('/whatever', data='{{{{', headers={
            'Content-Type': 'application/json'
        })
        assert resp.status_code == 400
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
    assert resp.json['errors'][''][0] == 'The header X-Api-Key is required.'

    # Login required, invalid X-Api-Key
    resp = anonymous.client.get('/login_401', headers={'X-Api-Key': 'xxx'})
    assert resp.status_code == 401
    assert len(resp.json['errors'].get('', [])) == 1
    assert resp.json['errors'][''][0] == 'The X-Api-Key provided is not valid.'

    # HTTP/500 for uncaught exception
    resp = anonymous.client.get('/error_500')
    assert resp.status_code == 500
    assert len(resp.json['errors'].get('', [])) == 1
    assert 'Internal server error' in resp.json['errors'][''][0]
