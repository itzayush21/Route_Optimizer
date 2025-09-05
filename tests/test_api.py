import pytest
import requests

BASE_URL = "http://10.53.178.199:5000"


# ----------------------------
# Fixtures
# ----------------------------
@pytest.fixture(scope="session")
def signup_payload():
    return {
        "email": "pytest_user1@example.com",  # ⚠️ must be unique each run
        "password": "TestPassword123",
        "warehouse": "W010",
        "phone": "9876543210"
    }


@pytest.fixture(scope="session")
def token(signup_payload):
    """Signup + login once, return access token"""
    # Signup
    requests.post(f"{BASE_URL}/api/signup", json=signup_payload)

    # Login
    r = requests.post(f"{BASE_URL}/api/login", json={
        "email": signup_payload["email"],
        "password": signup_payload["password"]
    })
    assert r.status_code == 200, f"Login failed: {r.text}"
    return r.json()["access_token"]


# ----------------------------
# Helpers
# ----------------------------
def auth_headers(token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


# ----------------------------
# Tests
# ----------------------------
def test_health():
    r = requests.get(f"{BASE_URL}/")
    assert r.status_code == 200


def test_nodes_flow(token):
    # Reset nodes
    r = requests.post(f"{BASE_URL}/api/nodes/reset-pending", headers=auth_headers(token))
    assert r.status_code == 200

    # Orders → Nodes
    r = requests.post(f"{BASE_URL}/api/orders/to-nodes", headers=auth_headers(token))
    assert r.status_code == 200

    # Pending Nodes
    r = requests.get(f"{BASE_URL}/api/nodes/pending", headers=auth_headers(token))
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_solve_vrp(token):
    payload = {
        "preferences": "Prioritize C046 and C038 first, avoid Oxford, balance workload.",
        "numVehicles": 3,
        "vehicleCapacity": 150
    }
    r = requests.post(f"{BASE_URL}/api/solve", headers=auth_headers(token), json=payload)
    assert r.status_code == 200
    assert "routes" in r.json()


def test_situation_endpoints(token):
    situations = [
        ("/api/situation/recommend", {"vehicle_id": "V2", "near_customer": "C07", "note": "Breakdown"}),
        ("/api/situation/fuel", {"vehicle_id": "V1", "near_customer": "C070", "note": "Low fuel"}),
        ("/api/situation/fatigue", {"vehicle_id": "V3", "near_customer": "C033", "note": "Driver fatigue"})
    ]
    for path, payload in situations:
        r = requests.post(f"{BASE_URL}{path}", headers=auth_headers(token), json=payload)
        assert r.status_code == 200


def test_routes_latest(token):
    r = requests.get(f"{BASE_URL}/api/routes/latest", headers=auth_headers(token))
    assert r.status_code == 200
