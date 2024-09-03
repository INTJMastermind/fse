USE_LOCAL = True # Download a local copy to save on key requests
NUM_JOBS = 10    # Limit the amount of destinations returned per airport.
NUM_ROUTES = 5   # Limit the number of routes searched. After each iteration, prune down to the top X most profitable routes

URL = 'https://server.fseconomy.net/data'

with open('key.txt') as f:
    USER_KEY = f.read()

import requests
import os
from bs4 import BeautifulSoup
from jobs import get_jobs, print_city_pair
from classes import *

fse = requests.Session()


def print_route(route):
    for cp in route.cps:
        print_city_pair(cp)
    print('-'*80)
    print(f'{len(route.legs)} LEG TOTAL:\t${route.value}\t{route.length} nm\t${int(route.dollars_per_nm)}/nm\n')


def advance_route(routes, max_jobs, max_routes, step, num_steps, allow_reverse):
    """
    Iteratively finds the most profitable assignments from the last airport on each route. After each step, the number of routes is pruned back, to prevent exponential growth.
    """
    new_routes = []
    for old_route in routes:
        # 1. Check the jobs from the end of the route.
        last_icao = old_route.cps[-1].destination
        cps = get_jobs(last_icao, max_jobs)
        
        # 2. Make new routes from the old route.
        for cp in cps:
            # Avoid duplicating the same leg twice in the same route.
            if cp.leg in old_route.legs:
                continue
            elif not allow_reverse and cp.leg[::-1] in old_route.legs:
                continue
            else:
                # Make a copy to avoid changing the old route.
                new_cps = old_route.cps.copy()
                new_cps.append(cp)
                new_routes.append(Route(new_cps))

    # 3. Sort new routes by $/nm:
    new_routes = sort_routes(new_routes, max_routes)

    # 5. Iterate
    step += 1
    if step < num_steps:
        new_routes = advance_route(new_routes, max_jobs, max_routes, step, num_steps, allow_reverse)
    
    return new_routes

def sort_routes(routes, max_routes):
    # Sort new routes by $/nm:
    routes = sorted(routes, key=lambda x: x.dollars_per_nm, reverse=True)

    # Return the top few routes.
    return routes[:min(len(routes), max_routes)]


def get_route(start_icao, num_steps, max_jobs, max_routes, allow_reverse):
    # Get the CityPairs starting from the first airport
    cps = get_jobs(start_icao, max_jobs)

    # Create a list of routes. At this point, each route only has one CityPair.
    routes = [Route(cp) for cp in cps]

    # Sort and filter the routes.
    routes = sort_routes(routes, max_routes)

    # For multi-step routes, advance the route now.
    steps = 1
    if steps < num_steps:
        routes = advance_route(routes, max_jobs, max_routes, steps, num_steps, allow_reverse)
    
    # Print the final routes.
    for route in routes:
        print_route(route)

    
if __name__ == '__main__':
    print('FSE Route Finder')
    if not os.path.exists('key.txt'):
        print('ERROR: Please paste your FSE access key into a file "key.txt".')
        exit()
    icao = input('Starting airport: ').upper()
    legs = int(input('Number of Legs: '))
    rev = input('Allow reverse legs (out-and-back trips)? (Y/N): ')
    allow_reverse = rev.upper().startswith('Y')
    get_route(icao, legs, NUM_JOBS, NUM_ROUTES, allow_reverse)