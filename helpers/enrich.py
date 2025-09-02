from sklearn.neighbors import BallTree
import numpy as np
from haversine import haversine

def build_countpoint_tree(df3):
    coords = np.radians(df3[["latitude","longitude"]].values)
    return BallTree(coords, metric="haversine")

def match_to_countpoint(customer, df3, tree):
    lat, lon = customer["lat"], customer["lon"]
    dist, idx = tree.query(np.radians([[lat, lon]]), k=1)
    idx = int(idx[0][0])
    row = df3.iloc[idx]
    return row.to_dict(), float(dist[0][0]) * 6371.0  # convert radians → km


def enrich_customers(customers, df1, df2, df3, user_prefs=None):
    """
    Enrich customers with traffic + contextual metadata.
    Includes:
      - Nearest countpoint (micro traffic)
      - Local authority stats (city-level congestion)
      - Region stats (macro mobility, HGV composition)
      - Slot → time_window (usable by OR-Tools)
      - User preference signals (priority, avoid_zones, eco_mode)
    """
    tree = build_countpoint_tree(df3)

    # Normalize join keys
    df1["local_authority_name"] = df1["local_authority_name"].str.strip().str.lower()
    df2["region_name"] = df2["region_name"].str.strip().str.lower()
    df3["local_authority_name"] = df3["local_authority_name"].str.strip().str.lower()
    df3["region_name"] = df3["region_name"].str.strip().str.lower()

    # Slot → numeric minutes
    slot_windows = {
        "Morning": [480, 720],      # 08:00–12:00
        "Afternoon": [720, 1020],   # 12:00–17:00
        "Evening": [1020, 1260],    # 17:00–21:00
        "Anytime": [480, 1080]      # 08:00–18:00
    }

    enriched = []
    for c in customers:
        row_dict, dist_km = match_to_countpoint(c, df3, tree)
        la_name = str(row_dict.get("local_authority_name", "")).lower()
        reg_name = str(row_dict.get("region_name", "")).lower()

        # --- df1 (local authority) → traffic density
        traffic_density = None
        if la_name in df1["local_authority_name"].values:
            la_data = df1[df1["local_authority_name"] == la_name].iloc[0]
            if la_data.get("link_length_km", 0) > 0:
                traffic_density = la_data["all_motor_vehicles"] / la_data["link_length_km"]

        # --- df2 (region) → HGV share
        hgvs_pct = None
        if reg_name in df2["region_name"].values:
            reg_data = df2[df2["region_name"] == reg_name]
            total_mv = reg_data["all_motor_vehicles"].sum()
            if total_mv > 0:
                hgvs_pct = reg_data["all_hgvs"].sum() / total_mv

        # --- Predicted travel speed (derived feature) ---
        road_type = str(row_dict.get("road_type", "")).lower()
        expected_speed = 40.0  # default baseline

        if "motorway" in road_type:
            expected_speed = 70.0
        elif "a road" in road_type:
            expected_speed = 50.0
        elif "b road" in road_type:
            expected_speed = 40.0
        elif "minor" in road_type:
            expected_speed = 30.0

        # Adjust for congestion / heavy vehicles
        if traffic_density and traffic_density > 2e6:
            expected_speed *= 0.7
        if hgvs_pct and hgvs_pct > 0.25:
            expected_speed *= 0.8

        # --- Slot → time_window in minutes
        slot_label = c.get("slot_label", "Anytime")
        time_window = slot_windows.get(slot_label, slot_windows["Anytime"])

        # --- User preferences (context-aware AI input)
        priority = "normal"
        if user_prefs:
            if c["customer_id"] in user_prefs.get("priority_customers", []):
                priority = "high"
            avoid_zones = [z.lower() for z in user_prefs.get("avoid_zones", [])]
            if la_name in avoid_zones or reg_name in avoid_zones:
                priority = "avoid"

        enriched.append({
            "customer_id": c["customer_id"],
            "lat": c["lat"], "lon": c["lon"],
            "time_window": time_window,
            "weight": float(c.get("weight", 0)),

            "region": reg_name,
            "local_authority": la_name,
            "road_type": road_type,
            "nearest_count_point": row_dict.get("count_point_id"),
            "dist_to_countpoint_km": round(dist_km, 2),

            "traffic_hourly": row_dict.get("all_motor_vehicles"),
            "traffic_density": traffic_density,
            "hgvs_pct": hgvs_pct,
            "expected_speed_kmph": round(expected_speed, 1),

            "priority": priority
        })

    return enriched
