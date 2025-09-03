import React from 'react';
import { useAuth } from '../context/AuthContext';
import { Link } from 'react-router-dom';
import './Dashboard.css';

const Dashboard: React.FC = () => {
  const { user, logout } = useAuth();

  const handleLogout = () => {
    logout();
  };

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <h1>Route Optimizer Dashboard</h1>
        <div className="user-info">
          <span>Welcome, {user?.email}</span>
          <button onClick={handleLogout} className="logout-button">
            Logout
          </button>
        </div>
      </header>

      <main className="dashboard-main">
        <div className="dashboard-grid">
          <div className="dashboard-card">
            <h2>📦 Order Management</h2>
            <p>Extract orders to nodes and manage pending deliveries</p>
            <Link to="/orders" className="card-button">
              Manage Orders
            </Link>
          </div>

          <div className="dashboard-card">
            <h2>🚛 Route Optimization</h2>
            <p>Solve routes with AI-powered optimization and preferences</p>
            <Link to="/routes" className="card-button">
              Optimize Routes
            </Link>
          </div>

          <div className="dashboard-card">
            <h2>⚠️ Situation Management</h2>
            <p>Handle fuel, fatigue, and operational situations with AI assistance</p>
            <Link to="/situations" className="card-button">
              Manage Situations
            </Link>
          </div>

          <div className="dashboard-card">
            <h2>📊 Analytics</h2>
            <p>View performance metrics and route analytics</p>
            <Link to="/analytics" className="card-button">
              View Analytics
            </Link>
          </div>
        </div>
      </main>
    </div>
  );
};

export default Dashboard;