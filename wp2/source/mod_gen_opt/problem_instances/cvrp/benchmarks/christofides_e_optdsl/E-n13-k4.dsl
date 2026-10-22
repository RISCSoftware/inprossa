# Christofides/Eilon CVRP instance: E-n13-k4
# City 0 is the depot.
# Converted from standard VRP file format.

N_CITIES : int = 13
DEPOT : int = 0
N_VEHICLES : int = 4
VEHICLE_CAPACITY : int = 6000
N_ARCS : int = N_VEHICLES * N_CITIES * N_CITIES
MAX_ROUTE_COST : int = 100000

X_COORDS : DSList(N_CITIES, DSInt()) = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
Y_COORDS : DSList(N_CITIES, DSInt()) = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

# Depot demand is 0.
DEMANDS : DSList(N_CITIES, DSInt()) = [0, 1200, 1700, 1500, 1400, 1700, 1400, 1200, 1900, 1800, 1600, 1700, 1100]

DISTANCE_MATRIX : DSList(N_CITIES, DSList(N_CITIES, DSInt())) = [
	[0, 9, 14, 23, 32, 50, 21, 49, 30, 27, 35, 28, 18],
	[9, 0, 21, 22, 36, 52, 24, 51, 36, 37, 41, 30, 20],
	[14, 21, 0, 25, 38, 5, 31, 7, 36, 43, 29, 7, 6],
	[23, 22, 25, 0, 42, 12, 35, 17, 44, 31, 31, 11, 6],
	[32, 36, 38, 42, 0, 22, 37, 16, 46, 37, 29, 13, 14],
	[50, 52, 5, 12, 22, 0, 41, 23, 10, 39, 9, 17, 16],
	[21, 24, 31, 35, 37, 41, 0, 26, 21, 19, 10, 25, 12],
	[49, 51, 7, 17, 16, 23, 26, 0, 30, 28, 16, 27, 12],
	[30, 36, 36, 44, 46, 10, 21, 30, 0, 25, 22, 10, 20],
	[27, 37, 43, 31, 37, 39, 19, 28, 25, 0, 20, 16, 8],
	[35, 41, 29, 31, 29, 9, 10, 16, 22, 20, 0, 10, 10],
	[28, 30, 7, 11, 13, 17, 25, 27, 10, 16, 10, 0, 10],
	[18, 20, 6, 6, 14, 16, 12, 12, 20, 8, 10, 10, 0]
]

# Flattened binary arc variables: arcs[v, i, j] in {0, 1}
arcs: DSList(N_ARCS, DSInt(0, 1))
vehicle_used: DSList(N_VEHICLES, DSInt(0, 1))
# MTZ/load variable to eliminate customer-only subtours.
u: DSList(N_CITIES, DSInt(0, VEHICLE_CAPACITY))


def all_customers_visited(arcs: DSList(N_ARCS, DSInt(0, 1))):
	for c in range(N_CITIES):
		if c != DEPOT:
			incoming = 0
			outgoing = 0
			for v in range(N_VEHICLES):
				for i in range(N_CITIES):
					incoming = incoming + arcs[v * N_CITIES * N_CITIES + i * N_CITIES + c]
				for j in range(N_CITIES):
					outgoing = outgoing + arcs[v * N_CITIES * N_CITIES + c * N_CITIES + j]
			assert incoming == 1
			assert outgoing == 1


def depot_start_end(
	arcs: DSList(N_ARCS, DSInt(0, 1)),
	vehicle_used: DSList(N_VEHICLES, DSInt(0, 1))
):
	for v in range(N_VEHICLES):
		departures = 0
		returns = 0
		for j in range(N_CITIES):
			departures = departures + arcs[v * N_CITIES * N_CITIES + DEPOT * N_CITIES + j]
		for i in range(N_CITIES):
			returns = returns + arcs[v * N_CITIES * N_CITIES + i * N_CITIES + DEPOT]
		assert departures == vehicle_used[v]
		assert returns == vehicle_used[v]


def flow_conservation(arcs: DSList(N_ARCS, DSInt(0, 1))):
	for v in range(N_VEHICLES):
		for c in range(N_CITIES):
			if c != DEPOT:
				incoming = 0
				outgoing = 0
				for i in range(N_CITIES):
					incoming = incoming + arcs[v * N_CITIES * N_CITIES + i * N_CITIES + c]
				for j in range(N_CITIES):
					outgoing = outgoing + arcs[v * N_CITIES * N_CITIES + c * N_CITIES + j]
				assert incoming == outgoing


def capacity_constraints(arcs: DSList(N_ARCS, DSInt(0, 1))):
	for v in range(N_VEHICLES):
		vehicle_load = 0
		for c in range(N_CITIES):
			if c != DEPOT:
				served_by_v = 0
				for j in range(N_CITIES):
					served_by_v = served_by_v + arcs[v * N_CITIES * N_CITIES + c * N_CITIES + j]
				vehicle_load = vehicle_load + DEMANDS[c] * served_by_v
		assert vehicle_load <= VEHICLE_CAPACITY


def no_self_loops(arcs: DSList(N_ARCS, DSInt(0, 1))):
	for v in range(N_VEHICLES):
		for i in range(N_CITIES):
			assert arcs[v * N_CITIES * N_CITIES + i * N_CITIES + i] == 0


def subtour_elimination(
	arcs: DSList(N_ARCS, DSInt(0, 1)),
	u: DSList(N_CITIES, DSInt(0, VEHICLE_CAPACITY))
):
	assert u[DEPOT] == 0

	for c in range(N_CITIES):
		if c != DEPOT:
			assert u[c] >= DEMANDS[c]
			assert u[c] <= VEHICLE_CAPACITY

	for i in range(N_CITIES):
		if i != DEPOT:
			for j in range(N_CITIES):
				if j != DEPOT and i != j:
					arc_ij = 0
					for v in range(N_VEHICLES):
						arc_ij = arc_ij + arcs[v * N_CITIES * N_CITIES + i * N_CITIES + j]
					assert u[i] - u[j] + VEHICLE_CAPACITY * arc_ij <= VEHICLE_CAPACITY - DEMANDS[j]


def total_distance(arcs: DSList(N_ARCS, DSInt(0, 1))):
	dist = 0
	for v in range(N_VEHICLES):
		for i in range(N_CITIES):
			for j in range(N_CITIES):
				dist = dist + DISTANCE_MATRIX[i][j] * arcs[v * N_CITIES * N_CITIES + i * N_CITIES + j]
	return dist


all_customers_visited(arcs)
depot_start_end(arcs, vehicle_used)
flow_conservation(arcs)
capacity_constraints(arcs)
no_self_loops(arcs)
subtour_elimination(arcs, u)

objective: DSInt(0, MAX_ROUTE_COST) = total_distance(arcs)

minimize(objective)
