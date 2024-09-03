"""
Finds and returns the optimal routes from a particular airport (ICAO code)
"""

USE_LOCAL = True # Download a local copy to save on key requests

URL = 'https://server.fseconomy.net/data'

with open('key.txt') as f:
    USER_KEY = f.read()

import requests
import os
from bs4 import BeautifulSoup
from classes import *

fse = requests.Session()

def get_jobs(icao, max_jobs):
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

    # Check for errors
    if s.Error:
        print(f'ERROR IN {icao}: {s.Error.text}')
        return []

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


def main():
    print('FSE Job Finder')
    if not os.path.exists('key.txt'):
        print('ERROR: Please paste your FSE access key into a file "key.txt".')
        exit()
    icao = input('Starting airport: ').upper()
    max_jobs = int(input('Number of jobs to return (0 = all): '))
    if max_jobs == 0:
        max_jobs = 99
    jobs = get_jobs(icao, max_jobs)
    for job in jobs:
        print_city_pair(job)

if __name__ == '__main__':
    main()