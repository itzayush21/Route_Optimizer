# ============================================
# 🗂 Database Models
# ============================================
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy import Enum, DateTime, Date ,JSON

db = SQLAlchemy()


class Customer(db.Model):
    __tablename__ = "customers"

    id = db.Column(db.Integer, primary_key=True)  # internal PK
    customer_id = db.Column(db.String(100), unique=True, nullable=False)  # external ID from CSV
    name = db.Column(db.String(200))
    region = db.Column(db.String(100))
    local_authority = db.Column(db.String(200))
    phone = db.Column(db.String(20))

    # Relationship to orders
    orders = db.relationship("Order", backref="customer", lazy=True)

    def __repr__(self):
        return f"<Customer {self.customer_id}>"


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    customer_id = db.Column(
        db.String(100),
        db.ForeignKey("customers.customer_id"),  # 👈 Foreign key link
        nullable=False
    )
    region = db.Column(db.String(100))
    local_authority = db.Column(db.String(200))
    cust_lat = db.Column(db.Float, nullable=False)
    cust_long = db.Column(db.Float, nullable=False)
    warehouse_id = db.Column(db.String(100), nullable=False)
    wh_region = db.Column(db.String(100))
    wh_local_authority = db.Column(db.String(200))
    wh_lat = db.Column(db.Float, nullable=False)
    wh_long = db.Column(db.Float, nullable=False)
    traffic_level = db.Column(db.String(50))
    package_weight = db.Column(db.Float)
    delivery_window = db.Column(db.String(100))
    status = db.Column(db.String(20), default="pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Order ID:{self.id}, Customer:{self.customer_id}, Warehouse:{self.warehouse_id}>"

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)  # internal ID
    user_id = db.Column(db.String(100), unique=True, nullable=False)  # Supabase UID
    warehouse = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    routes = db.relationship("Route", backref="user", lazy=True)

    def __repr__(self):
        return f"<User {self.user_id}>"


class Route(db.Model):
    __tablename__ = "routes"

    id = db.Column(db.Integer, primary_key=True)
    trip_id = db.Column(db.String(100), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    route_detail = db.Column(JSON)   # full route JSON from VRP solver
    summary = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Route {self.trip_id}>"
    
    
class Node(db.Model):
    __tablename__ = "nodes"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    warehouse_id = db.Column(db.String(100), nullable=False)

    cust_lat = db.Column(db.Float, nullable=False)
    cust_long = db.Column(db.Float, nullable=False)
    package_weight = db.Column(db.Float)
    traffic_level = db.Column(db.String(50))
    delivery_window = db.Column(db.String(100))
    status = db.Column(db.String(20), default="pending")  # pending/processed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Node {self.id} (Order {self.order_id}) - User {self.user_id}>"

