import google.generativeai as genai
import json
import re
import os
from dotenv import load_dotenv
load_dotenv()

# 🔑 Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def clean_response(raw_text: str) -> str:
    """Cleans Gemini response (removes markdown/code fences)."""
    return re.sub(r"```(json|text)?", "", raw_text).strip()

BASE_PROMPT = """
You are a professional trip planner and narrator.

Task:
Given a JSON description of ONE vehicle’s planned route (sequence of stops, nearby petrol stations, repair shops, traffic info),
write a **pre-trip description**.

Guidelines:
- Write in plain text, like advice for the driver before starting the journey.
- Begin by introducing the vehicle and its planned route (depot → customers → depot).
- Anticipate possible challenges: traffic levels, road conditions, long stretches without stops.
- Provide clear **warnings** (e.g., heavy traffic expected, limited repair shops nearby).
- Suggest **preparation tips** (e.g., fuel up at certain stations, note closest repair shops).
- Keep it practical and driver-focused: "Better to have X", "Make sure Y before departure".
- Avoid JSON or markdown in the response.
"""

def generate_trip_descriptions(routes_json: dict) -> str:
    """
    Generates a driver-friendly trip description for each vehicle.
    Returns one combined string (can also split per vehicle if needed).
    """
    model = genai.GenerativeModel("gemini-1.5-flash")
    trip_description = ""

    for route in routes_json.get("refined_routes", []):
        vehicle_id = route.get("vehicle")
        vehicle_data_str = json.dumps(route, indent=2)

        response = model.generate_content(
            [
                BASE_PROMPT,
                f"Here is the route for vehicle {vehicle_id}:\n{vehicle_data_str}"
            ]
        )
        text = clean_response(response.text)
        trip_description += f"\n\n=== Vehicle {vehicle_id} Trip Description ===\n{text}"

    return trip_description
