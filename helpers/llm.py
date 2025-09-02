import google.generativeai as genai
import json
import re

genai.configure(api_key="AIzaSyDgXXIWAQbUeBQHBU03V6pkv3tuV1OWuUc")


def build_prompt_from_payload(payload):
    instr = (
        "You are an AI co-planner collaborating with OR-Tools.\n"
        "OR-Tools has already generated baseline routes that satisfy feasibility "
        "(vehicle capacity, time windows, depot constraints).\n"
        "Your role: refine and reorder routes based on traffic context and human preferences.\n\n"

        "Return ONLY valid JSON, following this schema exactly:\n"
        "{\n"
        '  "depot": {"id": "<string>", "lat": <float>, "lon": <float>},\n'
        '  "refined_routes": [\n'
        '    {\n'
        '      "vehicle": "<string>",\n'
        '      "sequence": [ {"id": "<string>", "lat": <float>, "lon": <float>} ],\n'
        '      "metrics": {\n'
        '        "traffic_level": "<low|medium|high>",\n'
        '        "road_condition": "<good|moderate|bad>",\n'
        '        "notes": "<string>"\n'
        '      }\n'
        '    }\n'
        '  ]\n'
        "}\n\n"

        "⚠️ Rules:\n"
        "1. Do NOT remove depot start/end; every route begins and ends at depot.\n"
        "2. Keep baseline feasibility: do not violate capacity or time windows.\n"
        "3. Apply preferences from 'user_preferences':\n"
        "   - priority_customers → must appear earlier in sequences.\n"
        "   - avoid_zones → minimize or skip routes through those local authorities.\n"
        "   - fairness → balance load across vehicles when possible.\n"
        "   - eco_mode → prefer shorter, less congested routes.\n"
        "4. Use traffic context from customers (road_type, traffic_density, hgvs_pct):\n"
        "   - High traffic_density → longer travel times.\n"
        "   - High hgvs_pct → worse road_condition.\n"
        "5. Output must be clean JSON only (no commentary, no markdown).\n"
    )
    return instr + "\n\nINPUT:\n" + json.dumps(payload, indent=2)

def call_llm(payload, model_name="gemini-1.5-flash", max_tokens=3000):
    model = genai.GenerativeModel(model_name)
    prompt = build_prompt_from_payload(payload)
    response = model.generate_content(prompt, generation_config={"temperature":0.0,"max_output_tokens":max_tokens})
    return response.text

def extract_json(raw_text: str) -> str:
    cleaned = re.sub(r"```(json)?", "", raw_text).strip()
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    return match.group(0).strip() if match else "{}"
