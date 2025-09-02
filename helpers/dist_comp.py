import numpy as np
from haversine import haversine

# -------------------------
# 2) Distance Matrix + OR-Tools baseline (enhanced)
# -------------------------
def compute_distance_matrix(depot, customers, base_speed_kmph=40):
    """
    Compute pairwise distance matrix (km) and baseline travel time (sec).

    Args:
        depot (dict): {id, lat, lon}
        customers (list): list of customer dicts with lat/lon
        base_speed_kmph (float): assumed average speed for conversion

    Returns:
        dist_matrix (np.ndarray): distance matrix [n x n] in km
        time_matrix (np.ndarray): travel time matrix [n x n] in seconds
        node_ids (list): index → node_id (DEPOT + customers)
    """
    points = [("DEPOT", depot["lat"], depot["lon"])] + [
        (c["customer_id"], c["lat"], c["lon"]) for c in customers
    ]
    size = len(points)

    dist_matrix = np.zeros((size, size))
    time_matrix = np.zeros((size, size))
    node_ids = [pid for pid, _, _ in points]

    for i, (id_i, lat_i, lon_i) in enumerate(points):
        for j, (id_j, lat_j, lon_j) in enumerate(points):
            if i == j:
                dist_matrix[i][j] = 0.0
                time_matrix[i][j] = 0.0
            else:
                dist_km = haversine((lat_i, lon_i), (lat_j, lon_j))
                dist_matrix[i][j] = dist_km
                # Convert to time (sec) using baseline avg speed
                travel_time_hr = dist_km / base_speed_kmph if base_speed_kmph > 0 else 0
                time_matrix[i][j] = travel_time_hr * 3600

    return dist_matrix, time_matrix, node_ids
