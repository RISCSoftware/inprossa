# CVRP instance: E-n22-k4
# City 0 is the depot.

N_CITIES : int = 22
DEPOT : int = 0
N_VEHICLES : int = 4
VEHICLE_CAPACITY : int = 6000
N_ARCS : int = N_VEHICLES * N_CITIES * N_CITIES
MAX_ROUTE_COST : int = 100000

X_COORDS : DSList(N_CITIES, DSInt()) = [145, 151, 159, 130, 128, 163, 146, 161, 142, 163, 148, 128, 156, 129, 146, 164, 141, 147, 164, 129, 155, 139]
Y_COORDS : DSList(N_CITIES, DSInt()) = [215, 264, 261, 254, 252, 247, 246, 242, 239, 236, 232, 231, 217, 214, 208, 208, 206, 193, 193, 189, 185, 182]

DEMANDS : DSList(N_CITIES, DSInt()) = [0, 1100, 700, 800, 1400, 2100, 400, 800, 100, 500, 600, 1200, 1300, 1300, 300, 900, 2100, 1000, 900, 2500, 1800, 700]

DISTANCE_MATRIX : DSList(N_CITIES, DSList(N_CITIES, DSInt())) = [
	[0, 49, 48, 42, 41, 37, 31, 31, 24, 28, 17, 23, 11, 16, 7, 20, 10, 22, 29, 31, 32, 34],
	[49, 0, 9, 23, 26, 21, 19, 24, 27, 30, 32, 40, 47, 55, 56, 57, 59, 71, 72, 78, 79, 83],
	[48, 9, 0, 30, 32, 15, 20, 19, 28, 25, 31, 43, 44, 56, 55, 53, 58, 69, 68, 78, 76, 81],
	[42, 23, 30, 0, 3, 34, 18, 33, 19, 38, 28, 23, 45, 40, 49, 57, 49, 63, 70, 65, 73, 73],
	[41, 26, 32, 3, 0, 35, 19, 34, 19, 38, 28, 21, 45, 38, 48, 57, 48, 62, 69, 63, 72, 71],
	[37, 21, 15, 34, 35, 0, 17, 5, 22, 11, 21, 38, 31, 47, 43, 39, 47, 56, 54, 67, 63, 69],
	[31, 19, 20, 18, 19, 17, 0, 16, 8, 20, 14, 23, 31, 36, 38, 42, 40, 53, 56, 59, 62, 64],
	[31, 24, 19, 33, 34, 5, 16, 0, 19, 6, 16, 35, 25, 43, 37, 34, 41, 51, 49, 62, 57, 64],
	[24, 27, 28, 19, 19, 22, 8, 19, 0, 21, 9, 16, 26, 28, 31, 38, 33, 46, 51, 52, 56, 57],
	[28, 30, 25, 38, 38, 11, 20, 6, 21, 0, 16, 35, 20, 40, 33, 28, 37, 46, 43, 58, 52, 59],
	[17, 32, 31, 28, 28, 21, 14, 16, 9, 16, 0, 20, 17, 26, 24, 29, 27, 39, 42, 47, 48, 51],
	[23, 40, 43, 23, 21, 38, 23, 35, 16, 35, 20, 0, 31, 17, 29, 43, 28, 42, 52, 42, 53, 50],
	[11, 47, 44, 45, 45, 31, 31, 25, 26, 20, 17, 31, 0, 27, 13, 12, 19, 26, 25, 39, 32, 39],
	[16, 55, 56, 40, 38, 47, 36, 43, 28, 40, 26, 17, 27, 0, 18, 36, 14, 28, 41, 25, 39, 34],
	[7, 56, 55, 49, 48, 43, 38, 37, 31, 33, 24, 29, 13, 18, 0, 18, 5, 15, 23, 25, 25, 27],
	[20, 57, 53, 57, 57, 39, 42, 34, 38, 28, 29, 43, 12, 36, 18, 0, 23, 23, 15, 40, 25, 36],
	[10, 59, 58, 49, 48, 47, 40, 41, 33, 37, 27, 28, 19, 14, 5, 23, 0, 14, 26, 21, 25, 24],
	[22, 71, 69, 63, 62, 56, 53, 51, 46, 46, 39, 42, 26, 28, 15, 23, 14, 0, 17, 18, 11, 14],
	[29, 72, 68, 70, 69, 54, 56, 49, 51, 43, 42, 52, 25, 41, 23, 15, 26, 17, 0, 35, 12, 27],
	[31, 78, 78, 65, 63, 67, 59, 62, 52, 58, 47, 42, 39, 25, 25, 40, 21, 18, 35, 0, 26, 12],
	[32, 79, 76, 73, 72, 63, 62, 57, 56, 52, 48, 53, 32, 39, 25, 25, 25, 11, 12, 26, 0, 16],
	[34, 83, 81, 73, 71, 69, 64, 64, 57, 59, 51, 50, 39, 34, 27, 36, 24, 14, 27, 12, 16, 0]
]

arcs: DSList(N_ARCS, DSInt(0, 1))
vehicle_used: DSList(N_VEHICLES, DSInt(0, 1))
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
