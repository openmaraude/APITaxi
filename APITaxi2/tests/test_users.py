from APITaxi_models2.unittest.factories import UserFactory


class TestGetCustomers:
    def test_get_invalid(self, anonymous, admin, operateur, moteur):
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


    def test_get(self, admin):
        user = UserFactory(commercial_name='Bob Dylan')

        resp = admin.client.get('/users/%d' % user.id)
        assert resp.status_code == 200
        assert resp.json['data'][0]['name'] == 'Bob Dylan'
