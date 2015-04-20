from redis import StrictRedis

class GeoRedis(StrictRedis):
    def geoadd(self, geoset, lat, lon, id_):
        return self.execute_command("geoadd {geoset} {lat} {lon} {id_}".format(
            geoset=geoset, lat=lat, lon=lon, id_=id_))

    def georadius(self, geoset, lat, lon, radius=300, units='km',
            withdistance=True, withcoordinates=True, withhash=False,
            withgeojson=False, withgeojsoncollection=False,
            noproperties=False, order='asc'):
        command = 'georadius {geoset} {lat} {lon} {radius} {units}'.format(
                geoset=geoset, lat=lat, lon=lon, radius=radius, units=units)
        if withdistance:
            command += ' withdistance'
        if withcoordinates:
            command += ' withcoordinates'
        if withhash:
            command += ' withhash'
        if withgeojson:
            command += ' withgeojson'
        if withgeojsoncollection:
            command += ' withgeojsoncollection'
        if noproperties:
            command += ' noproperties'
        command += ' '+order
        return self.execute_command(command)



