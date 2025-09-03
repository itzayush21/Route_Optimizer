import React from 'react';
import './Analytics.css';

const AnalyticsPage: React.FC = () => {
  return (
    <div className="analytics-page">
      <div className="page-header">
        <h1>Analytics Dashboard</h1>
      </div>

      <div className="analytics-grid">
        <div className="metric-card">
          <h3>Total Routes Optimized</h3>
          <div className="metric-value">127</div>
          <div className="metric-change positive">+12% this month</div>
        </div>

        <div className="metric-card">
          <h3>Average Efficiency</h3>
          <div className="metric-value">94.2%</div>
          <div className="metric-change positive">+2.1% this month</div>
        </div>

        <div className="metric-card">
          <h3>Fuel Savings</h3>
          <div className="metric-value">£2,341</div>
          <div className="metric-change positive">+8.3% this month</div>
        </div>

        <div className="metric-card">
          <h3>Situations Handled</h3>
          <div className="metric-value">89</div>
          <div className="metric-change neutral">Same as last month</div>
        </div>
      </div>

      <div className="charts-section">
        <div className="chart-card">
          <h3>Route Optimization Trends</h3>
          <div className="chart-placeholder">
            <p>📊 Chart visualization would go here</p>
            <p>Shows daily/weekly route optimization performance</p>
          </div>
        </div>

        <div className="chart-card">
          <h3>Situation Types Distribution</h3>
          <div className="chart-placeholder">
            <p>🥧 Pie chart would go here</p>
            <p>Breakdown of fuel, fatigue, and general situations</p>
          </div>
        </div>
      </div>

      <div className="recent-activity">
        <h2>Recent Activity</h2>
        <div className="activity-list">
          <div className="activity-item">
            <div className="activity-icon">🚛</div>
            <div className="activity-content">
              <h4>Route Optimized</h4>
              <p>3 vehicles, 15 deliveries - Trip ID: abc123ef</p>
              <span className="activity-time">2 hours ago</span>
            </div>
          </div>

          <div className="activity-item">
            <div className="activity-icon">⛽</div>
            <div className="activity-content">
              <h4>Fuel Situation Handled</h4>
              <p>Vehicle V2 near customer C079 - Recommended nearest station</p>
              <span className="activity-time">4 hours ago</span>
            </div>
          </div>

          <div className="activity-item">
            <div className="activity-icon">📦</div>
            <div className="activity-content">
              <h4>Orders Extracted</h4>
              <p>25 new orders converted to nodes for optimization</p>
              <span className="activity-time">6 hours ago</span>
            </div>
          </div>

          <div className="activity-item">
            <div className="activity-icon">😴</div>
            <div className="activity-content">
              <h4>Fatigue Management</h4>
              <p>Driver rest recommendations provided for Vehicle V1</p>
              <span className="activity-time">1 day ago</span>
            </div>
          </div>
        </div>
      </div>

      <div className="insights-section">
        <h2>AI Insights</h2>
        <div className="insights-grid">
          <div className="insight-card">
            <h3>🎯 Optimization Tip</h3>
            <p>Your routes are 15% more efficient when you enable eco-mode preferences. Consider making it default for better fuel savings.</p>
          </div>

          <div className="insight-card">
            <h3>📍 Geographic Pattern</h3>
            <p>Most fuel situations occur in the Northwest region. Consider pre-positioning fuel stops for vehicles heading there.</p>
          </div>

          <div className="insight-card">
            <h3>⏰ Peak Times</h3>
            <p>Route optimizations are most requested between 9-11 AM. Consider batch processing for better resource utilization.</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AnalyticsPage;