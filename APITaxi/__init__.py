import APITaxi2


__author__ = 'Julien Castets'
__contact__ = 'julien.castets@beta.gouv.fr'
__homepage__ = 'https://github.com/openmaraude/APITaxi'
__version__ = '0.1.0'
__doc__ = 'REST API of le.taxi'


def create_app():
    return APITaxi2.create_app()
