def create_obj_from_json(cls, json_obj):
    keys = [getattr(cls, k) for k in cls.__dict__.keys() if k[:1] != '_']
    keys = filter(lambda k: hasattr(k, "name"), keys)
    required_keys = [k.name for k in keys if not k.nullable and not k.primary_key]
    for key in required_keys:
        if key not in json_obj:
            raise KeyError()
    new_obj = cls()
    for k in keys:
        name = k.name
        if name not in json_obj:
            continue
        setattr(new_obj, name, json_obj[name])
    return new_obj
