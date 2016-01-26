# -*- coding: utf-8 -*-
from .mixins import (AsDictMixin, HistoryMixin, unique_constructor,
        MarshalMixin, FilterOr404Mixin)
from .populate_obj import create_obj_from_json
from .request_wants_json import request_wants_json

get_columns_names = lambda m: [c.name for c in m.__table__.columns]
