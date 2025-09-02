import requests

def get_nearby_places(lat, lng, place_type, api_key, radius=5000, limit=2):
    """
    Fetch nearby places (petrol stations, repair shops, etc.)
    Returns a list of dicts with name, lat, lon, address
    """
    url = (
        "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
        f"?location={lat},{lng}"
        f"&radius={radius}"
        f"&type={place_type}"
        f"&key={api_key}"
    )
    res = requests.get(url).json()
    places = []
    if res.get("status") == "OK":
        for place in res.get("results", [])[:limit]:
            loc = place.get("geometry", {}).get("location", {})
            places.append({
                "name": place.get("name"),
                "address": place.get("vicinity"),
                "lat": loc.get("lat"),
                "lon": loc.get("lng")
            })
    return places


def enrich_with_support_stations(routes_json: dict, api_key: str, radius=3000, limit=2):
    """
    Enriches each node in routes_json with nearby petrol stations & repair shops.
    """
    for route in routes_json.get("refined_routes", []):
        for node in route.get("sequence", []):
            lat, lon = node["lat"], node["lon"]

            petrol_stations = get_nearby_places(lat, lon, "gas_station", api_key, radius, limit)
            repair_shops = get_nearby_places(lat, lon, "car_repair", api_key, radius, limit)

            node["nearby_petrol_stations"] = petrol_stations
            node["nearby_repair_shops"] = repair_shops

    return routes_json
