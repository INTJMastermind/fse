"""
Finds and returns the optimal routes from a particular airport (ICAO code)
"""
import os
import time
import requests
from math import sin, cos, sqrt, atan2, radians
from bs4 import BeautifulSoup

USE_LOCAL = True # Download a local copy to save on key requests
URL = 'https://server.fseconomy.net/data'

try:
    with open('key.txt') as f:
        USER_KEY = f.read()
except:
    print("ERROR: key.txt not found!")

global fse
fse = requests.Session()

class CityPair:
    '''
    A CityPair object summarizes all the jobs between two cities / airports.
    Jobs include the total cargo, passenger (pax), and VIP jobs, and their values.
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

    def add_cargo(self, weight, value):
        """
        Adds a cargo job. Inputs are the weight in kg and value of the job.
        """
        self.cargo += weight
        self.cargo_value += value
        self.cargo_jobs += 1
        self.update_totals()

    def add_pax(self, pax, value):
        """
        Adds a pax job. Inputs are the number of passengers and value of the job.
        """
        self.pax += pax
        self.pax_value += value
        self.pax_jobs += 1
        self.update_totals()

    def add_vip(self, vips, value):
        """
        Adds a VIP job. Inputs are the number of passengers and value of the job.
        """
        self.vips += vips
        self.vip_value += value
        self.vip_jobs += 1
        self.update_totals()    

    def update_totals(self):
        """
        Updates the total value of all jobs between the two cities, as well as the $/nm.
        """
        self.total_jobs = self.cargo_jobs + self.pax_jobs + self.vip_jobs
        self.total_value = self.cargo_value + self.pax_value + self.vip_value

        # Handle the divide by zero error if the ICAO code is not present.
        try:
            self.dollars_per_nm = self.total_value / self.length
        except:
            self.dollars_per_nm = 0

    def __str__(self):
        return f'{self.origin}-{self.destination}\t${self.total_value}\t{self.length} nm\t${int(self.dollars_per_nm)}/nm\t{self.total_jobs} jobs\t{self.pax} pax\t{self.cargo} kg\t{self.vips} VIPs'
    
    def __repr__(self):
        return f'CityPair: {self.origin}-{self.destination}'


class Airport():
    """
    The Airport object holds the basic information about an airport.
    ICAO: The airport's 4-letter ICAO identifier
    Name: The full name of the airport
    Lat: The airport's lattitude in decimal degrees.
    Long: The airport's longitude in decimal degrees.
    """
    def __init__(self, icao = str, name = str, lat = float, long = float):
        self.icao = icao
        self.name = name
        self.lat = lat
        self.long = long

    def __repr__(self):
        return f'Airport: {self.icao}'


def load_apt(filename = 'icaodata.csv'):
    with open(filename) as f:
        lines = f.readlines()

    apt = dict()
    for line in lines:
        data = line.split(',')
        icao = data[0]
        lat = float(data[1])
        long = float(data[2])
        name = data[5]

        apt[data[0]] = Airport(icao, name, lat, long)

    return apt

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


def get_jobs(icao, max_jobs):
    """
    Gets FSE assignments from an airport based on icao code.
    Inputs:
    - icao: ICAO code of the airport.
    - max_jobs: limits the number of jobs returned.
    Returns:
    - A sorted list of city pairs based on their $/nm value.
    """
    # Load the airport database as a global so it can be used multiple times in the route feature later on.
    if 'apt' not in globals():
        global apt
        apt = load_apt()

    # Check if we have a valid airport
    if icao not in apt:
        print(f'ERROR: {icao} was not found in the FSE Airport Database')
        return []

    # Format used for FSE requests
    data = {'userkey': USER_KEY,
            'format': 'xml',
            'query': 'icao',
            'search': 'jobsfrom',
            'icaos': icao}

    # Download a local copy for development to save on API access requests.
    if USE_LOCAL:
        # Check if the xml file exists or is current:
        filename = icao + '.xml'
        if not os.path.exists(filename) or is_stale(filename):
            try:
                #Download the xml file from FSE servers
                #print(f'Accessing {URL}')
                xml = fse.get(URL, params = data)
            except:
                print('Unable to access FSE server.')
                exit()
            #print(f'Saving {filename}')
            with open(filename, 'w') as f:
                f.write(xml.text)

        #print(f'Opening {filename}')
        with open(filename) as f:
            s = BeautifulSoup(f.read(), 'xml')
    else:
        # Use the most current copy from online.
        print(f'Accessing {URL}')
        s = BeautifulSoup(fse.get(URL, params = data).text, 'xml')

    # Check for errors. If so, return an empty list of jobs.
    if s.Error:
        print(f'ERROR IN {icao}: {s.Error.text}')
        return []

    # All jobs are under an <Assignment> tag.
    jobs = s.find_all('Assignment')

    # Remove All-In jobs:
    jobs = [j for j in jobs if j.Type.text != "All-In"]

    # Find jobs going to the same place using a dictionary, with the key as a tuple of
    # (origin ICAO, destination ICAO), and the value as the corresponding CityPair object.
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


def is_stale(filename, period = 3600):
    """
    Returns whether a file (filename) is older than a set duration (period) in seconds. Default is 1 hour.
    """
    last_modified = time.time()-os.stat(filename).st_mtime # Time in seconds since the file was last modified
    return last_modified > period


if __name__ == '__main__':
    print('FSE Job Finder')
    while True:
        icao = input('Airport ICAO: ').upper()
        max_jobs = int(input('Number of jobs to return (0 = all): '))
        if max_jobs == 0:
            max_jobs = 99
        jobs = get_jobs(icao, max_jobs)
        for job in jobs:
            print(job)