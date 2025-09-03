import React, { useState } from 'react';
import { routeAPI } from '../services/api';
import './Routes.css';

const RoutesPage: React.FC = () => {
  const [preferences, setPreferences] = useState('');
  const [numVehicles, setNumVehicles] = useState(3);
  const [vehicleCapacity, setVehicleCapacity] = useState(200);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');

  const handleSolveRoutes = async () => {
    try {
      setLoading(true);
      setError('');
      setResult(null);

      const response = await routeAPI.solve({
        preferences: preferences || undefined,
        num_vehicles: numVehicles,
        vehicle_capacity: vehicleCapacity,
      });

      setResult(response.data);
    } catch (err: any) {
      setError(err.response?.data?.message || 'Failed to solve routes');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="routes-page">
      <div className="page-header">
        <h1>Route Optimization</h1>
      </div>

      <div className="optimization-form">
        <h2>Optimization Parameters</h2>
        <div className="form-grid">
          <div className="form-group">
            <label htmlFor="numVehicles">Number of Vehicles</label>
            <input
              type="number"
              id="numVehicles"
              value={numVehicles}
              onChange={(e) => setNumVehicles(parseInt(e.target.value))}
              min="1"
              max="20"
              disabled={loading}
            />
          </div>

          <div className="form-group">
            <label htmlFor="vehicleCapacity">Vehicle Capacity (kg)</label>
            <input
              type="number"
              id="vehicleCapacity"
              value={vehicleCapacity}
              onChange={(e) => setVehicleCapacity(parseInt(e.target.value))}
              min="1"
              disabled={loading}
            />
          </div>
        </div>

        <div className="form-group full-width">
          <label htmlFor="preferences">Preferences (Natural Language)</label>
          <textarea
            id="preferences"
            value={preferences}
            onChange={(e) => setPreferences(e.target.value)}
            placeholder="e.g., Prioritize customer C123, avoid high traffic areas, enable eco mode, ensure fairness between routes"
            rows={4}
            disabled={loading}
          />
          <small>
            Describe your routing preferences in natural language. The AI will interpret your requirements.
          </small>
        </div>

        <button
          onClick={handleSolveRoutes}
          disabled={loading}
          className="solve-button"
        >
          {loading ? 'Optimizing Routes...' : 'Solve Routes'}
        </button>
      </div>

      {error && (
        <div className="error-message">
          {error}
        </div>
      )}

      {result && (
        <div className="result-section">
          <h2>Optimization Result</h2>
          <div className="result-card">
            <div className="result-header">
              <h3>✅ Routes Optimized Successfully</h3>
              <span className="trip-id">Trip ID: {result.trip_id}</span>
            </div>
            <p>{result.message}</p>
            <div className="result-actions">
              <button className="primary-button">View Route Details</button>
              <button className="secondary-button">Download Routes</button>
            </div>
          </div>
        </div>
      )}

      <div className="info-section">
        <h2>How It Works</h2>
        <div className="info-grid">
          <div className="info-card">
            <h3>1. 📊 Data Processing</h3>
            <p>We analyze pending orders, customer locations, and traffic patterns</p>
          </div>
          <div className="info-card">
            <h3>2. 🤖 AI Optimization</h3>
            <p>Our AI considers your preferences and optimizes routes using OR-Tools</p>
          </div>
          <div className="info-card">
            <h3>3. 🚦 Live Traffic</h3>
            <p>Routes are adjusted based on real-time traffic conditions</p>
          </div>
          <div className="info-card">
            <h3>4. ⛽ Support Stations</h3>
            <p>Nearby fuel stations and rest stops are added to routes</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default RoutesPage;