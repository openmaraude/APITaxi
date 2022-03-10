import datetime
import uuid

import factory

from APITaxi_models2 import (
    db,
    ADS,
    Customer,
    Departement,
    Driver,
    Hail,
    Taxi,
    Town,
    User,
    Role,
    RolesUsers,
    Vehicle,
    VehicleDescription,
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
        sqlalchemy_get_or_create = ['name']


class UserFactory(BaseFactory):
    class Meta:
        model = User
        sqlalchemy_get_or_create = ('email',)

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
    added_at = factory.LazyFunction(datetime.datetime.now)
    added_by = factory.SubFactory(UserFactory)
    added_via = 'api'
    source = 'added_by'
    phone_number = factory.Sequence(lambda n: '+336%09d' % n)


class DepartementFactory(BaseFactory):
    class Meta:
        model = Departement
        sqlalchemy_get_or_create = ['numero']

    nom = factory.Sequence(lambda n: 'DEPARTEMENT_%d' % n)
    numero = factory.Sequence(lambda n: '%02d' % n)


class TownFactory(BaseFactory):
    """Given how SQLAlchemy works, it's better not to access the built object directly,
    because it will contain the raw WKT string below, not the WKB object returned by
    PostgreSQL and expected by our code. Simply put, don't do:

        paris = TownFactory()

    but do:

        TownFactory()

    And do a query if you need the object in your test. I guess it's a matter of reference counting.
    """
    class Meta:
        model = Town
        sqlalchemy_get_or_create = ['insee']

    name = 'Paris'
    insee = '75056'

    # The MUTLIPOLYGON below is a simple square containing Paris. It has been
    # generated with a WKT editor such as:
    #
    # http://arthur-e.github.io/Wicket/sandbox-gmaps3.html
    # https://clydedacruz.github.io/openstreetmap-wkt-playground/
    #
    # To convert a POLYGON (as returned by these editors) to a MULTIPOLYGON (as
    # expected by ZUPC.shape), run the following query from a postgis database:
    #
    # SELECT ST_AsText(ST_Multi(ST_GeomFromText('POLYGON((2.24......))')));
    shape = 'MULTIPOLYGON(((2.24332732355285 48.9066360266329,2.42460173761535 48.9066360266329,2.42460173761535 48.8122203058303,2.24332732355285 48.8122203058303,2.24332732355285 48.9066360266329)))'

    class Params:
        paris = factory.Trait()
        bordeaux = factory.Trait(
            name='Bordeaux',
            insee='33063',
            shape='MULTIPOLYGON(((-0.686737474226045 44.9009485734125,-0.494476732038545 44.9009485734125,-0.494476732038545 44.7826391041975,-0.686737474226045 44.7826391041975,-0.686737474226045 44.9009485734125)))',
        )
        charenton = factory.Trait(
            name='Charenton-le-Pont',
            insee='94018',
            shape='MULTIPOLYGON(((2.40222930908203 48.8296390842375,2.41973876953125 48.8241580560601,2.41939544677734 48.8177721847637,2.40119934082031 48.8211630141963,2.39235877990723 48.8267008756382,2.40222930908203 48.8296390842375)))',
        )


class ZUPCFactory(BaseFactory):
    class Meta:
        model = ZUPC
        sqlalchemy_get_or_create = ['nom']

    nom = 'Paris'

    zupc_id = factory.LazyAttribute(lambda o: str(uuid.uuid4()))
    allowed = factory.LazyAttribute(lambda o: [TownFactory(), TownFactory(charenton=True)])

    class Params:
        bordeaux = factory.Trait(
            nom='Bordeaux',
            allowed=factory.LazyAttribute(lambda o: [TownFactory(bordeaux=True)])
        )


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


class VehicleDescriptionFactory(BaseFactory):
    class Meta:
        model = VehicleDescription

    # Circular dependencies require to provide the full import path of the
    # target.
    vehicle = factory.SubFactory(__name__ + '.VehicleFactory')
    constructor = 'Citroën'
    model = 'C4 PICASSO'
    added_at = factory.LazyFunction(datetime.datetime.now)
    added_by = factory.SubFactory(UserFactory)
    added_via = 'api'
    source = 'added_by'
    status = 'free'


class VehicleFactory(BaseFactory):
    class Meta:
        model = Vehicle

    licence_plate = factory.Sequence(lambda n: "AB-%03d-CD" % n)

    @factory.post_generation
    def descriptions(self, create, extracted, **kwargs):
        """Create a VehicleDescription for this Vehicle."""
        if not create or extracted is not None:
            return extracted
        return [VehicleDescriptionFactory(vehicle=self, **kwargs)]


class ADSFactory(BaseFactory):
    class Meta:
        model = ADS

    numero = factory.Sequence(lambda n: 'ads_number_%d' % n)
    added_at = factory.LazyFunction(datetime.datetime.now)
    added_by = factory.SubFactory(UserFactory)
    insee = '75056'
    vehicle = factory.SubFactory(VehicleFactory, descriptions__added_by=factory.SelfAttribute('...added_by'))
    owner_type = 'individual'
    owner_name = 'Owner ADS'
    category = ''
    added_via = 'api'
    source = 'added_by'


class TaxiFactory(BaseFactory):
    class Meta:
        model = Taxi

    id = factory.Sequence(lambda n: 'TAXI_%d' % n)
    vehicle = factory.SubFactory(VehicleFactory, descriptions__added_by=factory.SelfAttribute('...added_by'))
    ads = factory.SubFactory(
        ADSFactory,
        added_by=factory.SelfAttribute('..added_by'),
        vehicle=factory.SelfAttribute('..vehicle'),
    )
    added_at = factory.LazyFunction(datetime.datetime.now)
    added_by = factory.SubFactory(UserFactory)
    driver = factory.SubFactory(DriverFactory)
    added_via = 'api'
    source = 'added_by'


class HailFactory(BaseFactory):
    class Meta:
        model = Hail

    id = factory.Sequence(lambda n: 'HAIL_%d' % n)
    creation_datetime = datetime.datetime(2012, 12, 21, 13, 37, 13)
    taxi = factory.SubFactory(TaxiFactory, added_by=factory.SelfAttribute('..operateur'))
    status = 'received'
    customer = factory.SubFactory(CustomerFactory, added_by=factory.SelfAttribute('..added_by'))
    customer_lat = 48.850690
    customer_lon = 2.308620
    operateur = factory.SubFactory(UserFactory)
    customer_address = '20 Avenue de Ségur, 75007 Paris'
    customer_phone_number = '0799100222'
    added_at = factory.LazyFunction(datetime.datetime.now)
    added_by = factory.SubFactory(UserFactory)
    added_via = 'api'
    source = 'added_by'
