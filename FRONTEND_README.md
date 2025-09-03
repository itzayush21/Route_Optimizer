# Route Optimizer - React Frontend

This React frontend provides a modern web interface for the Route Optimizer logistics management system.

## Features

### 🔐 Authentication
- User registration and login with Supabase integration
- Session-based authentication
- Protected routes

### 📦 Order Management
- Extract orders from warehouse to processing nodes
- View pending orders with customer details
- Reset processed nodes for testing
- Real-time order status tracking

### 🚛 Route Optimization
- AI-powered route optimization with OR-Tools
- Natural language preference input
- Configurable vehicle parameters (count, capacity)
- Real-time traffic integration
- Support station recommendations

### ⚠️ Situation Management
- AI-powered dispatcher assistance
- Three specialized assistants:
  - **General Issues**: Breakdowns, traffic incidents, operational disruptions
  - **Fuel Management**: Fuel station recommendations, energy optimization
  - **Fatigue & Compliance**: Driver rest management, compliance tracking
- Conversational chat interface with context retention
- Real-time route context for accurate recommendations

### 📊 Analytics Dashboard
- Performance metrics and KPIs
- Recent activity tracking
- AI-generated insights and recommendations
- Route optimization trends

## Technology Stack

- **React 18** with TypeScript
- **React Router** for navigation
- **Axios** for API communication
- **Context API** for state management
- **CSS3** with modern styling and animations
- **Responsive design** for desktop and mobile

## Setup Instructions

### Prerequisites
- Node.js 16+ and npm
- Python Flask backend running on port 5000

### Installation

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm start
   ```

4. Open [http://localhost:3000](http://localhost:3000) in your browser.

### Build for Production

```bash
npm run build
```

This creates an optimized production build in the `build/` directory.

## Usage

1. **Sign up** for a new account or **log in** with existing credentials
2. **Navigate** to different sections using the dashboard cards
3. **Extract orders** to convert warehouse orders into delivery nodes
4. **Optimize routes** using AI with custom preferences
5. **Handle situations** using the AI dispatcher assistant

The frontend communicates with the Flask backend API for all functionality.