import shortuuid


def get_short_uuid():
    suid = shortuuid.ShortUUID()
    return suid.uuid()[:7]
