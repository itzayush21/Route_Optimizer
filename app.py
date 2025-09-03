from flask import Flask, jsonify, request, session, send_from_directory
from flask_cors import CORS
from auth.auth_client import create_supabase_client
from config import Config
from model import db, Customer, Order, User, Route , Node
from datetime import datetime
import pandas as pd
import json,os,uuid
from dotenv import load_dotenv
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

from sqlalchemy import desc
load_dotenv()
# ------------------------------------------------
# 🔧 Flask App Setup
# ------------------------------------------------
app = Flask(__name__)
CORS(app, supports_credentials=True)  # Enable CORS for frontend-backend communication
app.secret_key = 'supersecretkey'  # TODO: replace with os.getenv("SECRET_KEY")
S3_BUCKET = os.getenv("S3_BUCKET_NAME", "your-bucket-name")
print("✅ Starting app.py DB setup...")
app.config["SQLALCHEMY_DATABASE_URI"] = Config.DB_URI
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = Config.ENGINE_OPTIONS
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)
print("✅ Starting app.py DB setup 2...")

# Supabase client
print("✅ Starting app.py Supabase setup...")
supabase = create_supabase_client()
print("✅ Starting app.py imports...")

# ------------------------------------------------
# 🔑 Auth Endpoints
# ------------------------------------------------

@app.route("/", methods=["GET"])
def index():
    """Serve the frontend application"""
    return send_from_directory('static', 'index.html')

@app.route("/static/<path:filename>")
def serve_static(filename):
    """Serve static files"""
    return send_from_directory('static', filename)

@app.route("/api", methods=["GET"])
def api_info():
    return jsonify({
        "status": "ok",
        "message": "Welcome to the VRP Backend API 🚀",
        "available_endpoints": ["/api/signup", "/api/login", "/api/logout", "/api/solve", "/api/routes/latest"]
    })

@app.route('/api/signup', methods=['POST'])
def signup():
    """Signup with Supabase + store user in our DB"""
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")
    warehouse = data.get("warehouse") or "Default Warehouse"
    phone = data.get("phone")

    res = supabase.auth.sign_up({"email": email, "password": password})

    if res.user:
        # Check if user already exists in our DB
        existing_user = User.query.filter_by(user_id=res.user.id).first()
        if not existing_user:
            new_user = User(
                user_id=res.user.id,  # Supabase UID
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
    """Login with Supabase"""
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    res = supabase.auth.sign_in_with_password({"email": email, "password": password})

    if res.user:
        # Save session (optional if you rely only on JWT in frontend)
        session['user'] = {"id": res.user.id, "email": res.user.email}
        session['access_token'] = res.session.access_token

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
    session.clear()
    return jsonify({"status": "success", "message": "Logged out"}), 200


@app.route("/api/orders/to-nodes", methods=["POST"])
def extract_orders_to_nodes():
    """Extract pending orders for the logged-in manager's warehouse into nodes table."""
    if "user" not in session:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    supabase_uid = session["user"]["id"]

    # Find manager in DB
    user = User.query.filter_by(user_id=supabase_uid).first()
    if not user:
        return jsonify({"status": "error", "message": "User not found"}), 404

    # Get pending orders for that manager’s warehouse
    orders = Order.query.filter_by(warehouse_id=user.warehouse, status="pending").all()
    if not orders:
        return jsonify({
            "status": "success",
            "message": "No pending orders for this warehouse"
        }), 200

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
# 📌 Get Pending Nodes for Logged-in Manager
# ------------------------------------------------
@app.route("/api/nodes/pending", methods=["GET"])
def get_pending_nodes():
    """Return all pending nodes for the logged-in manager, including customer info."""
    if "user" not in session:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    supabase_uid = session["user"]["id"]
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


@app.route("/api/solve", methods=["POST"])
def solve_routes():
    """Run VRP pipeline on Node table for logged-in manager."""
    if "user" not in session:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    supabase_uid = session["user"]["id"]
    user = User.query.filter_by(user_id=supabase_uid).first()
    if not user:
        return jsonify({"status": "error", "message": "User not found"}), 404

    # ----------------------------
    # 1. Parse frontend config
    # ----------------------------
    data = request.get_json() or {}
    user_input = data.get("preferences", "")
    num_vehicles = int(data.get("num_vehicles", 3))          # default 3
    vehicle_capacity = int(data.get("vehicle_capacity", 200))  # default 200

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
    # Build customers list with real Customer_ID
    # ----------------------------
    customers = []
    for n in nodes:
        order = Order.query.get(n.order_id)
        cust_rec = Customer.query.filter_by(customer_id=order.customer_id).first() if order else None
        slot_label = normalize_slot(n.delivery_window)

        cust = {
            "customer_id": cust_rec.customer_id if cust_rec else f"order-{n.order_id}",
            "lat": float(n.cust_lat),
            "lon": float(n.cust_long),
            "weight": float(n.package_weight) if n.package_weight else 0.0,
            "slot_label": slot_label,
            "time_window": slot_map[slot_label],
            "local_authority": cust_rec.local_authority if cust_rec else None,
            "region": cust_rec.region if cust_rec else None,
            "priority": "normal"
        }
        customers.append(cust)

    # ----------------------------
    # 3. OR-Tools baseline
    # ----------------------------
    baseline = ortools_vrp(
        depot, customers,
        num_vehicles=num_vehicles,
        vehicle_capacity=vehicle_capacity
    )

    # ----------------------------
    # 4. Enrich + Distances
    # ----------------------------
    df1, df2, df3 = (
        read_csv_from_s3(S3_BUCKET, "local_authority_traffic.csv"),
        read_csv_from_s3(S3_BUCKET, "region_traffic.csv"),
        read_csv_from_s3(S3_BUCKET, "dft_traffic_counts_raw_counts.csv")
    )
    customers_info = enrich_customers(customers, df1, df2, df3)
    distance_lookup = build_distance_lookup(depot, customers)

    # ----------------------------
    # 5. Preferences
    # ----------------------------
    preferences = get_user_preferences(user_input)
    payload = make_payload_for_llm(depot, baseline, distance_lookup, customers_info, preferences)

     # Add user preference table for interpretability (extra, non-breaking)
    payload["user_preferences_table"] = {
        "priority_customers": preferences.get("priority_customers", []),
        "avoid_zones": preferences.get("avoid_zones", []),
        "fairness": preferences.get("fairness", False),
        "eco_mode": preferences.get("eco_mode", False)
    }

    '''with open("llm_payload.json", "w") as f:
        json.dump(payload, f, indent=2)'''
    # ----------------------------
    # 6. Call LLM
    # ----------------------------
    try:
        raw_text = call_llm(payload)
        parsed = extract_json(raw_text)
        parsed_json = json.loads(parsed)
    except Exception as e:
        return jsonify({"status": "error", "message": f"LLM failed: {e}"}), 500
    
    #-----------------------------------------
    # LIVE DATA INTREGRATION
    #-----------------------------------------
    
    # After step 7: Add traffic durations
    traffic_enriched,traffic_matrix= add_traffic_durations(parsed_json,api_key=os.getenv("GOOGLE_API_KEY"))  # you already have this

    # Load your cache file (distance_matrix) or build inline
    '''with open("distance_cache.json", "r") as f:
        traffic_matrix = json.load(f)'''

    # Step 8: Call Gemini for rerouting
    try:
        rerouted_json = reroute_with_traffic(traffic_enriched, traffic_matrix)
    except Exception as e:
        return jsonify({"status": "error", "message": f"Traffic rerouting failed: {e}"}), 500
    
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return jsonify({"status": "error", "message": "Missing Google API Key"}), 500

    final_plan = enrich_with_support_stations(rerouted_json, api_key=api_key)
    driver_notes = generate_trip_descriptions(final_plan)
    # ----------------------------
    # 7. Save route to DB
    # ----------------------------
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
# 📌 Reset Processed Nodes to Pending (Utility/Test) REMOVE AFTER WARDS
# ------------------------------------------------
@app.route("/api/nodes/reset-pending", methods=["POST"])
def reset_nodes_to_pending():
    """Reset all processed nodes for the logged-in manager's warehouse back to pending."""
    if "user" not in session:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    supabase_uid = session["user"]["id"]
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

# ------------------------------------------------
# 📍 Route Retrieval Endpoints for Frontend
# ------------------------------------------------
@app.route("/api/routes/latest", methods=["GET"])
def get_latest_route():
    """Get the latest route for the logged-in user."""
    if "user" not in session:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    supabase_uid = session["user"]["id"]
    user = User.query.filter_by(user_id=supabase_uid).first()
    if not user:
        return jsonify({"status": "error", "message": "User not found"}), 404

    # Get the latest route for this user
    latest_route = Route.query.filter_by(user_id=user.id).order_by(desc(Route.created_at)).first()
    if not latest_route:
        return jsonify({"status": "error", "message": "No routes found for this user"}), 404

    return jsonify({
        "status": "success",
        "trip_id": latest_route.trip_id,
        "route_detail": latest_route.route_detail,
        "summary": latest_route.summary,
        "created_at": latest_route.created_at.isoformat()
    }), 200

@app.route("/api/routes/<trip_id>", methods=["GET"])
def get_route_by_id(trip_id):
    """Get a specific route by trip_id."""
    if "user" not in session:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    supabase_uid = session["user"]["id"]
    user = User.query.filter_by(user_id=supabase_uid).first()
    if not user:
        return jsonify({"status": "error", "message": "User not found"}), 404

    # Get the route by trip_id for this user
    route = Route.query.filter_by(trip_id=trip_id, user_id=user.id).first()
    if not route:
        return jsonify({"status": "error", "message": "Route not found"}), 404

    return jsonify({
        "status": "success",
        "trip_id": route.trip_id,
        "route_detail": route.route_detail,
        "summary": route.summary,
        "created_at": route.created_at.isoformat()
    }), 200
    


@app.route("/api/situation/recommend", methods=["POST"])
def situation_recommend():
    """Interactive dispatcher chatbot for situation handling."""
    if "user" not in session:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    supabase_uid = session["user"]["id"]
    user = User.query.filter_by(user_id=supabase_uid).first()
    if not user:
        return jsonify({"status": "error", "message": "User not found"}), 404

    data = request.get_json() or {}
    vehicle_id = data.get("vehicle_id")
    near_customer = data.get("near_customer")
    note = data.get("note", "")

    if not vehicle_id or not near_customer:
        return jsonify({"status": "error", "message": "vehicle_id and near_customer are required"}), 400

    # Get latest route for context
    latest_route = Route.query.filter_by(user_id=user.id).order_by(desc(Route.created_at)).first()
    if not latest_route:
        return jsonify({"status": "error", "message": "No route found for this user"}), 404

    # Build user message
    user_message = f"Vehicle {vehicle_id} reported near {near_customer}. {note}"

    # Initialize chat history in session if not present
    if "situation_chat" not in session:
        session["situation_chat"] = []

    # Append user message
    session["situation_chat"].append({"role": "user", "content": user_message})

    try:
        # Generate recommendation using history
        recommendation = generate_situation_recommendation(
            vehicle_id, near_customer, note, latest_route.route_detail,
            history=session["situation_chat"]
        )
    except Exception as e:
        return jsonify({"status": "error", "message": f"Gemini call failed: {e}"}), 500

    # Append model response to chat history
    session["situation_chat"].append({"role": "assistant", "content": recommendation})

    return jsonify({
        "status": "success",
        "situation": user_message,
        "recommendation": recommendation,
        "chat_history": session["situation_chat"]
    }), 200
    
@app.route("/api/situation/fuel", methods=["POST"])
def situation_fuel():
    """Conversational fuel/energy management assistant."""
    if "user" not in session:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    supabase_uid = session["user"]["id"]
    user = User.query.filter_by(user_id=supabase_uid).first()
    if not user:
        return jsonify({"status": "error", "message": "User not found"}), 404

    data = request.get_json() or {}
    vehicle_id = data.get("vehicle_id")
    near_customer = data.get("near_customer")
    note = data.get("note", "")

    if not vehicle_id or not near_customer:
        return jsonify({"status": "error", "message": "vehicle_id and near_customer are required"}), 400

    # Fetch latest route
    latest_route = Route.query.filter_by(user_id=user.id).order_by(desc(Route.created_at)).first()
    if not latest_route:
        return jsonify({"status": "error", "message": "No route found"}), 404

    # Build user message
    user_message = f"Fuel situation: Vehicle {vehicle_id} is near {near_customer}. {note}"

    # Get conversation history (per user, per situation type)
    chat_key = f"fuel_chat_{user.id}"
    history = session.get(chat_key, [])
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
    history = result["conversation"]

    # Save assistant reply in session
    session[chat_key] = history

    return jsonify({
        "status": "success",
        "conversation": history,
        "latest_reply": recommendation
    }), 200



@app.route("/api/situation/fatigue", methods=["POST"])
def situation_fatigue():
    """Handle fatigue/compliance issues with chat-style recommendations."""
    if "user" not in session:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    supabase_uid = session["user"]["id"]
    user = User.query.filter_by(user_id=supabase_uid).first()
    if not user:
        return jsonify({"status": "error", "message": "User not found"}), 404

    data = request.get_json() or {}
    vehicle_id = data.get("vehicle_id")
    near_customer = data.get("near_customer")
    note = data.get("note", "")

    if not vehicle_id or not near_customer:
        return jsonify({"status": "error", "message": "vehicle_id and near_customer are required"}), 400

    # Get latest route
    latest_route = Route.query.filter_by(user_id=user.id).order_by(desc(Route.created_at)).first()
    if not latest_route:
        return jsonify({"status": "error", "message": "No route found"}), 404

    # Maintain conversation in session
    chat_key = f"fatigue_chat_{user.id}"
    conversation = session.get(chat_key, [])

    try:
        result = generate_fatigue_recommendation(
            vehicle_id,
            near_customer,
            note,
            latest_route.route_detail,
            conversation
        )
        recommendation = result["recommendation"]
        session[chat_key] = result["conversation"]  # persist updated conversation
    except Exception as e:
        return jsonify({"status": "error", "message": f"Gemini call failed: {e}"}), 500

    return jsonify({
        "status": "success",
        "vehicle_id": vehicle_id,
        "near_customer": near_customer,
        "note": note,
        "recommendation": recommendation,
        "conversation": session[chat_key]  # full chat for frontend display
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
    app.run(host="0.0.0.0", port=5000, debug=True)