USE_LOCAL = True # Download a local copy to save on key requests
URL = 'https://server.fseconomy.net/data'

with open('key.txt') as f:
    USER_KEY = f.read()

import requests
import os
from bs4 import BeautifulSoup
from classes import *

fse = requests.Session()

def get_assignments(icao, max_jobs = 100):
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
        print(f'{city_pair.origin}-{city_pair.destination}\t${city_pair.total_value}\t{city_pair.range} nm\t${city_pair.dollars_per_nm}/nm\t{city_pair.total_jobs} jobs\t{city_pair.pax} pax\t{city_pair.cargo} kg\t{city_pair.vips} VIPs')
    
    return cp


if __name__ == '__main__':
    get_assignments('KVNY', 10)