class CityPair:
    '''
    A City Pair object summarizes all the jobs between two cities.
    This includes cargo, passenger (pax), and VIP jobs.
    '''
    def __init__(self, origin, destination):
        self.origin = origin
        self.destination = destination

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

    def update_totals(self):
        self.total_jobs = self.cargo_jobs + self.pax_jobs + self.vip_jobs
        self.total_value = self.cargo_value + self.pax_value + self.vip_value
    
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
    A route is generated between two or more airports in succession.
    For route optimization, we want to track:
    - List of airports visited
    - Does the route loop back on itself?
    - Total value of all jobs along the route.
    - Total length of the route.
    - Average dollars per mile along the route.
    """
    def __init__(self, icao_1, icao_2, pay):
        self.route = [icao_1, icao_2]
        self.value = pay
        self.length = 100
        self.num_stops = 1
        self.dollars_per_mile = self.pay / self.length

    def _update(self):
        # Re-calculates the number of stops and dollars per mile.
        self.num_stops = len(self.route) - 1        
        self.dollars_per_mile = self.pay / self.length

    def add_leg(self, icao_next, pay, length = 100):
        self.route.append(icao_next)
        self.value += pay
        self.length += length
        self._update()

    def contains_loop(self):
        # Returns True if the route has a duplicate
        return len(self.route) != len(set(self.route))