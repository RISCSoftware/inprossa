# Random Euclidean CVRP instance + model (seed=108)
# City 0 is the depot.

N_CITIES : int = 8
DEPOT : int = 0
N_VEHICLES : int = 4
VEHICLE_CAPACITY : int = 10
N_ARCS : int = N_VEHICLES * N_CITIES * N_CITIES
MAX_ROUTE_COST : int = 5000

X_COORDS : DSList(N_CITIES, DSInt()) = [50, 16, 10, 49, 35, 25, 38, 23]
Y_COORDS : DSList(N_CITIES, DSInt()) = [50, 91, 84, 93, 48, 10, 27, 25]

# Depot demand is 0.
DEMANDS : DSList(N_CITIES, DSInt()) = [0, 6, 4, 2, 4, 2, 9, 7]

DISTANCE_MATRIX : DSList(N_CITIES, DSList(N_CITIES, DSInt())) = [
	[0, 53, 52, 43, 15, 47, 26, 37],
	[53, 0, 9, 33, 47, 81, 68, 66],
	[52, 9, 0, 40, 44, 76, 64, 60],
	[43, 33, 40, 0, 47, 86, 67, 73],
	[15, 47, 44, 47, 0, 39, 21, 26],
	[47, 81, 76, 86, 39, 0, 21, 15],
	[26, 68, 64, 67, 21, 21, 0, 15],
	[37, 66, 60, 73, 26, 15, 15, 0]
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
