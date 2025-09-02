from haversine import haversine
import numpy as np

def build_distance_lookup(depot, customers, base_speed_kmph=40):
    """
    Build a nested dict {nodeA: {nodeB: {distance_km, travel_time_min}}}.

    Args:
        depot (dict): {id, lat, lon}
        customers (list): [{customer_id, lat, lon, ...}]
        base_speed_kmph (float): assumed baseline average speed (default 40 km/h)

    Returns:
        dict: distance lookup table
    """
    # Use actual depot ID instead of "DEPOT"
    points = [(depot["id"], depot["lat"], depot["lon"])] + [
        (c["customer_id"], c["lat"], c["lon"]) for c in customers
    ]

    lookup = {}
    for i, (id_i, lat_i, lon_i) in enumerate(points):
        lookup[id_i] = {}
        for j, (id_j, lat_j, lon_j) in enumerate(points):
            if i == j:
                lookup[id_i][id_j] = {"distance_km": 0.0, "travel_time_min": 0.0}
            else:
                dist_km = haversine((lat_i, lon_i), (lat_j, lon_j))
                travel_time_hr = dist_km / base_speed_kmph if base_speed_kmph > 0 else 0
                travel_time_min = round(travel_time_hr * 60, 1)
                lookup[id_i][id_j] = {
                    "distance_km": round(dist_km, 2),
                    "travel_time_min": travel_time_min
                }
    return lookup
