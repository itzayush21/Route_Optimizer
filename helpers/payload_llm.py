def make_payload_for_llm(depot, routes, distance_lookup, customers_info, preferences):
    """
    Build payload for LLM-based route refinement.
    depot: dict {id, lat, lon}
    routes: output from OR-Tools (list of dicts, each with 'route': [...])
    distance_lookup: dict with {"order": [...], "distances_km": [...], "times_min": [...]}
    customers_info: dict {cid: {...}} or list of {...}
    preferences: dict of user preferences
    """

    # Ensure preferences has default structure
    preferences = preferences or {}
    preferences.setdefault("priority_customers", [])
    preferences.setdefault("avoid_zones", [])
    preferences.setdefault("fairness", False)
    preferences.setdefault("eco_mode", False)

    # Convert customers_info → list
    if isinstance(customers_info, dict):
        customers = []
        for cid, data in customers_info.items():
            cust = {"customer_id": cid}
            cust.update(data)
            customers.append(cust)
    else:
        customers = list(customers_info)

    # Update customer priorities from preferences
    for cust in customers:
        if cust["customer_id"] in preferences["priority_customers"]:
            cust["priority"] = "high"

    payload = {
        "task": "route_refinement",
        "depot": depot,
        "baseline_routes": [],
        "customers": customers,
        "distance_matrix": distance_lookup,
        "user_preferences": preferences,
    }

    # Always include all vehicles (even if unused)
    for i, r in enumerate(routes):
        if isinstance(r, dict) and "route" in r:
            baseline_entry = {
                "vehicle": f"V{i+1}",
                "sequence": r.get("route", []),
                "load": r.get("load", 0),
                "total_distance_km": r.get("total_distance_km", 0),
                "fuel_used_l": r.get("fuel_used_l", 0),
                "fuel_cost": r.get("fuel_cost", 0),
            }
        else:
            # fallback if routes are just lists of customers
            seq = [c["customer_id"] if isinstance(c, dict) else c for c in r]
            baseline_entry = {
                "vehicle": f"V{i+1}",
                "sequence": seq,
                "load": 0,
                "total_distance_km": 0,
                "fuel_used_l": 0,
                "fuel_cost": 0,
            }

        payload["baseline_routes"].append(baseline_entry)

    return payload
