import airport

NUM_JOBS = 10    # Limit the amount of destinations returned per airport.
NUM_ROUTES = 5   # Limit the number of routes searched. After each iteration, prune down to the top X most profitable routes


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
    
    def print_route(self):
        for cp in self.cps:
            print(cp)
        print('-'*80)
        print(f'{len(self.legs)} LEG TOTAL:\t${self.value}\t{self.length} nm\t${int(self.dollars_per_nm)}/nm\n')


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
        route.print_route

    
if __name__ == '__main__':
    print('FSE Route Finder')
    icao = input('Starting airport: ').upper()
    legs = int(input('Number of Legs: '))
    rev = input('Allow reverse legs (out-and-back trips)? (Y/N): ')
    allow_reverse = rev.upper().startswith('Y')
    get_route(icao, legs, NUM_JOBS, NUM_ROUTES, allow_reverse)