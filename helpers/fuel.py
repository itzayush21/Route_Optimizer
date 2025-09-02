import os
import re
import json
import math
import google.generativeai as genai
from dotenv import load_dotenv
load_dotenv()

# 🔑 Configure Gemini once
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# -------------------------------
# Distance Calculation
# -------------------------------
def haversine(lat1, lon1, lat2, lon2):
    """Calculate great-circle distance (km) between two coordinates."""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) *
         math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

# -------------------------------
# Compact Payload
# -------------------------------
def clean_payload(original_json: dict) -> dict:
    """
    Reduce JSON payload:
    - Keep depot
    - For each vehicle sequence: keep id, lat, lon
    - For nearby stations/shops: keep name, address, and distance (km)
    """
    minimal = {"depot": original_json.get("depot"), "refined_routes": []}

    for route in original_json.get("refined_routes", []):
        minimal_seq = []
        for stop in route.get("sequence", []):
            minimal_stop = {
                "id": stop.get("id"),
                "lat": stop.get("lat"),
                "lon": stop.get("lon"),
            }

            # Petrol stations
            if "nearby_petrol_stations" in stop:
                ps_list = []
                for ps in stop["nearby_petrol_stations"]:
                    dist_km = haversine(stop["lat"], stop["lon"], ps["lat"], ps["lon"])
                    ps_list.append({
                        "name": ps["name"],
                        "address": ps["address"],
                        "distance_km": round(dist_km, 2),
                    })
                minimal_stop["nearby_petrol_stations"] = ps_list

            # Repair shops
            if "nearby_repair_shops" in stop:
                rs_list = []
                for rs in stop["nearby_repair_shops"]:
                    dist_km = haversine(stop["lat"], stop["lon"], rs["lat"], rs["lon"])
                    rs_list.append({
                        "name": rs["name"],
                        "address": rs["address"],
                        "distance_km": round(dist_km, 2),
                    })
                minimal_stop["nearby_repair_shops"] = rs_list

            minimal_seq.append(minimal_stop)

        minimal["refined_routes"].append({
            "vehicle": route.get("vehicle"),
            "sequence": minimal_seq,
        })

    return minimal

# -------------------------------
# Response Cleaner
# -------------------------------
def clean_response(raw_text: str) -> str:
    """Clean Gemini response (remove code fences, markdown, etc)."""
    return re.sub(r"```(json|text)?", "", raw_text).strip()

# -------------------------------
# Main Fuel Management Recommender
# -------------------------------
def generate_fuel_recommendation(vehicle_id: str, near_customer: str, note: str, route_json: dict, conversation: list = None) -> dict:
    """
    Generate dispatcher-style recommendation for fuel/energy issues as a chat.
    
    Params:
    - vehicle_id: "V1", "V2", etc.
    - near_customer: "C079", etc.
    - note: user note describing the situation
    - route_json: full route JSON from DB
    - conversation: list of previous chat turns (optional)
    
    Returns:
    {
        "recommendation": str,   # Gemini response in plain text
        "conversation": list     # updated conversation history
    }
    """
    minimal_json = clean_payload(route_json)
    minimal_str = json.dumps(minimal_json, indent=2)

    # Situation description
    user_situation = f"Vehicle {vehicle_id} reported near customer {near_customer}. {note}"

    # Start or extend conversation
    if conversation is None:
        conversation = []
    conversation.append({"role": "user", "content": user_situation})

    # Format conversation string for Gemini
    conversation_str = "\n".join(
        f"{turn['role'].capitalize()}: {turn['content']}" for turn in conversation
    )

    # Enhanced dispatcher prompt
    prompt = f"""
    You are an expert dispatcher in delivery operations.

    Expectation:
    - Continue the conversation naturally, as if you are advising live.
    - Always answer in plain text (no JSON, no markdown).
    - Recommendations should be actionable, short, and practical.
    - Focus on: nearby petrol stations, depot distance, reassignment if needed.

    Conversation so far:
    {conversation_str}

    Context JSON (for calculations):
    {minimal_str}
    """

    # Call Gemini
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content([prompt])

    recommendation = clean_response(response.text)
    conversation.append({"role": "assistant", "content": recommendation})

    return {
        "recommendation": recommendation,
        "conversation": conversation
    }
