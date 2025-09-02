from ortools.constraint_solver import pywrapcp, routing_enums_pb2

from helpers.dist_comp import compute_distance_matrix

def ortools_vrp(depot, customers, num_vehicles=3, vehicle_capacity=200):
    dist_matrix = compute_distance_matrix(depot, customers)
    demands = [0] + [int(round(c["weight"])) for c in customers]
    manager = pywrapcp.RoutingIndexManager(len(dist_matrix), num_vehicles, 0)
    routing = pywrapcp.RoutingModel(manager)

    def distance_callback(from_index, to_index):
        return int(dist_matrix[manager.IndexToNode(from_index)][manager.IndexToNode(to_index)] * 1000)
    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    def demand_callback(from_index):
        return demands[manager.IndexToNode(from_index)]
    demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
    routing.AddDimensionWithVehicleCapacity(demand_callback_index, 0, [vehicle_capacity]*num_vehicles, True, "Capacity")

    search_params = pywrapcp.DefaultRoutingSearchParameters()
    search_params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    search_params.time_limit.seconds = 5

    solution = routing.SolveWithParameters(search_params)
    routes = [[] for _ in range(num_vehicles)]
    if solution:
        for v in range(num_vehicles):
            index = routing.Start(v)
            while not routing.IsEnd(index):
                node = manager.IndexToNode(index)
                if node != 0:
                    routes[v].append(customers[node-1])
                index = solution.Value(routing.NextVar(index))
    return routes