from ortools.constraint_solver import pywrapcp, routing_enums_pb2
from helpers.dist_comp import compute_distance_matrix

def ortools_vrp(
    depot,
    customers,
    num_vehicles=3,
    vehicle_capacity=200,
    mileage=15,          # km per liter
    fuel_price=110,      # cost per liter
    tank_size=45,        # liters
    time_limit=10
):
    dist_matrix = compute_distance_matrix(depot, customers)
    # demands: depot first (0), then each customer's weight as int
    demands = [0] + [int(round(c["weight"])) for c in customers]

    manager = pywrapcp.RoutingIndexManager(len(dist_matrix), int(num_vehicles), 0)
    routing = pywrapcp.RoutingModel(manager)

    # -------------------------
    # Distance callback (returns meters as int)
    # -------------------------
    def distance_callback(from_index, to_index):
        frm = manager.IndexToNode(from_index)
        to = manager.IndexToNode(to_index)
        # dist_matrix entries are in km (assumption) → convert to meters
        return int(dist_matrix[frm][to] * 1000)

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    # -------------------------
    # Capacity constraint
    # -------------------------
    def demand_callback(from_index):
        return int(demands[manager.IndexToNode(from_index)])

    demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
    routing.AddDimensionWithVehicleCapacity(
        demand_callback_index,
        int(0),                                # slack_max
        [int(vehicle_capacity)] * int(num_vehicles),  # vehicle capacities list
        name="Capacity",
        fix_start_cumul_to_zero=True
    )

    # -------------------------
    # Fuel constraint (uses ml as unit)
    # -------------------------
    def fuel_callback(from_index, to_index):
        frm = manager.IndexToNode(from_index)
        to = manager.IndexToNode(to_index)
        distance_km = float(dist_matrix[frm][to])
        # convert km -> liters used (km / mileage), then liters -> milliliters
        ml = int((distance_km / float(mileage)) * 1000)
        return ml

    fuel_callback_index = routing.RegisterTransitCallback(fuel_callback)
    routing.AddDimension(
        fuel_callback_index,
        int(4500),                     # slack_max in ml (~4.5 L buffer)
        int(tank_size * 1000),         # capacity in ml
        name="Fuel",
        fix_start_cumul_to_zero=True
    )

    # -------------------------
    # Solve
    # -------------------------
    search_params = pywrapcp.DefaultRoutingSearchParameters()
    search_params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    search_params.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    # time_limit is in seconds
    search_params.time_limit.seconds = int(time_limit)

    solution = routing.SolveWithParameters(search_params)

    routes = []
    if solution:
        for v in range(int(num_vehicles)):
            route, load, dist = [], 0, 0
            index = routing.Start(v)
            while not routing.IsEnd(index):
                node = manager.IndexToNode(index)
                if node != 0:
                    cust = customers[node - 1]
                    route.append(cust["customer_id"])
                    load += int(cust["weight"])

                next_index = solution.Value(routing.NextVar(index))
                # GetArcCostForVehicle expects routing indices (not manager nodes)
                dist += int(routing.GetArcCostForVehicle(index, next_index, v))
                index = next_index

            # dist is in meters (because distance_callback returned meters)
            km = float(dist) / 1000.0
            liters_used = km / float(mileage) if km > 0 else 0.0
            cost = liters_used * float(fuel_price)

            routes.append({
                "vehicle_id": int(v),
                "route": route,
                "load": int(load),
                "total_distance_km": round(km, 2),
                "fuel_used_l": round(liters_used, 2),
                "fuel_cost": round(cost, 2)
            })

    return routes
