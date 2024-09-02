USE_LOCAL = True # Download a local copy to save on key requests
URL = 'https://server.fseconomy.net/data'

with open('key.txt') as f:
    USER_KEY = f.read()

import requests
import os
import pickle
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

        self.num_stops = len(self.cps)

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


def load_apt(filename = 'apt.pkl'):
    """
    Loads the apt.pkl file, which contains a dictionary with key being the ICAO code, and 
    value containing an Airport object.
    """
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


def find_range(ICAO1, ICAO2):
    """
    Returns the range in nautical miles between two airports given their ICAO codes.
    """
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


def get_assignments(icao, max_jobs):
    """
    Gets FSE assignments from an airport based on icao code.
    Inputs:
    - icao: ICAO code of the airport.
    - max_jobs: limits the number of jobs returned.
    Returns:
    - A sorted list of city pairs based on their $/nm value.
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
    cps = dict()
    for j in jobs:
        # If the job's city pair doesn't exist in cp, add it.
        ident = (j.Location.text, j.ToIcao.text)
        if ident not in cps:
            cps[ident] = CityPair(ident[0], ident[1])

        # Extract the amount of passengers / cargo, and the pay from xml tags
        amount = int(j.Amount.text)
        pay = int(float(j.Pay.text))

        # Update the city pair based on the type of job.
        # Cargo jobs use 'kg's in the UnitType
        if j.UnitType.text == 'kg':
            cps[ident].add_cargo(amount, pay)
        # VIP jobs are under type 'VIP'
        elif j.Type.text == 'VIP':
            cps[ident].add_vip(amount, pay)
        # Otherwise it's a regular passenger job
        else:
            cps[ident].add_pax(amount, pay)

    # Sort city pairs by total value, take the top city pairs.
    sorted_cps = sorted(cps.values(), key=lambda x: x.dollars_per_nm, reverse=True)
    return sorted_cps[:min(len(sorted_cps), max_jobs)]


def print_city_pair(city_pair):
    print(f'{city_pair.origin}-{city_pair.destination}\t${city_pair.total_value}\t{city_pair.length} nm\t${int(city_pair.dollars_per_nm)}/nm\t{city_pair.total_jobs} jobs\t{city_pair.pax} pax\t{city_pair.cargo} kg\t{city_pair.vips} VIPs')
    

def print_route(route):
    for cp in route.cps:
        print_city_pair(cp)
    print(f'ROUTE TOTAL:\t${route.value}\t{route.length} nm\t${int(route.dollars_per_nm)}/nm\n')


def advance_route(routes, max_jobs, max_routes, step, num_steps):
    """
    Iteratively finds the most profitable assignments from the last airport on each route. After each step, the number of routes is pruned back, to prevent exponential growth.
    """
    new_routes = []
    for old_route in routes:
        # 1. Check the jobs from the end of the route.
        last_icao = old_route.cps[-1].destination
        cps = get_assignments(last_icao, max_jobs)
        
        # 2. Make new routes from the old route.
        for cp in cps:
            # Avoid duplicating the same leg twice in the same route.
            if cp not in old_route.cps:
                # Make a copy to avoid changing the old route.
                new_cps = old_route.cps.copy()
                new_cps.append(cp)
                new_routes.append(Route(new_cps))
            else:
                pass

    # 3. Sort new routes by $/nm:
    new_routes = sort_routes(new_routes, max_routes)

    # 5. Iterate
    step += 1
    if step < num_steps:
        new_routes = advance_route(new_routes, max_jobs, max_routes, step, num_steps)
    
    return new_routes

def sort_routes(routes, max_routes):
    # Sort new routes by $/nm:
    routes = sorted(routes, key=lambda x: x.dollars_per_nm, reverse=True)

    # Return the top few routes.
    return routes[:min(len(routes), max_routes)]


def main(start_icao, max_jobs, max_routes, num_steps):
    
    # Load the apt dictionary, used for range calculations.
    global apt

    if not os.path.exists('icaodata.pkl'):
        load_apt_csv()
    
    apt = load_apt('icaodata.pkl')

    # Get the CityPairs starting from the first airport
    cps = get_assignments(start_icao, max_jobs)

    # Create a list of routes. At this point, each route only has one CityPair.
    routes = [Route(cp) for cp in cps]

    # Sort and filter the routes.
    routes = sort_routes(routes, max_routes)

    # For multi-step routes, advance the route now.
    steps = 1
    if steps < num_steps:
        routes = advance_route(routes, max_jobs, max_routes, steps, num_steps)
    
    # Print the final routes.
    for route in routes:
        print_route(route)

    
if __name__ == '__main__':
    main('NZQN', 100, 5, 3)