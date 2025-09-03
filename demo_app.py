#!/usr/bin/env python3
"""
Demo Flask app for Route Optimizer Frontend
This is a simplified version for testing the frontend without full database setup.
"""

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import json
import uuid

app = Flask(__name__)
CORS(app, supports_credentials=True)
app.secret_key = 'demo_secret_key'

# Demo data for testing
demo_route = {
    "depot": {
        "id": "DEPOT_001",
        "lat": 51.5074,
        "lon": -0.1278
    },
    "refined_routes": [
        {
            "vehicle": "Vehicle 1",
            "sequence": [
                {
                    "id": "DEPOT_001",
                    "lat": 51.5074,
                    "lon": -0.1278
                },
                {
                    "id": "CUST_001",
                    "lat": 51.5155,
                    "lon": -0.1415,
                    "weight": 25.5,
                    "time_window": "Morning",
                    "nearby_petrol_stations": [
                        {
                            "name": "Shell Station",
                            "address": "123 High Street",
                            "lat": 51.5160,
                            "lon": -0.1420,
                            "distance_km": 0.3
                        }
                    ],
                    "nearby_repair_shops": [
                        {
                            "name": "AutoFix Garage",
                            "address": "456 Repair Lane",
                            "lat": 51.5150,
                            "lon": -0.1410,
                            "distance_km": 0.2
                        }
                    ]
                },
                {
                    "id": "CUST_002",
                    "lat": 51.5200,
                    "lon": -0.1500,
                    "weight": 15.0,
                    "time_window": "Afternoon"
                },
                {
                    "id": "DEPOT_001",
                    "lat": 51.5074,
                    "lon": -0.1278
                }
            ],
            "metrics": {
                "total_distance_km": 12.5,
                "total_traffic_duration_mins": 45.2,
                "total_normal_duration_mins": 38.1
            }
        },
        {
            "vehicle": "Vehicle 2",
            "sequence": [
                {
                    "id": "DEPOT_001",
                    "lat": 51.5074,
                    "lon": -0.1278
                },
                {
                    "id": "CUST_003",
                    "lat": 51.4950,
                    "lon": -0.1350,
                    "weight": 30.0,
                    "time_window": "Morning"
                },
                {
                    "id": "DEPOT_001",
                    "lat": 51.5074,
                    "lon": -0.1278
                }
            ],
            "metrics": {
                "total_distance_km": 8.2,
                "total_traffic_duration_mins": 28.7,
                "total_normal_duration_mins": 24.5
            }
        }
    ]
}

# Routes
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
        "message": "Route Optimizer Demo API 🚀",
        "mode": "demo",
        "available_endpoints": ["/api/login", "/api/solve", "/api/routes/latest"]
    })

@app.route("/api/login", methods=["POST"])
def demo_login():
    """Demo login - always succeeds"""
    data = request.get_json() or {}
    email = data.get("email", "")
    
    if email:
        return jsonify({
            "status": "success",
            "message": "Demo login successful",
            "user": {"email": email}
        }), 200
    else:
        return jsonify({"status": "error", "message": "Email required"}), 400

@app.route("/api/solve", methods=["POST"])
def demo_solve():
    """Demo route optimization - returns sample route"""
    data = request.get_json() or {}
    
    # Simulate processing time
    trip_id = str(uuid.uuid4())[:8]
    
    return jsonify({
        "status": "success",
        "trip_id": trip_id,
        "message": f"Demo route optimized! Trip ID: {trip_id}"
    }), 200

@app.route("/api/routes/latest", methods=["GET"])
def demo_latest_route():
    """Return demo route data"""
    return jsonify({
        "status": "success",
        "trip_id": "demo_123",
        "route_detail": demo_route,
        "summary": "Demo route with 2 vehicles visiting 3 customers. Vehicle 1 covers the northern area with 2 stops, while Vehicle 2 handles the southern customer. Total estimated time with traffic: 74 minutes.",
        "created_at": "2024-01-01T12:00:00"
    }), 200

@app.route("/api/routes/<trip_id>", methods=["GET"])
def demo_route_by_id(trip_id):
    """Return demo route data for any trip_id"""
    return jsonify({
        "status": "success",
        "trip_id": trip_id,
        "route_detail": demo_route,
        "summary": f"Demo route {trip_id} with real-time traffic optimization. This route has been optimized using current traffic conditions to minimize delivery time.",
        "created_at": "2024-01-01T12:00:00"
    }), 200

if __name__ == "__main__":
    print("🚀 Starting Route Optimizer Demo...")
    print("📍 Frontend available at: http://localhost:5000")
    print("🔧 API endpoint: http://localhost:5000/api")
    app.run(host="0.0.0.0", port=5000, debug=True)