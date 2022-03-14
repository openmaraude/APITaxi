from APITaxi_models2.unittest.factories import UserFactory


class TestUsersDetails:
    def test_invalid(self, anonymous, admin, operateur, moteur):
        user = UserFactory()

        # user id is not an integer, route is not found
        resp = anonymous.client.get('/users/xxx')
        assert resp.status_code == 404

        # Login required
        resp = anonymous.client.get('/users/999')
        assert resp.status_code == 401

        for role in (operateur, moteur):
            # User does not exist
            resp = role.client.get('/users/999')
            assert resp.status_code == 404

            # User exists but client is not the owner
            resp = role.client.get('/users/%s' % user.id)
            assert resp.status_code == 403

        # 404
        resp = admin.client.get('/users/999')
        assert resp.status_code == 404

    def test_ok(self, operateur, QueriesTracker):
        with QueriesTracker() as qtrack:
            resp = operateur.client.get('/users/%d' % operateur.user.id)
            # SELECT for permissions, SELECT users
            assert qtrack.count == 2

        assert resp.status_code == 200

    def test_admin(self, admin):
        user = UserFactory(commercial_name='Bob Dylan')
        resp = admin.client.get('/users/%d' % user.id)
        assert resp.status_code == 200
        assert resp.json['data'][0]['name'] == 'Bob Dylan'


class TestUsersPut:
    def test_ok(self, operateur):
        original_password = operateur.user.password

        # Empty payload is a no op
        resp = operateur.client.put('/users/%s' % operateur.user.id, json={})
        assert resp.status_code == 200

        # If data is provided, it must have one element.
        resp = operateur.client.put('/users/%s' % operateur.user.id, json={'data': []})
        assert resp.status_code == 400

        # No op
        resp = operateur.client.put('/users/%s' % operateur.user.id, json={'data': [{}]})
        assert resp.status_code == 200

        # If password is empty, it is not changed.
        resp = operateur.client.put('/users/%s' % operateur.user.id, json={'data': [{
            'password': ''
        }]})
        assert resp.status_code == 200
        assert operateur.user.password == original_password

        # Password too short.
        resp = operateur.client.put('/users/%s' % operateur.user.id, json={'data': [{
            'password': 'abc'
        }]})
        assert resp.status_code == 400

        # Password changed.
        resp = operateur.client.put('/users/%s' % operateur.user.id, json={'data': [{
            'password': 'abcdefghi'
        }]})
        assert resp.status_code == 200
        assert operateur.user.password != original_password

        # Email and API key can *not* be changed, they are ignored.
        resp = operateur.client.put('/users/%s' % operateur.user.id, json={'data': [{
            'email': 'xxx',
            'apikey': 'yyy',
        }]})
        assert resp.status_code == 200
        assert operateur.user.email != 'xxx'
        assert operateur.user.apikey != 'yyy'

        # Null values accepted for strings but not stored as is
        resp = operateur.client.put('/users/%s' % operateur.user.id, json={'data': [{
            'name': None,
            'email_customer': None,
            'email_technical': None,
            'operator_api_key': None,
            'operator_header_name': None,
            'phone_number_customer': None,
            'phone_number_technical': None,
            'hail_endpoint_production': None,
        }]})
        assert resp.status_code == 200
        assert operateur.user.commercial_name == ''
        assert operateur.user.email_customer == ''
        assert operateur.user.email_technical == ''
        assert operateur.user.operator_api_key == ''
        assert operateur.user.operator_header_name == ''
        assert operateur.user.phone_number_customer == ''
        assert operateur.user.phone_number_technical == ''
        assert operateur.user.hail_endpoint_production == ''

        # Other fields can be updated.
        resp = operateur.client.put('/users/%s' % operateur.user.id, json={'data': [{
            'name': 'New commercial name',
            'email_customer': 'new email customer',
            'email_technical': 'new email technical',
            'hail_endpoint_production': 'new hail endpoint production',
            'phone_number_customer': 'new phone number customer',
            'phone_number_technical': 'new phone number technical',
            'operator_api_key': 'new operator api key',
            'operator_header_name': 'new operator header name',
        }]})
        assert resp.status_code == 200, resp.json
        assert operateur.user.commercial_name == 'New commercial name'
        assert operateur.user.email_customer == 'new email customer'
        assert operateur.user.email_technical == 'new email technical'
        assert operateur.user.hail_endpoint_production == 'new hail endpoint production'
        assert operateur.user.phone_number_customer == 'new phone number customer'
        assert operateur.user.phone_number_technical == 'new phone number technical'
        assert operateur.user.operator_api_key == 'new operator api key'
        assert operateur.user.operator_header_name == 'new operator header name'

    def test_endpoint(self, operateur, app):
        app.debug = False  # Reproduce production conditions, tested to be local to this test
        for endpoint, expected in [
            ('foobar', 400),
            ('http://example.com', 200),
            ('http://localhost', 400),
            ('http://127.0.0.1', 400),
            ('', 200)
        ]:
            resp = operateur.client.put('/users/%s' % operateur.user.id, json={'data': [{
                'hail_endpoint_production': endpoint
            }]})
            assert resp.status_code == expected, endpoint

    def test_invalid_header(self, operateur):
        resp = operateur.client.put(f'/users/{operateur.user.id}', json={'data': [{
            'operator_header_name': "X-API-KEY: AB-12-CD-34",
        }]})
        assert resp.status_code == 400, resp.json
        assert list(resp.json['errors']['data']['0']) == ['operator_header_name']

        resp = operateur.client.put(f'/users/{operateur.user.id}', json={'data': [{
            'operator_api_key': "\nthis\tis\rvery\nwrong",
        }]})
        assert resp.status_code == 400, resp.json
        assert list(resp.json['errors']['data']['0']) == ['operator_api_key']

        resp = operateur.client.put(f'/users/{operateur.user.id}', json={'data': [{
            'operator_header_name': "Düsseldorf",
        }]})
        assert resp.status_code == 400, resp.json
        assert list(resp.json['errors']['data']['0']) == ['operator_header_name']

        # Empty string not validated
        resp = operateur.client.put(f'/users/{operateur.user.id}', json={'data': [{
            'operator_header_name': "",
            'operator_api_key': "",
        }]})
        assert resp.status_code == 200, resp.json


class TestUsersList:
    def test_invalid(self, anonymous):
        # Authentication required
        resp = anonymous.client.get('/users')
        assert resp.status_code == 401

    def test_ok(self, admin, operateur, QueriesTracker):
        user2 = UserFactory(commercial_name='user2')
        user3 = UserFactory(commercial_name='user3')

        # Four users: admin, operateur, user2, user3
        with QueriesTracker() as qtracker:
            resp = admin.client.get('/users')
            assert resp.status_code == 200

            assert resp.json['data'][0]['email'] == admin.user.email
            assert resp.json['data'][1]['email'] == operateur.user.email
            assert resp.json['data'][2]['email'] == user2.email
            assert resp.json['data'][3]['email'] == user3.email

            assert qtracker.count == 3

        # Filter on email
        resp = admin.client.get('/users?email=%s' % user2.email)
        assert resp.status_code == 200
        assert len(resp.json['data']) == 1
        assert resp.json['data'][0]['email'] == user2.email

        # Filter on commercial name
        resp = admin.client.get('/users?name=%s' % user2.commercial_name)
        assert resp.status_code == 200
        assert len(resp.json['data']) == 1
        assert resp.json['data'][0]['email'] == user2.email

        # Operateur is not administrator, it sees only the accounts it manages.
        resp = operateur.client.get('/users')
        assert resp.status_code == 200
        assert len(resp.json['data']) == 0

        # Operateur becomes manager of user2 and user3.
        user2.manager = operateur.user
        user3.manager = operateur.user

        resp = operateur.client.get('/users')
        assert resp.status_code == 200
        assert len(resp.json['data']) == 2
