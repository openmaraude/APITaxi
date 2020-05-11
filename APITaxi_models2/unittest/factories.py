import datetime

import factory

from APITaxi_models2 import (
    db,
    ADS,
    Customer,
    Departement,
    Driver,
    Hail,
    Taxi,
    User,
    Role,
    RolesUsers,
    Vehicle,
    ZUPC
)


class BaseFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        sqlalchemy_session = db.session
        # Call session.flush() when object is created.
        sqlalchemy_session_persistence = 'flush'


class RoleFactory(BaseFactory):
    class Meta:
        model = Role

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """Get Role, or create it if it doesn't exist."""
        session = cls._meta.sqlalchemy_session
        obj = session.query(Role).filter_by(name=kwargs['name']).one_or_none()
        if not obj:
            obj = super(RoleFactory, cls)._create(model_class, *args, **kwargs)
        return obj


class UserFactory(BaseFactory):
    class Meta:
        model = User

    email = factory.Sequence(lambda n: 'test_user_%d' % n)
    password = 'super_password'
    active = True
    confirmed_at = datetime.datetime(2015, 12, 1, 13, 37)
    apikey = factory.Sequence(lambda n: 'API_KEY_%d' % n)


class RolesUsersFactory(BaseFactory):
    class Meta:
        model = RolesUsers


class CustomerFactory(BaseFactory):
    class Meta:
        model = Customer

    id = factory.Sequence(lambda n: 'CUSTOMER_%d' % n)
    moteur = factory.SubFactory(UserFactory)
    added_by = factory.SubFactory(UserFactory)
    added_via = 'api'
    source = 'added_by'
    phone_number = factory.Sequence(lambda n: '+336%09d' % n)


class DepartementFactory(BaseFactory):
    class Meta:
        model = Departement

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """Get Department, or create it if it doesn't exist."""
        session = cls._meta.sqlalchemy_session
        obj = session.query(Departement).filter_by(numero=kwargs['numero']).one_or_none()
        if not obj:
            obj = super(DepartementFactory, cls)._create(model_class, *args, **kwargs)
        return obj

    nom = factory.Sequence(lambda n: 'DEPARTEMENT_%d' % n)
    numero = factory.Sequence(lambda n: '%d' % n)


class ZUPCFactory(BaseFactory):
    class Meta:
        model = ZUPC

    departement = factory.SubFactory(DepartementFactory)
    nom = 'Paris'
    insee = '75101'
    # Not really the shape of Paris
    shape = 'MULTIPOLYGON(((0 0,4 0,4 4,0 4,0 0),(1 1,2 1,2 2,1 2,1 1)), ((-1 -1,-1 -2,-2 -2,-2 -1,-1 -1)))'
    active = True


class ADSFactory(BaseFactory):
    class Meta:
        model = ADS

    numero = factory.Sequence(lambda n: 'ads_number_%d' % n)
    insee = '75101'
    owner_type = 'individual'
    owner_name = 'Owner ADS'
    category = ''
    zupc_id = factory.SubFactory(ZUPCFactory)


class DriverFactory(BaseFactory):
    class Meta:
        model = Driver

    last_name = factory.Sequence(lambda n: 'Dupont %d' % n)
    first_name = 'Jean'
    birth_date = datetime.date(1978, 1, 11)
    professional_licence = factory.Sequence(lambda n: 'LICENCE_PRO_%d' % n)
    departement = factory.SubFactory(DepartementFactory)
    added_via = 'api'
    source = 'added_by'


class VehicleFactory(BaseFactory):
    class Meta:
        model = Vehicle

    licence_plate = factory.Sequence(lambda n: "Licence plate %d" % n)


class TaxiFactory(BaseFactory):
    class Meta:
        model = Taxi

    @factory.lazy_attribute
    def vehicle(self):
        vehicle = VehicleFactory()
        db.session.flush()
        return {
            'licence_plate': vehicle.licence_plate
        }

    @factory.lazy_attribute
    def ads(self):
        ads = ADSFactory()
        db.session.flush()
        return {
            'numero': ads.numero,
            'insee': ads.insee
        }

    @factory.lazy_attribute
    def driver(self):
        departement = DepartementFactory()
        driver = DriverFactory()
        db.session.flush()
        return {
            'departement': departement.numero,
            'professional_licence': driver.professional_licence

        }


class HailFactory(BaseFactory):
    class Meta:
        model = Hail

    operateur_id = factory.SubFactory(UserFactory)
    customer_lon = 2.308620
    customer_lat = 48.850690
    customer_address = '20 Avenue de Ségur, 75007 Paris'
    customer_phone_number = '0799100222'
    taxi_id = factory.SubFactory(TaxiFactory)
    status = 'received'

