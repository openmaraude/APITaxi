class TestInternalAuth:
    def test_invalid(self, anonymous, moteur):
        resp = anonymous.client.post('/internal/auth', json={'data': [{}]})
        assert resp.status_code == 400
        assert 'email' in resp.json['errors']['data']['0']

        # Should specify either apikey or password
        resp = anonymous.client.post('/internal/auth', json={'data': [{
            'email': 'xxx',
        }]})
        assert resp.status_code == 400

        # Specify both password and apikey
        resp = anonymous.client.post('/internal/auth', json={'data': [{
            'email': 'xxx',
            'apikey': 'xxx',
            'password': 'xxx',
        }]})
        assert resp.status_code == 400

        # Invalid password
        resp = moteur.client.post('/internal/auth', json={'data': [{
            'email': moteur.user.email,
            'password': moteur.user.password + '_invalid'
        }]})
        assert resp.status_code == 401

        # Invalid api key
        resp = moteur.client.post('/internal/auth', json={'data': [{
            'email': moteur.user.email,
            'apikey': moteur.user.apikey + '_invalid'
        }]})
        assert resp.status_code == 401

    def test_ok(self, moteur, QueriesTracker):
        with QueriesTracker() as qtracker:
            resp = moteur.client.post('/internal/auth', json={'data': [{
                'email': moteur.user.email,
                'password': moteur.user.password,
            }]})
            # SELECT permissions, INSERT LOG (auth_apikey), SELECT user, INSERT LOG (login_password)
            assert qtracker.count == 4
        assert resp.status_code == 200

        resp = moteur.client.post('/internal/auth', json={'data': [{
            'email': moteur.user.email,
            'apikey': moteur.user.apikey,
        }]})
        assert resp.status_code == 200
