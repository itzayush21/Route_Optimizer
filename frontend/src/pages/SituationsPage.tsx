import React, { useState } from 'react';
import { situationAPI } from '../services/api';
import './Situations.css';

type SituationType = 'general' | 'fuel' | 'fatigue';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

const SituationsPage: React.FC = () => {
  const [situationType, setSituationType] = useState<SituationType>('general');
  const [vehicleId, setVehicleId] = useState('');
  const [nearCustomer, setNearCustomer] = useState('');
  const [note, setNote] = useState('');
  const [loading, setLoading] = useState(false);
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!vehicleId || !nearCustomer) return;

    setLoading(true);
    setError('');

    try {
      let response;
      const requestData = { vehicle_id: vehicleId, near_customer: nearCustomer, note };

      switch (situationType) {
        case 'fuel':
          response = await situationAPI.fuel(requestData);
          setChatHistory(response.data.conversation || []);
          break;
        case 'fatigue':
          response = await situationAPI.fatigue(requestData);
          setChatHistory(response.data.conversation || []);
          break;
        default:
          response = await situationAPI.recommend(requestData);
          setChatHistory(response.data.chat_history || []);
          break;
      }
    } catch (err: any) {
      setError(err.response?.data?.message || 'Failed to get recommendation');
    } finally {
      setLoading(false);
    }
  };

  const clearChat = () => {
    setChatHistory([]);
    setError('');
  };

  return (
    <div className="situations-page">
      <div className="page-header">
        <h1>Situation Management</h1>
        <button onClick={clearChat} className="clear-button">
          Clear Chat
        </button>
      </div>

      <div className="situation-form">
        <h2>Report Situation</h2>
        
        <div className="situation-types">
          <label className={`type-option ${situationType === 'general' ? 'active' : ''}`}>
            <input
              type="radio"
              value="general"
              checked={situationType === 'general'}
              onChange={(e) => setSituationType(e.target.value as SituationType)}
            />
            <span>🚨 General Issue</span>
          </label>
          <label className={`type-option ${situationType === 'fuel' ? 'active' : ''}`}>
            <input
              type="radio"
              value="fuel"
              checked={situationType === 'fuel'}
              onChange={(e) => setSituationType(e.target.value as SituationType)}
            />
            <span>⛽ Fuel/Energy</span>
          </label>
          <label className={`type-option ${situationType === 'fatigue' ? 'active' : ''}`}>
            <input
              type="radio"
              value="fatigue"
              checked={situationType === 'fatigue'}
              onChange={(e) => setSituationType(e.target.value as SituationType)}
            />
            <span>😴 Fatigue/Compliance</span>
          </label>
        </div>

        <form onSubmit={handleSubmit} className="form-grid">
          <div className="form-group">
            <label htmlFor="vehicleId">Vehicle ID</label>
            <input
              type="text"
              id="vehicleId"
              value={vehicleId}
              onChange={(e) => setVehicleId(e.target.value)}
              placeholder="e.g., V1, V2, V3"
              required
              disabled={loading}
            />
          </div>

          <div className="form-group">
            <label htmlFor="nearCustomer">Near Customer</label>
            <input
              type="text"
              id="nearCustomer"
              value={nearCustomer}
              onChange={(e) => setNearCustomer(e.target.value)}
              placeholder="e.g., C079, C123"
              required
              disabled={loading}
            />
          </div>

          <div className="form-group full-width">
            <label htmlFor="note">Situation Description</label>
            <textarea
              id="note"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Describe the situation in detail..."
              rows={3}
              disabled={loading}
            />
          </div>

          <button type="submit" disabled={loading} className="submit-button">
            {loading ? 'Getting Recommendation...' : 'Get AI Recommendation'}
          </button>
        </form>
      </div>

      {error && (
        <div className="error-message">
          {error}
        </div>
      )}

      {chatHistory.length > 0 && (
        <div className="chat-section">
          <h2>AI Dispatcher Chat</h2>
          <div className="chat-container">
            {chatHistory.map((message, index) => (
              <div key={index} className={`chat-message ${message.role}`}>
                <div className="message-header">
                  <span className="role-label">
                    {message.role === 'user' ? '👤 You' : '🤖 AI Dispatcher'}
                  </span>
                </div>
                <div className="message-content">
                  {message.content}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="info-section">
        <h2>AI Situation Assistant</h2>
        <div className="info-grid">
          <div className="info-card">
            <h3>🚨 General Issues</h3>
            <p>Get expert advice for breakdowns, traffic incidents, and operational disruptions with route adjustments.</p>
          </div>
          <div className="info-card">
            <h3>⛽ Fuel Management</h3>
            <p>Find nearby fuel stations, calculate fuel requirements, and get guidance on energy optimization.</p>
          </div>
          <div className="info-card">
            <h3>😴 Fatigue & Compliance</h3>
            <p>Manage driver hours, find rest stops, and ensure compliance with transportation regulations.</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SituationsPage;