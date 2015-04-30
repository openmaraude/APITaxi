from .skeleton import Skeleton
from APITaxi.models.taxis import Driver
from APITaxi.models.administrative import Departement
from json import dumps, loads
from copy import deepcopy
from APITaxi import db


class TestDriverPost(Skeleton):
    url = '/drivers/'
    dict_ = {
        "last_name" : "last name",
        "first_name" : "first name",
        "birth_date" : "1980-03-03",
        "professional_licence" :  "ppkkpp",
        "departement" : "53"
    }

    def init_dep(self):
        dep = Departement()
        dep.nom = "Mayenne"
        dep.numero = "53"
        db.session.add(dep)
        db.session.commit()

    def test_null(self):
        r = self.post([])
        self.assert200(r)

    def test_simple(self):
        self.init_dep()
        dict_ = deepcopy(self.__class__.dict_)
        r = self.post([dict_])
        self.assert200(r)
        json = loads(r.data)
        self.check_req_vs_dict(json['data'][0], dict_)
        self.assertEqual(len(Driver.query.all()), 1)

    def test_no_data(self):
        self.init_dep()
        r = self.post({}, envelope_data=False)
        self.assert400(r)
        self.assertEqual(len(Driver.query.all()), 0)

    def test_too_many_drivers(self):
        self.init_dep()
        r = self.post([self.__class__.dict_ for x in xrange(0, 251)])
        self.assertEqual(r.status_code, 413)
        self.assertEqual(len(Driver.query.all()), 0)

    def test_no_departement(self):
        r = self.post([self.__class__.dict_])
        self.assert400(r)
        self.assertEqual(len(Driver.query.all()), 0)

    def test_pas_de_nom(self):
        dict_ = deepcopy(self.__class__.dict_)
        del dict_['first_name']
        r = self.post([dict_])
        self.assert400(r)
        self.assertEqual(len(Driver.query.all()), 0)

    def test_two_inserts(self):
        self.init_dep()
        r = self.post([self.__class__.dict_ for x in xrange(0, 2)])
        self.assert200(r)
        self.assertEqual(len(Driver.query.all()), 2)




