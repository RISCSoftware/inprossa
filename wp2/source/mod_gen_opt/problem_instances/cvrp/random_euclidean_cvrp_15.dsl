# Random Euclidean CVRP instance + model (seed=115)
# City 0 is the depot.

N_CITIES : int = 15
DEPOT : int = 0
N_VEHICLES : int = 10
VEHICLE_CAPACITY : int = 17
N_ARCS : int = N_VEHICLES * N_CITIES * N_CITIES
MAX_ROUTE_COST : int = 20000

X_COORDS : DSList(N_CITIES, DSInt()) = [50, 36, 99, 68, 42, 70, 86, 36, 43, 7, 70, 19, 36, 62, 75]
Y_COORDS : DSList(N_CITIES, DSInt()) = [50, 25, 14, 14, 96, 37, 81, 87, 61, 70, 18, 5, 22, 94, 31]

# Depot demand is 0.
DEMANDS : DSList(N_CITIES, DSInt()) = [0, 3, 3, 3, 9, 4, 3, 7, 1, 4, 9, 6, 4, 5, 4]

DISTANCE_MATRIX : DSList(N_CITIES, DSList(N_CITIES, DSInt())) = [
	[0, 29, 61, 40, 47, 24, 48, 40, 13, 47, 38, 55, 31, 46, 31],
	[29, 0, 64, 34, 71, 36, 75, 62, 37, 54, 35, 26, 3, 74, 39],
	[61, 64, 0, 31, 100, 37, 68, 96, 73, 108, 29, 81, 64, 88, 29],
	[40, 34, 31, 0, 86, 23, 69, 80, 53, 83, 4, 50, 33, 80, 18],
	[47, 71, 100, 86, 0, 65, 46, 11, 35, 44, 83, 94, 74, 20, 73],
	[24, 36, 37, 23, 65, 0, 47, 60, 36, 71, 19, 60, 37, 58, 8],
	[48, 75, 68, 69, 46, 47, 0, 50, 47, 80, 65, 101, 77, 27, 51],
	[40, 62, 96, 80, 11, 60, 50, 0, 27, 34, 77, 84, 65, 27, 68],
	[13, 37, 73, 53, 35, 36, 47, 27, 0, 37, 51, 61, 40, 38, 44],
	[47, 54, 108, 83, 44, 71, 80, 34, 37, 0, 82, 66, 56, 60, 78],
	[38, 35, 29, 4, 83, 19, 65, 77, 51, 82, 0, 53, 34, 76, 14],
	[55, 26, 81, 50, 94, 60, 101, 84, 61, 66, 53, 0, 24, 99, 62],
	[31, 3, 64, 33, 74, 37, 77, 65, 40, 56, 34, 24, 0, 77, 40],
	[46, 74, 88, 80, 20, 58, 27, 27, 38, 60, 76, 99, 77, 0, 64],
	[31, 39, 29, 18, 73, 8, 51, 68, 44, 78, 14, 62, 40, 64, 0]
]

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
