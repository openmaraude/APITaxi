from APITaxi_models2.unittest.factories import HailFactory


class TestGetHailDetails:
    def test_invalid(self, anonymous, operateur, moteur):
        # Login required
        resp = anonymous.client.get('/hails/xxx')
        assert resp.status_code == 401

        # Hail does not exist
        resp = operateur.client.get('/hails/xxxx')
        assert resp.status_code == 404

        # User making the query is not the hail's moteur or operateur.
        hail = HailFactory()
        resp = operateur.client.get('/hails/%s' % hail.id)
        assert resp.status_code == 403

    def test_ok(self, app, operateur, moteur):
        # Hail exists and user is the moteur
        hail = HailFactory(added_by=moteur.user)
        resp = moteur.client.get('/hails/%s' % hail.id)
        assert resp.status_code == 200

        # Hail exists and user is the operateur
        hail = HailFactory(operateur=operateur.user)
        resp = operateur.client.get('/hails/%s' % hail.id)
        assert resp.status_code == 200

        # Position exists in redis and hail is in progress: location is returned
        hail = HailFactory(status='customer_on_board', added_by=moteur.user, operateur=operateur.user)
        app.redis.hset(
            'taxi:%s' % hail.taxi.id,
            hail.added_by.email,
            '1589567716 48.84 2.35 free phone 2'
        )
        resp = moteur.client.get('/hails/%s' % hail.id)
        assert resp.status_code == 200
        assert resp.json['data'][0]['taxi']['crowfly_distance']
        assert resp.json['data'][0]['taxi']['last_update']
        assert resp.json['data'][0]['taxi']['position']['lon']
        assert resp.json['data'][0]['taxi']['position']['lat']

        # Position exists in redis and hail is finished: location is not returned
        hail = HailFactory(status='finished', added_by=moteur.user, operateur=operateur.user)
        app.redis.hset(
            'taxi:%s' % hail.taxi.id,
            hail.added_by.email,
            '1589567716 48.84 2.35 free phone 2'
        )
        resp = moteur.client.get('/hails/%s' % hail.id)
        assert resp.status_code == 200
        assert not resp.json['data'][0]['taxi']['crowfly_distance']
        assert not resp.json['data'][0]['taxi']['last_update']
        assert not resp.json['data'][0]['taxi']['position']['lon']
        assert not resp.json['data'][0]['taxi']['position']['lat']
