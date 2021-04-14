import dateutil

from APITaxi_models2.unittest.factories import (
    CustomerFactory,
    HailFactory,
    UserFactory,
)


class TestSession:
    def test_invalid(self, anonymous, moteur, operateur, admin):
        resp = anonymous.client.get('/sessions')
        assert resp.status_code == 401

        resp = operateur.client.get('/sessions')
        assert resp.status_code == 403

        # Invalid querystring parameters
        resp = admin.client.get('/sessions?x=y')
        assert resp.status_code == 400
        assert 'x' in resp.json['errors']

        resp = moteur.client.get('/sessions?x=y')
        assert resp.status_code == 400
        assert 'x' in resp.json['errors']

    def test_ok(self, admin, moteur, QueriesTracker):
        customer = CustomerFactory(added_by=moteur.user)

        other_user = UserFactory()
        other_customer = CustomerFactory(added_by=other_user)

        # Hail 1
        hail_1 = HailFactory(
            customer=customer,
            added_by=moteur.user,
            status='finished'
        )

        # Hail 2, same session id than hail 1
        hail_2 = HailFactory(
            customer=customer,
            added_by=moteur.user,
            status='customer_on_board',
            session_id=hail_1.session_id
        )

        # Hail 3, different session id
        hail_3 = HailFactory(
            customer=other_customer,
            added_by=other_user,
            status='failure'
        )

        with QueriesTracker() as qtracker:
            resp = admin.client.get('/sessions')
            # SELECT permissions
            # Pagination, select query
            assert qtracker.count == 3

        assert resp.status_code == 200
        assert len(resp.json['data']) == 2

        # First entry is the last hail created
        assert len(resp.json['data'][0]['hails']) == 1
        assert dateutil.parser.parse(resp.json['data'][0]['added_at']) == hail_3.added_at

        # Second entry contains the infos of hail and hail_2
        assert len(resp.json['data'][1]['hails']) == 2
        assert dateutil.parser.parse(resp.json['data'][1]['added_at']) == hail_1.added_at
        assert dateutil.parser.parse(resp.json['data'][1]['hails'][0]['added_at']) == hail_1.added_at
        assert dateutil.parser.parse(resp.json['data'][1]['hails'][1]['added_at']) == hail_2.added_at

        # Moteurs can only view sessions they created.
        resp = moteur.client.get('/sessions')
        assert resp.status_code == 200
        assert len(resp.json['data']) == 1
