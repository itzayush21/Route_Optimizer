import re
import google.generativeai as genai
import json

def extract_json(raw_text: str) -> str:
    cleaned = re.sub(r"```(json)?", "", raw_text).strip()
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    return match.group(0).strip() if match else "{}"

def get_user_preferences(user_input: str, model_name="gemini-1.5-flash"):
    """
    Use LLM to infer user preferences (priority customers, avoid zones, fairness, eco_mode).
    Fallback = {} if LLM fails.
    """
    prompt = f"""
    You are a logistics assistant.
    Input: "{user_input}"

    Task: Convert this into a clean JSON preference object with keys:
    {{
      "priority_customers": [list of customer IDs or []],
      "avoid_zones": [list of region/local authority names or []],
      "fairness": true/false,
      "eco_mode": true/false
    }}

    Rules:
    - Output only valid JSON (no markdown, no commentary).
    - Use [] for empty lists.
    """

    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt, generation_config={"temperature":0.0, "max_output_tokens":500})
        raw_text = response.text
        parsed = extract_json(raw_text)
        return json.loads(parsed)
    except Exception as e:
        print("⚠️ Preference LLM call failed, using fallback:", e)
        return {}
