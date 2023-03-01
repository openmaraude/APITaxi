from APITaxi_models2.unittest.factories import CustomerFactory


class TestEditCustomers:
    def test_invalid(self, anonymous, operateur, moteur):
        # Login required
        resp = anonymous.client.put('/customers/xxx', json={})
        assert resp.status_code == 401

        # Permission denied
        resp = operateur.client.put('/customers/xxx', json={})
        assert resp.status_code == 403

        # No data
        resp = moteur.client.put('/customers/xxx', json={})
        assert resp.status_code == 400
        assert 'data' in resp.json['errors']

        # Empty data
        resp = moteur.client.put('/customers/xxx', json={'data': []})
        assert resp.status_code == 400
        assert 'data' in resp.json['errors']

        # Invalid types
        resp = moteur.client.put('/customers/xxx', json={'data': [{
            'reprieve_begin': 'xxx',
            'reprieve_end': 'xxx',
            'ban_begin': 'xxx',
            'ban_end': 'xxx'
        }]})
        assert resp.status_code == 400
        for field in (
            'reprieve_begin', 'reprieve_end',
            'ban_begin', 'ban_end'
        ):
            assert field in resp.json['errors'].get('data', {}).get('0', {})

        # Data ok, but invalid client
        resp = moteur.client.put('/customers/xxx', json={'data': [{}]})
        assert resp.status_code == 404
        assert 'url' in resp.json['errors']

    def test_edit(self, moteur, QueriesTracker):
        customer = CustomerFactory(added_by=moteur.user)

        # Empty
        with QueriesTracker() as qtrack:
            resp = moteur.client.put('/customers/%s' % customer.id, json={
                'data': [{
                    'reprieve_begin': '2001-01-01 01:01:01',
                    'reprieve_end': '2002-02-02 02:02:02',
                    'ban_begin': '2003-03-03 03:03:03',
                    'ban_end': '2004-04-04 04:04:04'
                }]
            })
            # SELECT permissions, INSERT LOG, SELECT customer, UPDATE customer
            assert qtrack.count == 4

        assert resp.status_code == 200
        assert customer.reprieve_begin.year == 2001
        assert customer.reprieve_end.year == 2002
        assert customer.ban_begin.year == 2003
        assert customer.ban_end.year == 2004
