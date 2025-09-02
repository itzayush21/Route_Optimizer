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

    # Build user situation
    user_situation = f"Vehicle {vehicle_id} reported near customer {near_customer}. {note}"

    # Build conversation
    messages = history or []
    messages.append({"role": "user", "content": user_situation})

    # Flatten into prompt
    conversation_str = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in messages])

    prompt = f"""
You are an expert vehicle routing dispatcher and mentor.
Your role is to help logistics managers handle real-world disruptions and make safe, practical routing decisions.

=== Expectations ===
- You are continuing an **ongoing conversation** with the user (dispatcher chat).
- Your answers must **sound like a human dispatcher** giving real advice, not a computer.
- You have access to:
  1. The conversation so far.
  2. A compact JSON of current routes and stops (with depot, vehicles, and customers).
- You are expected to combine both when giving advice.

=== Conversation so far ===
{conversation_str}

=== Current Context (JSON) ===
{minimal_str}

=== Guidelines ===
- Respond in **plain text only** (never output JSON, tables, or code).
- Give **actionable advice** the manager can directly follow (reroute, assign, wait, stop, refuel).
- Always explain your **reasoning in dispatcher terms** (e.g., “V2 is closer to C079, so hand over this delivery”).
- Balance safety, fairness, and efficiency — never overload one vehicle.
- If no good reroute exists, say so clearly and suggest alternatives (e.g., reschedule deliveries, return to depot).
- Keep responses **short, clear, and operational** (like radio or shift-room advice).
- If user input is unclear, **ask clarifying questions** before making recommendations.

=== Your Output Format ===
- Always plain text.
- Direct, practical, dispatcher-style advice.
- No JSON, no markdown, no code.
"""


    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content([prompt])
    return clean_response(response.text)