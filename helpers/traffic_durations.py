import requests
import datetime
import json
import os

def get_matrix_durations(origins, destinations, api_key):
    """
    Calls Google Distance Matrix API for multiple origin-destination pairs.
    Returns dict { "lat1,lon1|lat2,lon2": {"normal": secs, "traffic": secs} }
    """
    departure_time = int(datetime.datetime.now().timestamp())
    origins_str = "|".join([f"{lat},{lon}" for lat, lon in origins])
    destinations_str = "|".join([f"{lat},{lon}" for lat, lon in destinations])

    url = (
        "https://maps.googleapis.com/maps/api/distancematrix/json"
        f"?origins={origins_str}"
        f"&destinations={destinations_str}"
        f"&departure_time={departure_time}"
        f"&traffic_model=best_guess"
        f"&mode=driving"
        f"&key={api_key}"
    )

    res = requests.get(url).json()
    result = {}

    if res.get("status") == "OK":
        for i, origin in enumerate(origins):
            for j, destination in enumerate(destinations):
                element = res["rows"][i]["elements"][j]
                if element.get("status") == "OK":
                    normal = element["duration"]["value"]
                    traffic = element.get("duration_in_traffic", element["duration"])["value"]
                else:
                    normal, traffic = 0, 0

                # ✅ JSON-safe key
                key = f"{origin[0]},{origin[1]}|{destination[0]},{destination[1]}"
                result[key] = {"normal": normal, "traffic": traffic}
    else:
        print("⚠️ Matrix Error:", res.get("status"), res.get("error_message"))

    return result


def add_traffic_durations(routes_json: dict, api_key: str):
    """
    Enriches routes_json with normal + traffic durations (mins/secs).
    No caching — everything fresh per call.
    """
    distance_lookup = {}

    # Collect all pairs
    pairs_needed = set()
    for route in routes_json["refined_routes"]:
        seq = route["sequence"]
        for i in range(len(seq) - 1):
            origin = (seq[i]["lat"], seq[i]["lon"])
            destination = (seq[i+1]["lat"], seq[i+1]["lon"])
            key = f"{origin[0]},{origin[1]}|{destination[0]},{destination[1]}"
            pairs_needed.add((origin, destination, key))

    if pairs_needed:
        unique_points = {pt for (origin, dest, key) in pairs_needed for pt in (origin, dest)}
        unique_points = list(unique_points)

        # Fetch new durations
        distance_lookup = get_matrix_durations(unique_points, unique_points, api_key)

    # Attach durations to routes
    for route in routes_json["refined_routes"]:
        total_normal = 0
        total_traffic = 0
        seq = route["sequence"]

        for i in range(len(seq) - 1):
            origin = (seq[i]["lat"], seq[i]["lon"])
            destination = (seq[i+1]["lat"], seq[i+1]["lon"])
            key = f"{origin[0]},{origin[1]}|{destination[0]},{destination[1]}"
            durations = distance_lookup.get(key, {"normal": 0, "traffic": 0})

            total_normal += durations.get("normal", 0)
            total_traffic += durations.get("traffic", 0)

        route.setdefault("metrics", {})
        route["metrics"]["total_normal_duration_secs"] = total_normal
        route["metrics"]["total_normal_duration_mins"] = round(total_normal / 60, 2)
        route["metrics"]["total_traffic_duration_secs"] = total_traffic
        route["metrics"]["total_traffic_duration_mins"] = round(total_traffic / 60, 2)
        
    print(routes_json)
    print(distance_lookup)

    return routes_json, distance_lookup
