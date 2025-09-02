import requests
import datetime
import json
import os

def get_matrix_durations(origins, destinations, api_key):
    """
    Calls Google Distance Matrix API for multiple origin-destination pairs.
    Returns dict { (origin, destination): {"normal": secs, "traffic": secs} }
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
                    normal = element["duration"]["value"]  # seconds
                    traffic = element.get("duration_in_traffic", element["duration"])["value"]
                else:
                    normal, traffic = 0, 0
                result[(origin, destination)] = {
                    "normal": normal,
                    "traffic": traffic
                }
    else:
        print("⚠️ Matrix Error:", res.get("status"), res.get("error_message"))

    return result


def add_traffic_durations(routes_json: dict, api_key: str, cache_file="distance_cache.json"):
    """
    Enriches routes_json with normal + traffic durations (mins/secs).
    Uses cache to avoid repeated API calls.
    """


    distance_cache = {}

    # Step 1: collect all unique pairs
    pairs_needed = set()
    for route in routes_json["refined_routes"]:
        seq = route["sequence"]
        for i in range(len(seq) - 1):
            origin = (seq[i]["lat"], seq[i]["lon"])
            destination = (seq[i+1]["lat"], seq[i+1]["lon"])
            pairs_needed.add((origin, destination))

    # Step 2: find missing pairs
    pairs_to_query = [pair for pair in pairs_needed if pair not in distance_cache]

    # Step 3: query API if needed
    if pairs_to_query:
        unique_points = {pt for pair in pairs_to_query for pt in pair}
        unique_points = list(unique_points)

        new_durations = get_matrix_durations(unique_points, unique_points, api_key)
        distance_cache.update(new_durations)

    # Step 4: attach durations to each route
    for route in routes_json["refined_routes"]:
        total_normal_duration = 0
        total_traffic_duration = 0
        seq = route["sequence"]

        for i in range(len(seq) - 1):
            origin = (seq[i]["lat"], seq[i]["lon"])
            destination = (seq[i+1]["lat"], seq[i+1]["lon"])
            durations = distance_cache.get((origin, destination), {"normal": 0, "traffic": 0})

            if isinstance(durations, int):
                normal_val = durations
                traffic_val = durations
            else:
                normal_val = durations.get("normal", 0)
                traffic_val = durations.get("traffic", 0)

            total_normal_duration += normal_val
            total_traffic_duration += traffic_val

        # Add to metrics
        route.setdefault("metrics", {})
        route["metrics"]["total_normal_duration_secs"] = total_normal_duration
        route["metrics"]["total_normal_duration_mins"] = round(total_normal_duration / 60, 2)
        route["metrics"]["total_traffic_duration_secs"] = total_traffic_duration
        route["metrics"]["total_traffic_duration_mins"] = round(total_traffic_duration / 60, 2)

    # Save updated cache
    with open(cache_file, "w") as f:
        json.dump({str(k): v for k, v in distance_cache.items()}, f, indent=2)

    return routes_json, distance_cache