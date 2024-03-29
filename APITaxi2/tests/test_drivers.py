from unittest import mock

import psycopg2.errors

from APITaxi_models2 import db, Driver
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

        driver = DriverFactory(added_by=operateur.user)
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
        assert resp.status_code == 201
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

            # SELECT permissions, INSERT LOG, SELECT departement, SELECT driver (to check
            # if exists), INSERT driver
            assert qtracker.count == 5

        assert resp.status_code == 201
        assert Driver.query.count() == 1

    def test_mispelled_departement(self, operateur):
        """If departement numero is correct but not the name, request should
        still succeed."""
        departement = DepartementFactory()

        resp = operateur.client.post('/drivers', json={'data': [{
            'first_name': 'Evander',
            'last_name': 'Holyfield',
            'professional_licence': 'xxx',
            'departement': {
                'nom': 'xxxxxxxxxxx',
                'numero': departement.numero
            }
        }]})

        assert resp.status_code == 201
        assert Driver.query.count() == 1

    def test_duplicates_departement(self, operateur):
        """We specify a valid departement numero and nom, but they refer to two
        different departements.
        """
        departement = DepartementFactory()
        departement2 = DepartementFactory()

        resp = operateur.client.post('/drivers', json={'data': [{
            'first_name': 'Manny',
            'last_name': 'Pacquiao',
            'professional_licence': 'xxx',
            'departement': {
                'nom': departement.nom,
                'numero': departement2.numero
            }
        }]})

        assert resp.status_code == 409  # HTTP/409 Conflict
        assert 'nom' in resp.json['errors']['data']['0']['departement']
        assert 'numero' in resp.json['errors']['data']['0']['departement']

    def test_unique_violation(self, operateur):
        departement = DepartementFactory()

        with mock.patch.object(db.session, 'flush') as patched:
            patched.side_effect = psycopg2.errors.UniqueViolation()
            resp = operateur.client.post('/drivers', json={'data': [{
                'first_name': 'Manny',
                'last_name': 'Pacquiao',
                'professional_licence': 'xxx',
                'departement': {
                    'numero': departement.numero,
                }
            }]})

            assert resp.status_code == 409, resp.json
