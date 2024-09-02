USE_LOCAL = True # Download a local copy to save on key requests
URL = 'https://server.fseconomy.net/data'

with open('key.txt') as f:
    USER_KEY = f.read()

import requests
import os
from bs4 import BeautifulSoup
from math import sin, cos, sqrt, atan2, radians

fse = requests.Session()

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

    def __repr__(self):
        # Tuple containing origin and destination ICAOs.
        return (self.origin, self.destination)

    def update_totals(self):
        self.total_jobs = self.cargo_jobs + self.pax_jobs + self.vip_jobs
        self.total_value = self.cargo_value + self.pax_value + self.vip_value
        if self.length:
            self.dollars_per_nm = int(self.total_value / self.length)
    
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
        self.cps = city_pairs

        self.num_stops = len(self.cps)

        # Total value of jobs along the route
        self.value = sum([cp.total_value for cp in self.cps])

        # Total length of the jobs along the route.
        self.length = sum([cp.length for cp in self.cps])
        
        # Total efficiency as $/nm.
        self.dollars_per_nm = self.value / self.length

    def __repr__(self):
        # CityPair object is represented by a tuple of origin and destination ICAOs.
        # A route is represented as a list of CityPair tuples.
        return [repr(cp) for cp in self.cps]

        
class Airport():
    def __init__(self, icao = str, name = str, lat = float, long = float, alt = int, rwy_length = int):
        self.icao = icao
        self.name = name
        self.lat = lat
        self.long = long
        self.alt = alt
        self.rwy_length = rwy_length


def load_apt(filename = 'apt.pkl'):
    """
    Loads and returns the apt.pkl file, which contains a dictionary with key being the ICAO code, and 
    value containing an Airport object.
    """
    import pickle
    with open('apt.pkl', 'rb') as f:
        return pickle.load(f)


def find_range(ICAO1, ICAO2):
    """
    Returns the range in nautical miles between two airports given their ICAO codes.
    """

    if ICAO1 not in apt or ICAO2 not in apt:
        return False

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


def get_assignments(icao, max_jobs = 10):
    """
    Returns FSE assignments from an airport based on icao code.
    Inputs:
    - icao: ICAO code of the airport.
    - max_jobs: limits the number of jobs returned.
    Returns:
    - A sorted dictionary with key as the city pair in tuple form,
    and the CityPair object as value.
    """

    # Used for FSE requests
    data = {'userkey': USER_KEY,
            'format': 'xml',
            'query': 'icao',
            'search': 'jobsfrom',
            'icaos': icao}

    # Download a local copy for development to save on API access requests.
    if USE_LOCAL:
        filename = icao + '.xml'
        if not os.path.exists(filename):
            try:
                #Download the xml file from FSE servers
                print(f'Accessing {URL}')
                xml = fse.get(URL, params = data)
            except:
                print('Unable to access FSE server.')
                exit()
            print(f'Saving {filename}')
            with open(filename, 'w') as f:
                f.write(xml.text)

        print(f'Opening {filename}')
        with open(filename) as f:
            s = BeautifulSoup(f.read(), 'xml')
    else:
        # Use the most current copy from online.
        print(f'Accessing {URL}')
        s = BeautifulSoup(fse.get(URL, params = data).text, 'xml')

    # All jobs are under an <Assignment> tag.
    jobs = s.find_all('Assignment')

    # Organize city pairs into a dictionary, with the key as a tuple of
    # (origin, destination), and the value as the CityPair object.
    cp = dict()
    for j in jobs:
        # If the job's city pair doesn't exist in cp, add it.
        ident = (j.Location.text, j.ToIcao.text)
        if ident not in cp:
            cp[ident] = CityPair(ident[0], ident[1])

        # Extract the amount of passengers / cargo, and the pay from xml tags
        amount = int(j.Amount.text)
        pay = int(float(j.Pay.text))

        # Update the city pair based on the type of job.
        # Cargo jobs use 'kg's in the UnitType
        if j.UnitType.text == 'kg':
            cp[ident].add_cargo(amount, pay)
        # VIP jobs are under type 'VIP'
        elif j.Type.text == 'VIP':
            cp[ident].add_vip(amount, pay)
        # Otherwise it's a regular passenger job
        else:
            cp[ident].add_pax(amount, pay)

    # Sort city pairs by total value, take the top city pairs.
    dict_items = list(cp.items())
    sorted_dict_items = sorted(dict_items, key=lambda x: x[1].dollars_per_nm, reverse=True)
    cp = dict(sorted_dict_items[:min(len(sorted_dict_items), max_jobs)])

    # Print each result
    for city_pair in cp.values():
        print(f'{city_pair.origin}-{city_pair.destination}\t${city_pair.total_value}\t{city_pair.length} nm\t${city_pair.dollars_per_nm}/nm\t{city_pair.total_jobs} jobs\t{city_pair.pax} pax\t{city_pair.cargo} kg\t{city_pair.vips} VIPs')
    
    return cp


def main():
    global apt
    apt = load_apt()
    get_assignments('KVNY', 10)

if __name__ == '__main__':
    main()