import google.generativeai as genai
import json
import re
import os
from dotenv import load_dotenv
load_dotenv()

# 🔑 Configure Gemini API once
API_KEY = os.getenv("GEMINI_API_KEY", "YOUR_DEFAULT_KEY")
genai.configure(api_key=API_KEY)

def extract_json(raw_text: str) -> str:
    """
    Cleans LLM response and extracts valid JSON.
    Removes markdown fences and captures the first JSON object.
    """
    cleaned = re.sub(r"```(json)?", "", raw_text).strip()
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    return match.group(0).strip() if match else "{}"

def make_json_safe(obj):
    """Recursively make an object JSON serializable by converting tuple keys to strings."""
    if isinstance(obj, dict):
        safe_dict = {}
        for k, v in obj.items():
            if isinstance(k, tuple):
                k = "_".join(map(str, k))   # turn tuple into "a_b"
            else:
                k = str(k)
            safe_dict[k] = make_json_safe(v)
        return safe_dict
    elif isinstance(obj, list):
        return [make_json_safe(x) for x in obj]
    elif isinstance(obj, tuple):
        return "_".join(map(str, obj))  # convert tuple values too
    else:
        return obj



def reroute_with_traffic(traffic_routes: dict, traffic_matrix: dict) -> dict:
    """
    Calls Gemini with traffic-aware routes + traffic matrix and returns rerouted plan.
    """

    # ✅ Ensure JSON serializable
    traffic_routes_str = json.dumps(make_json_safe(traffic_routes), indent=2)
    traffic_matrix_str = json.dumps(make_json_safe(traffic_matrix), indent=2)
    print("Traffic matrix JSON prepared.")
    prompt = """
    You are an expert in logistics optimization and real-time traffic-aware vehicle routing.

    I will provide two JSON files:
    1. `traffic_routes` – a route plan enriched with real-time traffic durations per vehicle.
    2. `traffic_matrix` – a cache of detailed pairwise travel times between all origins and destinations
       (from Google Distance Matrix API).

    Your tasks:
    - Analyze the current `traffic_routes` plan and see how traffic impacts each vehicle's journey.
    - Use the `traffic_matrix` to check whether reordering stops or reassigning customers could reduce delays.
    - Propose an improved routing plan that minimizes total travel time while respecting:
      - Every customer must be served exactly once.
      - Each vehicle starts and ends at the depot.
      - Avoid unbalanced loads (don’t overburden one vehicle).

    Output strictly in JSON (no explanations, no markdown).
    """

    model = genai.GenerativeModel("gemini-1.5-flash")

    response = model.generate_content(
        [
            prompt,
            f"Here is traffic_routes JSON:\n{traffic_routes_str}\n\n"
            f"Here is traffic_matrix JSON:\n{traffic_matrix_str}"
        ]
    )

    cleaned_json_str = extract_json(response.text)
    return json.loads(cleaned_json_str)
