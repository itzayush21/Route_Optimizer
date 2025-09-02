import os
import re
import json
import math
import requests
import google.generativeai as genai
from dotenv import load_dotenv
load_dotenv()

# 🔑 Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
GOOGLE_CLOUD_API = os.getenv("GOOGLE_API_KEY")

# -------------------------------
# Distance Calculation
# -------------------------------
def haversine(lat1, lon1, lat2, lon2):
    """Great-circle distance (km)."""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat/2)**2 +
         math.cos(math.radians(lat1)) *
         math.cos(math.radians(lat2)) *
         math.sin(dlon/2)**2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

# -------------------------------
# Google Places API
# -------------------------------
def get_safe_rest_stops(lat, lon, radius=5000):
    """
    Fetch nearby hospitals, hotels, parking.
    Returns top 3 closest with name, type, address, distance_km.
    """
    if not GOOGLE_CLOUD_API:
        return []

    types = ["hospital", "lodging", "parking"]
    results = []

    for place_type in types:
        url = (
            f"https://maps.googleapis.com/maps/api/place/nearbysearch/json"
            f"?location={lat},{lon}&radius={radius}&type={place_type}&key={GOOGLE_CLOUD_API}"
        )
        res = requests.get(url).json()

        if res.get("status") == "OK":
            for place in res.get("results", []):
                name = place.get("name")
                address = place.get("vicinity", "Unknown")
                loc = place.get("geometry", {}).get("location", {})
                plat, plon = loc.get("lat"), loc.get("lng")
                dist = haversine(lat, lon, plat, plon)
                results.append({
                    "name": name,
                    "type": place_type,
                    "address": address,
                    "distance_km": round(dist, 2)
                })

    return sorted(results, key=lambda x: x["distance_km"])[:3]

# -------------------------------
# Payload Cleaning
# -------------------------------
def clean_payload(original_json):
    depot_lat, depot_lon = original_json["depot"]["lat"], original_json["depot"]["lon"]
    minimal = {"depot": {"id": original_json["depot"]["id"]}, "refined_routes": []}

    for route in original_json.get("refined_routes", []):
        minimal_seq = []
        for stop in route.get("sequence", []):
            stop_lat, stop_lon = stop["lat"], stop["lon"]
            minimal_stop = {
                "id": stop["id"],
                "distance_to_depot_km": round(
                    haversine(stop_lat, stop_lon, depot_lat, depot_lon), 2
                ),
                "nearby_safe_stops": get_safe_rest_stops(stop_lat, stop_lon)
            }
            minimal_seq.append(minimal_stop)

        minimal["refined_routes"].append({
            "vehicle": route["vehicle"],
            "sequence": minimal_seq
        })

    return minimal

def clean_response(raw_text: str) -> str:
    return re.sub(r"```(json|text)?", "", raw_text).strip()

# -------------------------------
# Main Dispatcher Function
# -------------------------------
def generate_fatigue_recommendation(
    vehicle_id: str,
    near_customer: str,
    note: str,
    route_json: dict,
    conversation: list
) -> dict:
    """
    Dispatcher-style fatigue/compliance recommendation with chat memory.
    Returns dict: {"recommendation": str, "conversation": updated_list}
    """
    minimal_json = clean_payload(route_json)
    minimal_str = json.dumps(minimal_json, indent=2)

    user_situation = f"Driver of Vehicle {vehicle_id} near customer {near_customer}. {note}"

    # Build conversation string
    conversation_str = "\n".join(
        [f"User: {c['user']}\nDispatcher: {c['dispatcher']}" for c in conversation]
    )

    # Enhanced prompt
    prompt = f"""
    You are an expert dispatcher in delivery operations.

    Expectation:
    - Continue the conversation logically, not just one-time advice.
    - Context JSON (routes, distances, rest stops) is provided.
    - Answer in dispatcher-style plain text.

    Conversation so far:
    {conversation_str}

    Current situation:
    {user_situation}

    Context JSON:
    {minimal_str}

    Guidelines:
    - Use `distance_to_depot_km` to decide if driver should return to depot.
    - Use `nearby_safe_stops` (hospitals, hotels, parking) for rest options.
    - Recommend one of these actions:
      (1) Return to depot,
      (2) Stop at safe rest stop,
      (3) Handover deliveries to other vehicles,
      (4) Reschedule deliveries.
    - Be practical, concise, and empathetic.
    - Do NOT output JSON, only plain dispatcher text.
    """

    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(prompt)
    recommendation = clean_response(response.text)

    # Update conversation history
    conversation.append({
        "user": user_situation,
        "dispatcher": recommendation
    })

    return {"recommendation": recommendation, "conversation": conversation}
