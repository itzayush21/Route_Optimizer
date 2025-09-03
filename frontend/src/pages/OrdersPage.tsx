import React, { useState, useEffect } from 'react';
import { ordersAPI, Node } from '../services/api';
import './Orders.css';

const OrdersPage: React.FC = () => {
  const [nodes, setNodes] = useState<Node[]>([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  const fetchPendingNodes = async () => {
    try {
      setLoading(true);
      const response = await ordersAPI.getPendingNodes();
      setNodes(response.data.nodes);
    } catch (error: any) {
      setMessage(error.response?.data?.message || 'Failed to fetch nodes');
    } finally {
      setLoading(false);
    }
  };

  const handleExtractOrders = async () => {
    try {
      setLoading(true);
      await ordersAPI.extractToNodes();
      setMessage('Orders extracted successfully');
      await fetchPendingNodes(); // Refresh the list
    } catch (error: any) {
      setMessage(error.response?.data?.message || 'Failed to extract orders');
    } finally {
      setLoading(false);
    }
  };

  const handleResetNodes = async () => {
    try {
      setLoading(true);
      await ordersAPI.resetNodes();
      setMessage('Nodes reset successfully');
      await fetchPendingNodes(); // Refresh the list
    } catch (error: any) {
      setMessage(error.response?.data?.message || 'Failed to reset nodes');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPendingNodes();
  }, []);

  return (
    <div className="orders-page">
      <div className="page-header">
        <h1>Order Management</h1>
        <div className="action-buttons">
          <button onClick={handleExtractOrders} disabled={loading} className="primary-button">
            Extract Orders to Nodes
          </button>
          <button onClick={handleResetNodes} disabled={loading} className="secondary-button">
            Reset Processed Nodes
          </button>
          <button onClick={fetchPendingNodes} disabled={loading} className="secondary-button">
            Refresh
          </button>
        </div>
      </div>

      {message && (
        <div className={`message ${message.includes('success') ? 'success' : 'error'}`}>
          {message}
        </div>
      )}

      <div className="nodes-section">
        <h2>Pending Nodes ({nodes.length})</h2>
        {loading ? (
          <div className="loading">Loading...</div>
        ) : nodes.length === 0 ? (
          <div className="empty-state">
            <p>No pending nodes found.</p>
            <p>Click "Extract Orders to Nodes" to load orders from your warehouse.</p>
          </div>
        ) : (
          <div className="nodes-grid">
            {nodes.map((node) => (
              <div key={node.node_id} className="node-card">
                <div className="node-header">
                  <h3>Node #{node.node_id}</h3>
                  <span className="order-id">Order #{node.order_id}</span>
                </div>
                <div className="node-details">
                  <div className="detail-row">
                    <span className="label">Customer:</span>
                    <span>{node.customer.name || node.customer.customer_id || 'Unknown'}</span>
                  </div>
                  <div className="detail-row">
                    <span className="label">Location:</span>
                    <span>{node.cust_lat.toFixed(4)}, {node.cust_long.toFixed(4)}</span>
                  </div>
                  <div className="detail-row">
                    <span className="label">Weight:</span>
                    <span>{node.package_weight} kg</span>
                  </div>
                  <div className="detail-row">
                    <span className="label">Delivery Window:</span>
                    <span>{node.delivery_window}</span>
                  </div>
                  <div className="detail-row">
                    <span className="label">Traffic Level:</span>
                    <span className={`traffic-level ${node.traffic_level?.toLowerCase()}`}>
                      {node.traffic_level}
                    </span>
                  </div>
                  <div className="detail-row">
                    <span className="label">Region:</span>
                    <span>{node.customer.region || 'N/A'}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default OrdersPage;