class TestStats:

    def test_stats_taxis(self, admin):
        resp = admin.client.get('/stats/taxis')
        assert resp.status_code == 200

    def test_stats_taxis(self, admin):
        resp = admin.client.get('/stats/hails')
        assert resp.status_code == 200
