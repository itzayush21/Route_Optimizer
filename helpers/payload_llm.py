def make_payload_for_llm(depot, routes, distance_lookup, customers_info, preferences):
    """
    Build payload for LLM-based route refinement.
    depot: dict {id, lat, lon}
    routes: list of lists of customers [{customer_id,...}]
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
        customers = list(customers_info)  # already a list

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
        payload["baseline_routes"].append({
            "vehicle": f"V{i+1}",
            "sequence": [c["customer_id"] for c in r]
        })

    return payload
