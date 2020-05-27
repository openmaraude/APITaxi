from APITaxi_models2 import Driver
from APITaxi_models2.unittest.factories import DepartementFactory, DriverFactory


class TestDriversCreate:
    def test_invalid(self, anonymous, moteur, operateur):
        # Login required
        resp = anonymous.client.post('/drivers', json={})
        assert resp.status_code == 401

        # Permission denied
        resp = moteur.client.post('/drivers', json={})
        assert resp.status_code == 403

        # Permissions OK, check required fields
        resp = operateur.client.post('/drivers', json={'data': [{
        }]})
        assert resp.status_code == 400
        assert 'departement' in resp.json['errors']['data']['0']
        assert 'first_name' in resp.json['errors']['data']['0']
        assert 'last_name' in resp.json['errors']['data']['0']
        assert 'professional_licence' in resp.json['errors']['data']['0']

        # Permissions OK, check required fields of departement
        resp = operateur.client.post('/drivers', json={'data': [{
            'departement': {}
        }]})
        assert resp.status_code == 400
        assert 'nom' in resp.json['errors']['data']['0']['departement']

        # Data ok, but invalid departement
        resp = operateur.client.post('/drivers', json={'data': [{
            'first_name': 'Floyd',
            'last_name': 'Mayweather',
            'professional_licence': 'b4d4ss',
            'departement': {
                'nom': 'does not exist',
                'numero': '999'
            }
        }]})
        assert resp.status_code == 404
        assert len(resp.json['errors']['data']['0']['departement']['nom']) > 0
        assert len(resp.json['errors']['data']['0']['departement']['numero']) > 0

    def test_already_exists(self, operateur):
        """POST to an existing driver doesn't create the driver."""
        assert Driver.query.count() == 0

        driver = DriverFactory()
        assert Driver.query.count() == 1

        # Driver already exists, Driver is updated but no new driver created
        resp = operateur.client.post('/drivers', json={'data': [{
            'first_name': driver.first_name,
            'last_name': driver.last_name,
            'professional_licence': driver.professional_licence,
            'departement': {
                'nom': driver.departement.nom,
                'numero': driver.departement.numero
            }
        }]})
        assert resp.status_code == 200
        assert Driver.query.count() == 1

    def test_already_exists_different_departement(self, operateur):
        """Two drivers with same professional_licence id but different
        departements are considered different."""
        assert Driver.query.count() == 0
        driver = DriverFactory()
        assert Driver.query.count() == 1

        other_departement = DepartementFactory()

        # Driver already exists, Driver is updated but no new driver created
        resp = operateur.client.post('/drivers', json={'data': [{
            'first_name': driver.first_name,
            'last_name': driver.last_name,
            'professional_licence': driver.professional_licence,
            'departement': {
                'nom': other_departement.nom
            }
        }]})
        assert resp.status_code == 200
        assert Driver.query.count() == 2

    def test_ok(self, operateur, QueriesTracker):
        departement = DepartementFactory()

        with QueriesTracker() as qtracker:
            resp = operateur.client.post('/drivers', json={'data': [{
                'first_name': 'Mike',
                'last_name': 'Tyson',
                'professional_licence': 'super b4da55',
                'departement': {
                    'nom': departement.nom
                }
            }]})

            # SELECT permissions, SELECT departement, SELECT driver (to check
            # if exists), INSERT driver
            assert qtracker.count == 4

        assert resp.status_code == 200
        assert Driver.query.count() == 1
