from APITaxi_models2.unittest.factories import UserFactory


class TestUsersDetails:
    def test_invalid(self, anonymous, admin, operateur, moteur):
        # user id is not an integer, route is not found
        resp = anonymous.client.get('/users/xxx')
        assert resp.status_code == 404

        # Login required
        resp = anonymous.client.get('/users/999')
        assert resp.status_code == 401

        # Permission denied
        for role in (operateur, moteur):
            resp = role.client.get('/users/999')
            assert resp.status_code == 403

        # 404
        resp = admin.client.get('/users/999')
        assert resp.status_code == 404

    def test_ok(self, admin, QueriesTracker):
        user = UserFactory(commercial_name='Bob Dylan')

        with QueriesTracker() as qtrack:
            resp = admin.client.get('/users/%d' % user.id)
            # SELECT for permissions, SELECT users
            assert qtrack.count == 2

        assert resp.status_code == 200
        assert resp.json['data'][0]['name'] == 'Bob Dylan'


class TestUsersList:
    def test_invalid(self, anonymous, operateur, moteur):
        # Authentication required
        resp = anonymous.client.get('/users')
        assert resp.status_code == 401

        # Not enough permissions
        for role in (operateur, moteur):
            resp = role.client.get('/users')
            assert resp.status_code == 403

    def test_ok(self, admin, QueriesTracker):
        user2 = UserFactory()
        user3 = UserFactory()

        # Three users: admin, user2, user3
        with QueriesTracker() as qtrack:
            resp = admin.client.get('/users')
            assert resp.status_code == 200
            for user in (admin.user, user2, user3):
                assert {
                    'email': user.email,
                    'apikey': user.apikey
                } in resp.json['data']

            assert qtrack.count == 2
