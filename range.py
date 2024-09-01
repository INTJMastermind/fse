import pickle
from classes import *
from math import sin, cos, sqrt, atan2, radians

with open('apt.pkl', 'rb') as f:
    apt = pickle.load(f)

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

if __name__ == '__main__':
    ICAO1 = 'KSFO'
    ICAO2 = 'KJFK'
    distance = find_range(ICAO1, ICAO2)
    print(f'{apt[ICAO1].name} is {distance} nm from {apt[ICAO2].name}.')