import os
import re
import json
import google.generativeai as genai
from dotenv import load_dotenv
load_dotenv()

# 🔑 Configure Gemini once
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

import math

def haversine(lat1, lon1, lat2, lon2):
    """Calculate great-circle distance (km) between two coordinates."""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat/2)**2 +
         math.cos(math.radians(lat1)) *
         math.cos(math.radians(lat2)) *
         math.sin(dlon/2)**2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def clean_payload(original_json: dict):
    """
    Reduce JSON payload:
    - Keep depot
    - For each vehicle sequence: keep id only
    - For nearby repair shops: keep name, address, and distance (from stop)
    """
    depot = original_json.get("depot", {})
    minimal = {"depot": {"id": depot.get("id")}, "refined_routes": []}

    for route in original_json.get("refined_routes", []):
        minimal_seq = []
        for stop in route.get("sequence", []):
            minimal_stop = {"id": stop.get("id")}

            # Repair shops with computed distance
            if "nearby_repair_shops" in stop:
                rs_list = []
                for rs in stop["nearby_repair_shops"]:
                    dist_km = haversine(
                        stop.get("lat"), stop.get("lon"),
                        rs.get("lat"), rs.get("lon")
                    )
                    rs_list.append({
                        "name": rs["name"],
                        "address": rs["address"],
                        "distance_km": round(dist_km, 2)
                    })
                minimal_stop["nearby_repair_shops"] = rs_list

            minimal_seq.append(minimal_stop)

        minimal["refined_routes"].append({
            "vehicle": route.get("vehicle"),
            "sequence": minimal_seq
        })

    return minimal


def clean_response(raw_text: str) -> str:
    """Clean Gemini response (remove code fences, markdown)."""
    return re.sub(r"```(json|text)?", "", raw_text).strip()

def generate_situation_recommendation(vehicle_id: str, near_customer: str, note: str, route_json: dict,history=None) -> str:
    """
    Main dispatcher recommendation generator.
    - vehicle_id: e.g., "V2"
    - near_customer: e.g., "C079"
    - note: free text
    - route_json: route_detail from DB
    Returns plain text recommendation.
    """
    minimal_json = clean_payload(route_json)
    minimal_str = json.dumps(minimal_json, indent=2)
    print(minimal_str)
    # Build user situation
    user_situation = f"Vehicle {vehicle_id} reported near customer {near_customer}. {note}"

    # Build conversation
    messages = history or []
    messages.append({"role": "user", "content": user_situation})

    # Flatten into prompt
    conversation_str = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in messages])

    prompt = f"""
You are an expert vehicle routing dispatcher and mentor.

Expectations
- Continue an ongoing dispatcher conversation using both the conversation history and the compact JSON of current routes/stops.
- Sound like a human dispatcher: direct, practical, empathetic, and operational (short radio / shift-room style).

You have access to:
- Conversation so far: {conversation_str}
- Current user situation (if provided): {user_situation}
- Compact context JSON (depot, vehicles, customers, distances, stops): {minimal_str}

Decision rules & data to use
- Use `distance_to_depot_km` to decide if a driver should return to depot.
- Use `nearby_safe_stops` (hospitals, hotels, secure parking, petrol stations) for rest/refuel/repair options.
- Consider traffic, vehicle load, vehicle condition, ETA windows, and nearest repair shops when forming recommendations.

Primary actions (choose one as the main recommendation; you may add a short secondary action):
1) Return to depot
2) Stop at a safe rest stop
3) Handover deliveries to another vehicle
4) Reschedule deliveries
Also consider: reroute, refuel, wait, escalate to repair/emergency.

Guidelines for output
- Output ONLY plain text. Do NOT output JSON, code, tables, or markdown.
- Keep it concise and actionable — radio-style lines or very short paragraphs.
- Always explain reasoning in dispatcher terms (e.g., "V2 is 3.2 km from C079 and nearly empty, so handover is fastest").
- Always suggest nearest repair shops when vehicle fault or road conditions are mentioned.
- Balance safety, fairness, and efficiency — do not overload one vehicle.
- If no viable reroute or handover exists, state that clearly and propose alternatives (reschedule, return to depot).
- If required input is missing or ambiguous (missing vehicle locations, loads, traffic), ask ONE focused clarifying question before making major recommendations.

Tone
- Practical, concise, empathetic, and authoritative — like a senior dispatcher on the radio.

Final output format
- Plain dispatcher-style advice that the logistics manager can act on immediately (1–6 short lines).
"""



    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content([prompt])
    return clean_response(response.text)