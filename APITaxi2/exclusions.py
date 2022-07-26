from functools import lru_cache

from geoalchemy2.shape import to_shape
from shapely.geometry import Point
from shapely.strtree import STRtree

from APITaxi_models2 import db, Exclusion


# Load exclusion zones the first time
@lru_cache()
def _load_exclusion_tree():
    shapes = [to_shape(shape) for shape, in db.session.query(Exclusion.shape)]
    # We don't need to keep track of which zone, just it exists
    return STRtree(shapes)


class ExclusionHelper:
    _tree = None

    def __init__(self):
        self._load_tree()

    def _load_tree(self):
        self._tree = _load_exclusion_tree()

    def is_at_excluded_zone(self, lon, lat):
        if lon == 0.0 and lat == 0.0:  # Seen in production
            return None
        point = Point(lon, lat)
        # __bool__ is not implemented on the resulting array itself...
        return bool(self._tree.query(point).size)

    def reset(self):
        _load_exclusion_tree.cache_clear()
        self._load_tree()
