from flask import Flask, jsonify, request
from auth.auth_client import create_supabase_client
from config import Config
from model import db, Customer, Order, User, Route, Node
from datetime import datetime
import pandas as pd
import json, os, uuid, jwt
from dotenv import load_dotenv
from functools import wraps
from sqlalchemy import desc
from flask_cors import CORS
from haversine import haversine, Unit

# Helpers
from helpers.ortools import ortools_vrp
from helpers.enrich import enrich_customers
from helpers.dist_look import build_distance_lookup
from helpers.user_pref import get_user_preferences
from helpers.payload_llm import make_payload_for_llm
from helpers.llm import call_llm, extract_json
from helpers.traffic_durations import add_traffic_durations
from helpers.traffic_reroute import reroute_with_traffic
from helpers.nearby_places import enrich_with_support_stations
from helpers.trip_description import generate_trip_descriptions
from helpers.breakage import generate_situation_recommendation
from helpers.fuel import generate_fuel_recommendation
from helpers.fatigue import generate_fatigue_recommendation
from helpers.s3_bucket import read_csv_from_s3

load_dotenv()

# ------------------------------------------------
# 🔧 Flask App Setup
# ------------------------------------------------
app = Flask(__name__)
CORS(app, origins=[
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://10.53.178.140:5173",
    "https://d2wzvctg4ipy6w.cloudfront.net/"
], allow_headers=["Content-Type", "Authorization"])

S3_BUCKET = os.getenv("S3_BUCKET_NAME", "your-bucket-name")
app.config["SQLALCHEMY_DATABASE_URI"] = Config.DB_URI
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = Config.ENGINE_OPTIONS
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Supabase client
supabase = create_supabase_client()

# Supabase JWT secret (get this from Supabase Project Settings → API)
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")


# ------------------------------------------------
# 🔐 JWT Auth Middleware
# ------------------------------------------------
import jwt
from flask import request, jsonify

SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")  # from env

# ------------------------------------------------
# 🔐 JWT Auth Middleware
# ------------------------------------------------
from functools import wraps
from flask import request, jsonify
import jwt

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        print("Auth header:", auth_header)
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid Authorization header"}), 401

        token = auth_header.split(" ")[1]
        try:
            decoded = jwt.decode(
                token,
                SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                options={"verify_aud": False},   # 👈 disable audience check
                leeway=180
            )
            # Attach user_id from JWT into request context
            request.user_id = decoded.get("sub")  # Supabase UID
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except Exception as e:
            print("JWT decode error:", e)
            return jsonify({"error": "Invalid token"}), 401

        # If valid, continue
        return f(*args, **kwargs)
    return decorated

def parse_int(val, default=None, name=None, min_value=None, max_value=None):
    if val is None or (isinstance(val, str) and val.strip() == ""):
        return default
    try:
        iv = int(float(val))   # accepts "3", "3.0", 3.0, 3
    except Exception:
        raise ValueError(f"Invalid integer for {name}: {val!r}")
    if min_value is not None and iv < min_value:
        raise ValueError(f"{name} must be >= {min_value}")
    if max_value is not None and iv > max_value:
        raise ValueError(f"{name} must be <= {max_value}")
    return iv

def parse_float(val, default=None, name=None, min_value=None, max_value=None):
    if val is None or (isinstance(val, str) and val.strip() == ""):
        return default
    try:
        fv = float(val)
    except Exception:
        raise ValueError(f"Invalid float for {name}: {val!r}")
    if min_value is not None and fv < min_value:
        raise ValueError(f"{name} must be >= {min_value}")
    if max_value is not None and fv > max_value:
        raise ValueError(f"{name} must be <= {max_value}")
    return fv


# ------------------------------------------------
# 🔑 Auth Endpoints
# ------------------------------------------------

@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "status": "ok",
        "message": "Welcome to the VRP Backend API 🚀",
        "available_endpoints": ["/api/signup", "/api/login", "/api/logout"]
    })

@app.route('/api/signup', methods=['POST'])
def signup():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")
    warehouse = data.get("warehouse") or "Default Warehouse"
    phone = data.get("phone")

    res = supabase.auth.sign_up({"email": email, "password": password})

    if res.user:
        existing_user = User.query.filter_by(user_id=res.user.id).first()
        if not existing_user:
            new_user = User(
                user_id=res.user.id,
                warehouse=warehouse,
                phone=phone,
                created_at=datetime.utcnow()
            )
            db.session.add(new_user)
            db.session.commit()
        
        
        return jsonify({
            "status": "success",
            "user": {"id": res.user.id, "email": res.user.email},
            "access_token": res.session.access_token
        }), 201
    else:
        return jsonify({"status": "error", "message": "Signup failed"}), 400


@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    res = supabase.auth.sign_in_with_password({"email": email, "password": password})

    if res.user:
        return jsonify({
            "status": "success",
            "user": {"id": res.user.id, "email": res.user.email},
            "access_token": res.session.access_token
        }), 200
    else:
        return jsonify({"status": "error", "message": "Invalid credentials"}), 401



@app.route('/api/logout', methods=['POST'])
def logout():
    """Clear server-side session"""
    #session.clear()
    return jsonify({"status": "success", "message": "Logged out"}), 200


@app.route("/api/orders/to-nodes", methods=["POST"])
@require_auth
def extract_orders_to_nodes():
    """Extract pending orders for the logged-in manager's warehouse into nodes table."""
    supabase_uid = request.user_id

    # Find manager in DB
    user = User.query.filter_by(user_id=supabase_uid).first()
    if not user:
        print("User not found")
        return jsonify({"status": "error", "message": "User not found"}), 404

    # Get pending orders for that manager’s warehouse
    
    orders = Order.query.filter_by(warehouse_id=user.warehouse, status="pending").all()
    if not orders:
        print("No pending orders")
        return jsonify({"status": "success", "message": "No pending orders for this warehouse"}), 200

    for o in orders:
        node = Node(
            order_id=o.id,
            user_id=user.id,
            warehouse_id=user.warehouse,
            cust_lat=o.cust_lat,
            cust_long=o.cust_long,
            package_weight=o.package_weight,
            traffic_level=o.traffic_level,
            delivery_window=o.delivery_window,
            status="pending"
        )
        db.session.add(node)

    db.session.commit()

    return jsonify({
        "status": "success",
        "message": f"{len(orders)} orders extracted to nodes"
    }), 201


# ------------------------------------------------
# 📌 Get Pending Nodes for Logged-in Manager (JWT version)
# ------------------------------------------------
@app.route("/api/nodes/pending", methods=["GET"])
@require_auth
def get_pending_nodes():
    """Return all pending nodes for the logged-in manager, including customer info."""
    supabase_uid = request.user_id   # Extracted from JWT by @require_auth
    
    user = User.query.filter_by(user_id=supabase_uid).first()
    if not user:
        return jsonify({"status": "error", "message": "User not found"}), 404

    # Fetch pending nodes for this manager
    nodes = Node.query.filter_by(user_id=user.id, status="pending").all()

    result = []
    for n in nodes:
        order = Order.query.get(n.order_id)
        customer = Customer.query.filter_by(customer_id=order.customer_id).first() if order else None

        result.append({
            "node_id": n.id,
            "order_id": n.order_id,
            "cust_lat": n.cust_lat,
            "cust_long": n.cust_long,
            "package_weight": n.package_weight,
            "traffic_level": n.traffic_level,
            "delivery_window": n.delivery_window,
            "warehouse_id": n.warehouse_id,
            "status": n.status,
            "customer": {
                "customer_id": customer.customer_id if customer else None,
                "name": customer.name if customer else None,
                "region": customer.region if customer else None,
                "local_authority": customer.local_authority if customer else None,
                "phone": customer.phone if customer else None
            }
        })

    return jsonify({"status": "success", "nodes": result}), 200

import uuid
# ------------------------------------------------
# 📌 Solve VRP (JWT version)
# ------------------------------------------------
@app.route("/api/solve", methods=["POST"])
@require_auth
def solve_routes():
    """Run VRP pipeline on Node table for logged-in manager."""
    supabase_uid = request.user_id   # comes from JWT
    user = User.query.filter_by(user_id=supabase_uid).first()
    if not user:
        print("User not found")
        return jsonify({"status": "error", "message": "User not found"}), 404

    # ----------------------------
    # 1. Parse frontend config
    # ----------------------------
    data = request.get_json() or {}
    try:
        num_vehicles = parse_int(data.get("numVehicles"), default=3, name="numVehicles", min_value=1)
        vehicle_capacity = parse_int(data.get("vehicleCapacity"), default=200, name="vehicleCapacity", min_value=1)
        # allow tank_size from fuelRequired or a separate tankSize field
        fuel_required = parse_float(
            data.get("fuelRequired") or data.get("tankSize"),
            default=45.0,
            name="tankSize",
            min_value=0.1
        )
        mileage = parse_float(data.get("mileage"), default=15.0, name="mileage", min_value=0.1)

        # ✅ Handle preference (string or None)
        preference = data.get("preference")
        if preference is not None:
            # strip whitespace and normalize empty string -> None
            preference = str(preference).strip() or None

    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400



    fuel_required = float(fuel_required) if fuel_required else None
    mileage = float(mileage) if mileage else None
    print(f"User input: {preference}, num_vehicles: {num_vehicles}, vehicle_capacity: {vehicle_capacity}, fuel_required: {fuel_required}, mileage: {mileage}")
    # ----------------------------
    # 2. Load nodes from DB
    # ----------------------------
    nodes = Node.query.filter_by(user_id=user.id, status="pending").all()
    if not nodes:
        return jsonify({"status": "error", "message": "No pending nodes found"}), 404

    # Slot map (minutes since midnight)
    slot_map = {
        "Morning": (480, 720),
        "Afternoon": (720, 1020),
        "Evening": (1020, 1260),
        "Anytime": (480, 1080)
    }

    def normalize_slot(s):
        if not s:
            return "Anytime"
        t = str(s).strip().title()
        return t if t in slot_map else "Anytime"

    # ----------------------------
    # Depot: take from warehouse lat/lon of first order
    # ----------------------------
    first_order = Order.query.get(nodes[0].order_id)
    depot = {
        "id": user.warehouse,
        "lat": first_order.wh_lat,
        "lon": first_order.wh_long
    }

    # ----------------------------
    # Build customers list
    # ----------------------------
    print("Building customers list...")
    customers = []
    for n in nodes:
        order = Order.query.get(n.order_id)
        cust_rec = Customer.query.filter_by(customer_id=order.customer_id).first() if order else None
        slot_label = normalize_slot(n.delivery_window)

        customers.append({
            "customer_id": cust_rec.customer_id if cust_rec else f"order-{n.order_id}",
            "lat": float(n.cust_lat),
            "lon": float(n.cust_long),
            "weight": float(n.package_weight) if n.package_weight else 0.0,
            "slot_label": slot_label,
            "time_window": slot_map[slot_label],
            "local_authority": cust_rec.local_authority if cust_rec else None,
            "region": cust_rec.region if cust_rec else None,
            "priority": "normal"
        })
    print(f"{len(customers)} customers loaded.")
    # ----------------------------
    # 3. OR-Tools baseline
    # ----------------------------
    print("Computing baseline routes with OR-Tools...")
    baseline = ortools_vrp(
    depot,
    customers,
    num_vehicles=num_vehicles,
    vehicle_capacity=vehicle_capacity,
    mileage=mileage or 15,
    fuel_price=110,
    tank_size=fuel_required or 45
)

    print("Baseline routes computed.")
    print(baseline)
    # ----------------------------
    # 4. Enrich + Distances
    # ----------------------------
    print("Enriching customers with traffic data and building distance lookup...")
    df1, df2, df3 = (
        read_csv_from_s3(S3_BUCKET, "local_authority_traffic.csv"),
        read_csv_from_s3(S3_BUCKET, "region_traffic.csv"),
        read_csv_from_s3(S3_BUCKET, "dft_traffic_counts_raw_counts.csv")
    )
    print("CSV files loaded from S3")
    customers_info = enrich_customers(customers, df1, df2, df3)
    distance_lookup = build_distance_lookup(depot, customers)
    print("Customer enrichment and distance lookup done.")
    # ----------------------------
    # 5. Preferences
    # ----------------------------
    print("Parsing user preferences...")
    preferences = get_user_preferences(preference)
    payload = make_payload_for_llm(depot, baseline, distance_lookup, customers_info, preferences)
    
    print("Payload for LLM constructed.")
    payload["user_preferences_table"] = {
        "priority_customers": preferences.get("priority_customers", []),
        "avoid_zones": preferences.get("avoid_zones", []),
        "fairness": preferences.get("fairness", False),
        "eco_mode": preferences.get("eco_mode", False)
    }
    
    with open("llm_payload.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=4, ensure_ascii=False)
    
    

    # ----------------------------
    # 6. Call LLM
    # ----------------------------
    try:
        raw_text = call_llm(payload)
        parsed = extract_json(raw_text)
        parsed_json = json.loads(parsed)
        print("LLM call and JSON parse successful.")
    except Exception as e:
        print("LLM call or JSON parse error:", e)
        return jsonify({"status": "error", "message": f"LLM failed: {e}"}), 500

    # ----------------------------
    # 7. Live Data Integration
    # ----------------------------
    print("Integrating live traffic data...")
    traffic_enriched, traffic_matrix = add_traffic_durations(
        parsed_json,
        api_key=os.getenv("GOOGLE_API_KEY")
    )
    print("Traffic data integration done.")
    print(traffic_enriched)
    print(traffic_matrix)
    try:
        rerouted_json = reroute_with_traffic(traffic_enriched,traffic_matrix)
    except Exception as e:
        return jsonify({"status": "error", "message": f"Traffic rerouting failed: {e}"}), 500

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return jsonify({"status": "error", "message": "Missing Google API Key"}), 500
    print("Rerouting with traffic data done.")
    final_plan = enrich_with_support_stations(rerouted_json, api_key=api_key)
    for route in final_plan["refined_routes"]:
        vehicle = route["vehicle"]
        seq = route["sequence"]

        total_distance = 0
        for i in range(len(seq) - 1):
            p1 = (seq[i]["lat"], seq[i]["lon"])
            p2 = (seq[i+1]["lat"], seq[i+1]["lon"])
            dist = haversine(p1, p2, unit=Unit.KILOMETERS)
            total_distance += dist

        # ✅ Add total distance back into the route dictionary
        route["total_distance_km"] = round(total_distance, 3)
            
    final_plan["ortools"] = baseline
    driver_notes = generate_trip_descriptions(final_plan)
    print("Support station enrichment and trip descriptions done.")
    # ----------------------------
    # 8. Save Route to DB
    # ----------------------------
    print("Saving route to DB...")
    trip_id = str(uuid.uuid4())[:8]
    new_route = Route(
        trip_id=trip_id,
        user_id=user.id,
        route_detail=final_plan,
        summary=driver_notes
    )
    db.session.add(new_route)

    # Mark nodes as processed
    for n in nodes:
        n.status = "processed"

    db.session.commit()

    return jsonify({
        "status": "success",
        "trip_id": trip_id,
        "message": f"Route saved for warehouse {user.warehouse}. Fetch using /api/routes/{trip_id}"
    }), 200


# ------------------------------------------------
# 📌 Get All Trip IDs + Created At for Logged-in User (JWT version)
# ------------------------------------------------
@app.route("/api/routes/trip-ids", methods=["GET"])
@require_auth
def get_all_trip_ids():
    """Fetch all trip_ids with created_at for the logged-in user from the Route table."""
    supabase_uid = request.user_id   # comes from JWT

    # Find user in DB
    user = User.query.filter_by(user_id=supabase_uid).first()
    if not user:
        return jsonify({"status": "error", "message": "User not found"}), 404

    # Fetch all routes for this user (newest first)
    routes = Route.query.filter_by(user_id=user.id).order_by(desc(Route.created_at)).all()
    if not routes:
        return jsonify({"status": "success", "trip_ids": []}), 200

    # Build response with trip_id and created_at
    trip_list = [
        {
            "trip_id": r.trip_id,
            "created_at": r.created_at.isoformat() if r.created_at else None
        }
        for r in routes
    ]

    return jsonify({
        "status": "success",
        "trip_ids": trip_list,
        "count": len(trip_list)
    }), 200


# ------------------------------------------------
# 📌 Get Latest Route for Logged-in User (JWT version)
# ------------------------------------------------
@app.route("/api/routes", methods=["GET"])
@app.route("/api/routes/<trip_id>", methods=["GET"])
@require_auth
def get_route(trip_id=None):
    """Fetch a specific route by trip_id, or the latest route if no trip_id is given."""
    supabase_uid = request.user_id  # comes from JWT

    user = User.query.filter_by(user_id=supabase_uid).first()
    print("Fetched user:", user)
    if not user:
        return jsonify({"status": "error", "message": "User not found"}), 404

    if trip_id:
        # Fetch by trip_id
        print("Fetching route for trip_id:", trip_id)
        route = Route.query.filter_by(user_id=user.id, trip_id=trip_id).first()
        if not route:
            return jsonify({"status": "error", "message": "Route not found"}), 404
    else:
        # Fetch the latest route
        route = Route.query.filter_by(user_id=user.id).order_by(desc(Route.created_at)).first()
        if not route:
            return jsonify({"status": "error", "message": "No routes found"}), 404
        
    print("Fetched route:", route)

    return jsonify({
        "status": "success",
        "trip_id": route.trip_id,
        "route": route.route_detail,   # Full JSON plan
        "summary": route.summary
    }), 200

# ------------------------------------------------
# 📌 Reset Processed Nodes to Pending (Utility/Test) REMOVE AFTER WARDS
# ------------------------------------------------
# ------------------------------------------------
# 📌 Reset Processed Nodes to Pending (JWT version)
# ------------------------------------------------
@app.route("/api/nodes/reset-pending", methods=["POST"])
@require_auth
def reset_nodes_to_pending():
    """Reset all processed nodes for the logged-in manager's warehouse back to pending."""
    supabase_uid = request.user_id   # comes from JWT

    user = User.query.filter_by(user_id=supabase_uid).first()
    if not user:
        return jsonify({"status": "error", "message": "User not found"}), 404

    # Find processed nodes for this manager
    processed_nodes = Node.query.filter_by(user_id=user.id, status="processed").all()
    if not processed_nodes:
        return jsonify({
            "status": "success",
            "message": "No processed nodes found for this warehouse"
        }), 200

    # Reset them to pending
    for n in processed_nodes:
        n.status = "pending"

    db.session.commit()

    return jsonify({
        "status": "success",
        "message": f"{len(processed_nodes)} nodes reset to pending",
        "warehouse_id": user.warehouse
    }), 200



# In-memory store for conversation history (per user)
situation_chat_history = {}

# ------------------------------------------------
# 📌 Situation Recommendation (JWT version)
# ------------------------------------------------
@app.route("/api/situation/recommend/<tripid>", methods=["POST"])
@require_auth
def situation_recommend(tripid):
    """Interactive dispatcher chatbot for situation handling (JWT auth)."""
    supabase_uid = request.user_id   # from JWT

    user = User.query.filter_by(user_id=supabase_uid).first()
    if not user:
        return jsonify({"status": "error", "message": "User not found"}), 404

    data = request.get_json() or {}
    vehicle_id = data.get("vehicle_id")
    near_customer = data.get("near_customer")
    note = data.get("note", "")

    if not vehicle_id or not near_customer:
        return jsonify({
            "status": "error",
            "message": "vehicle_id and near_customer are required"
        }), 400

    # Get latest route for context (searching by trip id as requested)
    latest_route = Route.query.filter_by(user_id=user.id, trip_id=tripid).order_by(desc(Route.created_at)).first()
    if not latest_route:
        return jsonify({"status": "error", "message": f"No route found for this user and trip id {tripid}"}), 404

    # Build user message
    user_message = f"Vehicle {vehicle_id} reported near {near_customer}. {note}"

    # Initialize chat history for this user if not present
    if supabase_uid not in situation_chat_history:
        situation_chat_history[supabase_uid] = []

    # Append user message
    situation_chat_history[supabase_uid].append({"role": "user", "content": user_message})

    try:
        # Generate recommendation using history
        recommendation = generate_situation_recommendation(
            vehicle_id,
            near_customer,
            note,
            latest_route.route_detail,
            history=situation_chat_history[supabase_uid]
        )
    except Exception as e:
        return jsonify({"status": "error", "message": f"Gemini call failed: {e}"}), 500

    # Append model response to chat history
    situation_chat_history[supabase_uid].append({"role": "assistant", "content": recommendation})

    return jsonify({
        "status": "success",
        "situation": user_message,
        "recommendation": recommendation,
        "chat_history": situation_chat_history[supabase_uid]
    }), 200


# In-memory store for fuel conversations (per user)
fuel_chat_history = {}

# ------------------------------------------------
# 📌 Situation Fuel (JWT version)
# ------------------------------------------------
@app.route("/api/situation/fuel/<tripid>", methods=["POST"])
@require_auth
def situation_fuel(tripid):
    """Conversational fuel/energy management assistant (JWT auth)."""
    supabase_uid = request.user_id   # from JWT

    user = User.query.filter_by(user_id=supabase_uid).first()
    if not user:
        return jsonify({"status": "error", "message": "User not found"}), 404

    data = request.get_json() or {}
    vehicle_id = data.get("vehicle_id")
    near_customer = data.get("near_customer")
    note = data.get("note", "")

    if not vehicle_id or not near_customer:
        return jsonify({
            "status": "error",
            "message": "vehicle_id and near_customer are required"
        }), 400

    # Fetch latest route (filter by trip id)
    latest_route = Route.query.filter_by(user_id=user.id, trip_id=tripid).order_by(desc(Route.created_at)).first()
    if not latest_route:
        return jsonify({"status": "error", "message": f"No route found for trip id {tripid}"}), 404

    # Build user message
    user_message = f"Fuel situation: Vehicle {vehicle_id} is near {near_customer}. {note}"

    # Get conversation history (per user)
    if supabase_uid not in fuel_chat_history:
        fuel_chat_history[supabase_uid] = []
    history = fuel_chat_history[supabase_uid]

    # Add user message
    history.append({"role": "user", "content": user_message})

    # Call Gemini with history + route context
    try:
        result = generate_fuel_recommendation(
            vehicle_id=vehicle_id,
            near_customer=near_customer,
            note=note,
            route_json=latest_route.route_detail,
            conversation=history
        )
    except Exception as e:
        return jsonify({"status": "error", "message": f"Gemini call failed: {e}"}), 500

    # Save assistant reply in history
    recommendation = result["recommendation"]
    fuel_chat_history[supabase_uid] = result["conversation"]

    return jsonify({
        "status": "success",
        "conversation": fuel_chat_history[supabase_uid],
        "latest_reply": recommendation
    }), 200


# In-memory store for fatigue conversations (per user)
fatigue_chat_history = {}

# ------------------------------------------------
# 📌 Situation Fatigue (JWT version)
# ------------------------------------------------
@app.route("/api/situation/fatigue/<tripid>", methods=["POST"])
@require_auth
def situation_fatigue(tripid):
    """Handle fatigue/compliance issues with chat-style recommendations (JWT auth)."""
    supabase_uid = request.user_id   # from JWT

    user = User.query.filter_by(user_id=supabase_uid).first()
    if not user:
        return jsonify({"status": "error", "message": "User not found"}), 404

    data = request.get_json() or {}
    vehicle_id = data.get("vehicle_id")
    near_customer = data.get("near_customer")
    note = data.get("note", "")

    if not vehicle_id or not near_customer:
        return jsonify({
            "status": "error",
            "message": "vehicle_id and near_customer are required"
        }), 400

    # Get latest route (filter by trip id)
    latest_route = Route.query.filter_by(user_id=user.id, trip_id=tripid).order_by(desc(Route.created_at)).first()
    if not latest_route:
        return jsonify({"status": "error", "message": f"No route found for trip id {tripid}"}), 404

    # Maintain conversation in memory
    if supabase_uid not in fatigue_chat_history:
        fatigue_chat_history[supabase_uid] = []
    conversation = fatigue_chat_history[supabase_uid]

    try:
        result = generate_fatigue_recommendation(
            vehicle_id,
            near_customer,
            note,
            latest_route.route_detail,
            conversation
        )
        recommendation = result["recommendation"]
        fatigue_chat_history[supabase_uid] = result["conversation"]  # update memory store
    except Exception as e:
        return jsonify({"status": "error", "message": f"Gemini call failed: {e}"}), 500

    return jsonify({
        "status": "success",
        "vehicle_id": vehicle_id,
        "near_customer": near_customer,
        "note": note,
        "recommendation": recommendation,
        "conversation": fatigue_chat_history[supabase_uid]  # full chat for frontend display
    }), 200




  
    
# ------------------------------------------------
# 🚀 Run Flask App
if __name__ == "__main__":
    print("✅ About to run db.create_all()")
    with app.app_context():
        print("✅ About to run db.create_all()")
        db.create_all()
        print("✅ db.create_all() finished")
    print("🚀 Starting Flask app...")
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)