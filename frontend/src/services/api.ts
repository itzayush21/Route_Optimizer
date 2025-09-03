import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';

const api = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true, // For session-based auth
  headers: {
    'Content-Type': 'application/json',
  },
});

// Auth interfaces
export interface LoginRequest {
  email: string;
  password: string;
}

export interface SignupRequest {
  email: string;
  password: string;
  warehouse?: string;
  phone?: string;
}

export interface AuthResponse {
  status: string;
  user: {
    id: string;
    email: string;
  };
  access_token: string;
}

// Node interfaces
export interface Customer {
  customer_id: string | null;
  name: string | null;
  region: string | null;
  local_authority: string | null;
  phone: string | null;
}

export interface Node {
  node_id: number;
  order_id: number;
  cust_lat: number;
  cust_long: number;
  package_weight: number;
  traffic_level: string;
  delivery_window: string;
  warehouse_id: string;
  status: string;
  customer: Customer;
}

export interface SolveRequest {
  preferences?: string;
  num_vehicles?: number;
  vehicle_capacity?: number;
}

export interface SituationRequest {
  vehicle_id: string;
  near_customer: string;
  note?: string;
}

// Auth API calls
export const authAPI = {
  login: (data: LoginRequest) => api.post<AuthResponse>('/api/login', data),
  signup: (data: SignupRequest) => api.post<AuthResponse>('/api/signup', data),
  logout: () => api.post('/api/logout'),
};

// Orders and Nodes API calls
export const ordersAPI = {
  extractToNodes: () => api.post('/api/orders/to-nodes'),
  getPendingNodes: () => api.get<{ status: string; nodes: Node[] }>('/api/nodes/pending'),
  resetNodes: () => api.post('/api/nodes/reset-pending'),
};

// Route solving API
export const routeAPI = {
  solve: (data: SolveRequest) => api.post('/api/solve', data),
};

// Situation management API
export const situationAPI = {
  recommend: (data: SituationRequest) => api.post('/api/situation/recommend', data),
  fuel: (data: SituationRequest) => api.post('/api/situation/fuel', data),
  fatigue: (data: SituationRequest) => api.post('/api/situation/fatigue', data),
};

export default api;