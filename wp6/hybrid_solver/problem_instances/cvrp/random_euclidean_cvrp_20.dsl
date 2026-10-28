# Random Euclidean CVRP instance + model (seed=120)
# City 0 is the depot.

N_CITIES : int = 20
DEPOT : int = 0
N_VEHICLES : int = 5
VEHICLE_CAPACITY : int = 25
N_ARCS : int = N_VEHICLES * N_CITIES * N_CITIES
MAX_ROUTE_COST : int = 30000

X_COORDS : DSList(N_CITIES, DSInt()) = [50, 65, 24, 93, 85, 11, 27, 32, 41, 94, 13, 86, 38, 36, 37, 24, 65, 14, 26, 89]
Y_COORDS : DSList(N_CITIES, DSInt()) = [50, 31, 81, 75, 59, 40, 28, 92, 47, 20, 90, 40, 16, 36, 27, 64, 94, 54, 25, 3]

# Depot demand is 0.
DEMANDS : DSList(N_CITIES, DSInt()) = [0, 2, 1, 8, 7, 7, 7, 7, 9, 7, 2, 1, 1, 7, 6, 5, 4, 3, 7, 7]

DISTANCE_MATRIX : DSList(N_CITIES, DSList(N_CITIES, DSInt())) = [
	[0, 24, 40, 50, 36, 40, 32, 46, 9, 53, 54, 37, 36, 20, 26, 30, 46, 36, 35, 61],
	[24, 0, 65, 52, 34, 55, 38, 69, 29, 31, 79, 23, 31, 29, 28, 53, 63, 56, 39, 37],
	[40, 65, 0, 69, 65, 43, 53, 14, 38, 93, 14, 74, 66, 47, 56, 17, 43, 29, 56, 102],
	[50, 52, 69, 0, 18, 89, 81, 63, 59, 55, 81, 36, 81, 69, 74, 70, 34, 82, 84, 72],
	[36, 34, 65, 18, 0, 76, 66, 62, 46, 40, 78, 19, 64, 54, 58, 61, 40, 71, 68, 56],
	[40, 55, 43, 89, 76, 0, 20, 56, 31, 85, 50, 75, 36, 25, 29, 27, 76, 14, 21, 86],
	[32, 38, 53, 81, 66, 20, 0, 64, 24, 67, 64, 60, 16, 12, 10, 36, 76, 29, 3, 67],
	[46, 69, 14, 63, 62, 56, 64, 0, 46, 95, 19, 75, 76, 56, 65, 29, 33, 42, 67, 106],
	[9, 29, 38, 59, 46, 31, 24, 46, 0, 59, 51, 46, 31, 12, 20, 24, 53, 28, 27, 65],
	[53, 31, 93, 55, 40, 85, 67, 95, 59, 0, 107, 22, 56, 60, 57, 83, 79, 87, 68, 18],
	[54, 79, 14, 81, 78, 50, 64, 19, 51, 107, 0, 88, 78, 59, 67, 28, 52, 36, 66, 116],
	[37, 23, 74, 36, 19, 75, 60, 75, 46, 22, 88, 0, 54, 50, 51, 66, 58, 73, 62, 37],
	[36, 31, 66, 81, 64, 36, 16, 76, 31, 56, 78, 54, 0, 20, 11, 50, 83, 45, 15, 53],
	[20, 29, 47, 69, 54, 25, 12, 56, 12, 60, 59, 50, 20, 0, 9, 30, 65, 28, 15, 62],
	[26, 28, 56, 74, 58, 29, 10, 65, 20, 57, 67, 51, 11, 9, 0, 39, 73, 35, 11, 57],
	[30, 53, 17, 70, 61, 27, 36, 29, 24, 83, 28, 66, 50, 30, 39, 0, 51, 14, 39, 89],
	[46, 63, 43, 34, 40, 76, 76, 33, 53, 79, 52, 58, 83, 65, 73, 51, 0, 65, 79, 94],
	[36, 56, 29, 82, 71, 14, 29, 42, 28, 87, 36, 73, 45, 28, 35, 14, 65, 0, 31, 91],
	[35, 39, 56, 84, 68, 21, 3, 67, 27, 68, 66, 62, 15, 15, 11, 39, 79, 31, 0, 67],
	[61, 37, 102, 72, 56, 86, 67, 106, 65, 18, 116, 37, 53, 62, 57, 89, 94, 91, 67, 0]
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
