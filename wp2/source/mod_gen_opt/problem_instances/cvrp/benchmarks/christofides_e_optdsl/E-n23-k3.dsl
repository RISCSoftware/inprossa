# Christofides/Eilon CVRP instance: E-n23-k3
# City 0 is the depot.
# Converted from standard VRP file format.

N_CITIES : int = 23
DEPOT : int = 0
N_VEHICLES : int = 3
VEHICLE_CAPACITY : int = 4500
N_ARCS : int = N_VEHICLES * N_CITIES * N_CITIES
MAX_ROUTE_COST : int = 100000

X_COORDS : DSList(N_CITIES, DSInt()) = [266, 295, 301, 309, 217, 218, 282, 242, 230, 249, 256, 265, 267, 259, 315, 329, 318, 329, 267, 275, 303, 208, 326]
Y_COORDS : DSList(N_CITIES, DSInt()) = [235, 272, 258, 260, 274, 278, 267, 249, 262, 268, 267, 257, 242, 265, 233, 252, 252, 224, 213, 192, 201, 217, 181]

# Depot demand is 0.
DEMANDS : DSList(N_CITIES, DSInt()) = [0, 125, 84, 60, 500, 300, 175, 350, 150, 1100, 4100, 225, 300, 250, 500, 150, 100, 250, 120, 600, 500, 175, 75]

DISTANCE_MATRIX : DSList(N_CITIES, DSList(N_CITIES, DSInt())) = [
	[0, 47, 42, 50, 63, 64, 36, 28, 45, 37, 34, 22, 7, 31, 49, 65, 55, 64, 22, 44, 50, 61, 81],
	[47, 0, 15, 18, 78, 77, 14, 58, 66, 46, 39, 34, 41, 37, 44, 39, 30, 59, 65, 82, 71, 103, 96],
	[42, 15, 0, 8, 86, 85, 21, 60, 71, 53, 46, 36, 38, 43, 29, 29, 18, 44, 56, 71, 57, 102, 81],
	[50, 18, 8, 0, 93, 93, 28, 68, 79, 61, 53, 44, 46, 50, 28, 22, 12, 41, 63, 76, 59, 110, 81],
	[63, 78, 86, 93, 0, 4, 65, 35, 18, 33, 40, 51, 59, 43, 106, 114, 103, 123, 79, 100, 113, 58, 143],
	[64, 77, 85, 93, 4, 0, 65, 38, 20, 33, 40, 51, 61, 43, 107, 114, 103, 123, 81, 103, 115, 62, 145],
	[36, 14, 21, 28, 65, 65, 0, 44, 52, 33, 26, 20, 29, 23, 47, 49, 39, 64, 56, 75, 69, 89, 97],
	[28, 58, 60, 68, 35, 38, 44, 0, 18, 20, 23, 24, 26, 23, 75, 87, 76, 91, 44, 66, 78, 47, 108],
	[45, 66, 71, 79, 18, 20, 52, 18, 0, 20, 26, 35, 42, 29, 90, 100, 89, 106, 61, 83, 95, 50, 126],
	[37, 46, 53, 61, 33, 33, 33, 20, 20, 0, 7, 19, 32, 10, 75, 82, 71, 91, 58, 80, 86, 65, 116],
	[34, 39, 46, 53, 40, 40, 26, 23, 26, 7, 0, 13, 27, 4, 68, 75, 64, 85, 55, 77, 81, 69, 111],
	[22, 34, 36, 44, 51, 51, 20, 24, 35, 19, 13, 0, 15, 10, 55, 64, 53, 72, 44, 66, 68, 70, 97],
	[7, 41, 38, 46, 59, 61, 29, 26, 42, 32, 27, 15, 0, 24, 49, 63, 52, 65, 29, 51, 55, 64, 85],
	[31, 37, 43, 50, 43, 43, 23, 23, 29, 10, 4, 10, 24, 0, 64, 71, 60, 81, 53, 75, 78, 70, 107],
	[49, 44, 29, 28, 106, 107, 47, 75, 90, 75, 68, 55, 49, 64, 0, 24, 19, 17, 52, 57, 34, 108, 53],
	[65, 39, 29, 22, 114, 114, 49, 87, 100, 82, 75, 64, 63, 71, 24, 0, 11, 28, 73, 81, 57, 126, 71],
	[55, 30, 18, 12, 103, 103, 39, 76, 89, 71, 64, 53, 52, 60, 19, 11, 0, 30, 64, 74, 53, 115, 71],
	[64, 59, 44, 41, 123, 123, 64, 91, 106, 91, 85, 72, 65, 81, 17, 28, 30, 0, 63, 63, 35, 121, 43],
	[22, 65, 56, 63, 79, 81, 56, 44, 61, 58, 55, 44, 29, 53, 52, 73, 64, 63, 0, 22, 38, 59, 67],
	[44, 82, 71, 76, 100, 103, 75, 66, 83, 80, 77, 66, 51, 75, 57, 81, 74, 63, 22, 0, 29, 72, 52],
	[50, 71, 57, 59, 113, 115, 69, 78, 95, 86, 81, 68, 55, 78, 34, 57, 53, 35, 38, 29, 0, 96, 30],
	[61, 103, 102, 110, 58, 62, 89, 47, 50, 65, 69, 70, 64, 70, 108, 126, 115, 121, 59, 72, 96, 0, 123],
	[81, 96, 81, 81, 143, 145, 97, 108, 126, 116, 111, 97, 85, 107, 53, 71, 71, 43, 67, 52, 30, 123, 0]
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
