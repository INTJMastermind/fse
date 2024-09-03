import pickle, os

class CityPair:
    '''
    A City Pair object holds all the jobs between two cities.
    This includes cargo, passenger (pax), and VIP jobs.
    It is represented by a tuple of origin and destination ICAOs.
    '''
    def __init__(self, origin, destination):
        self.origin = origin
        self.destination = destination
        self.length = find_range(self.origin, self.destination)
        self.leg = (self.origin, self.destination)

        # Cargo jobs
        self.cargo = 0 # total cargo in kg
        self.cargo_jobs = 0 # number of cargo trips
        self.cargo_value = 0 # value of cargo jobs

        # Non-VIP passenger jobs.
        self.pax = 0
        self.pax_jobs = 0
        self.pax_value = 0

        # VIP jobs
        self.vips = 0
        self.vip_jobs = 0
        self.vip_value = 0

        # Totals
        self.total_jobs = 0 # number of jobs in total
        self.total_value = 0 # sum of all assignments going between the city pair.
        self.dollars_per_nm = 0

    def update_totals(self):
        self.total_jobs = self.cargo_jobs + self.pax_jobs + self.vip_jobs
        self.total_value = self.cargo_value + self.pax_value + self.vip_value
        if self.length:
            self.dollars_per_nm = self.total_value / self.length
    
    def add_cargo(self, weight, pay):
        '''
        Adds a cargo job.
        '''
        self.cargo += weight
        self.cargo_value += pay
        self.cargo_jobs += 1
        self.update_totals()

    def add_pax(self, pax, pay):
        '''
        Adds a pax job.
        '''
        self.pax += pax
        self.pax_value += pay
        self.pax_jobs += 1
        self.update_totals()

    def add_vip(self, vips, pay):
        '''
        Adds a VIP job.
        '''
        self.vips += vips
        self.vip_value += pay
        self.vip_jobs += 1
        self.update_totals()


class Route():
    """
    A Route object contains a list of CityPair objects, representing
    the airports traveled in sequence.
    For route optimization, we want to track:
    - A list of city pairs visited
    - Total value of all jobs along the route.
    - Total length of the route.
    - Average dollars per mile along the route.
    """
    def __init__(self, city_pairs):
        # List of CityPair objects making up the route
        if type(city_pairs) == list:        
            self.cps = city_pairs
        else:
            self.cps = [city_pairs]

        self.legs = {cp.leg for cp in self.cps}

        # Total value of jobs along the route
        self.value = sum([cp.total_value for cp in self.cps])

        # Total length of the jobs along the route.
        self.length = sum([cp.length for cp in self.cps])
        
        # Total efficiency as $/nm.
        self.dollars_per_nm = self.value / self.length


class Airport():
    def __init__(self, icao = str, name = str, lat = float, long = float, alt = int, rwy_length = int):
        self.icao = icao
        self.name = name
        self.lat = lat
        self.long = long
        self.alt = alt
        self.rwy_length = rwy_length


def load_apt(filename = 'icaodata.pkl'):
    """
    Loads the icaodata.pkl file, which contains a dictionary with key being the ICAO code, and 
    value containing an Airport object.
    """
    if not os.path.exists(filename):
        return load_apt_csv()
    else:
        with open(filename, 'rb') as f:
            return pickle.load(f)
    
    
def load_apt_csv(filename = 'icaodata.csv', outname = 'icaodata.pkl'):
    with open(filename) as f:
        lines = f.readlines()

    apt = dict()
    for line in lines:
        data = line.split(',')
        icao = data[0]
        lat = float(data[1])
        long = float(data[2])
        alt = int(data[4])
        name = data[5]

        apt[data[0]] = Airport(icao, name, lat, long, alt, 0)

    with open(outname, 'wb') as f:
        pickle.dump(apt, f)

    return apt


def find_range(ICAO1, ICAO2):
    """
    Returns the range in nautical miles between two airports given their ICAO codes.
    """
    from math import sin, cos, sqrt, atan2, radians

    apt = load_apt()

    if ICAO1 not in apt or ICAO2 not in apt:
        return 100

    # Approximate radius of earth in km
    R = 6373.0
    # Nautical Miles per KM
    NM_per_KM = 0.54

    lat1 = radians(apt[ICAO1].lat)
    lon1 = radians(apt[ICAO1].long)
    lat2 = radians(apt[ICAO2].lat)
    lon2 = radians(apt[ICAO2].long)

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return int(R * c * NM_per_KM)

if __name__ == '__main__':
    load_apt_csv()