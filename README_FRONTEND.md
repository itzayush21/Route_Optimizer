# Route Optimizer - Mapbox Frontend

A web-based frontend for the Route Optimizer system that displays real-time traffic-aware vehicle routing using Mapbox maps.

## Features

- 🗺️ **Interactive Mapbox Maps** - Visualize routes, customers, and support stations
- 🚦 **Real-Time Traffic Routing** - Routes optimized using current traffic conditions
- 🚛 **Multi-Vehicle Support** - Handle multiple vehicles with different routes
- ⛽ **Support Stations** - Display nearby petrol stations and repair shops
- 📊 **Route Metrics** - Show distance, time, and traffic-adjusted durations
- 💡 **Smart Rerouting** - AI-powered route optimization with Gemini

## Setup Instructions

### 1. Prerequisites

- Python 3.8+
- Flask and dependencies (install via `pip install -r requirements.txt`)
- Mapbox account for map visualization

### 2. Quick Demo Setup

For testing the frontend without full database setup:

```bash
# Run the demo application
python demo_app.py
```

Then open your browser to `http://localhost:5000`

### 3. Mapbox Configuration

1. Sign up for a free Mapbox account at [mapbox.com](https://account.mapbox.com/)
2. Create an access token at [account.mapbox.com/access-tokens/](https://account.mapbox.com/access-tokens/)
3. Replace `YOUR_MAPBOX_ACCESS_TOKEN_HERE` in `static/app.js` with your actual token

### 4. Full Production Setup

For the complete system with database:

1. Configure your `.env` file with database and API credentials:
   ```bash
   cp .env.example .env
   # Edit .env with your actual credentials
   ```

2. Set up required API keys:
   - Google Maps API key (for traffic data)
   - Gemini AI API key (for smart routing)
   - Supabase credentials (for authentication)

3. Run the full application:
   ```bash
   python app.py
   ```

## Usage

### Demo Mode

1. **Login**: Use any email address (demo mode accepts any credentials)
2. **Optimize Routes**: Click "Optimize Routes" to generate a sample route
3. **Load Route**: Click "Load Latest Route" to display the demo route on the map
4. **Explore**: Click on markers to see details about customers, depot, and support stations

### Production Mode

1. **Authentication**: Login with valid Supabase credentials
2. **Set Parameters**: Configure number of vehicles, capacity, and preferences
3. **Optimize**: Click "Optimize Routes" to run real-time traffic-aware optimization
4. **Visualize**: View optimized routes with traffic conditions on the map

## Frontend Features

### Map Visualization

- **Depot** (🏭): Red markers showing the warehouse/depot location
- **Customers** (📦): Teal markers for delivery locations
- **Route Lines**: Colored lines showing vehicle paths
- **Support Stations** (⛽🔧): Pink markers for petrol stations and repair shops

### Route Information

The sidebar displays:
- Vehicle assignments and metrics
- Distance and time calculations
- Traffic vs. normal duration comparisons
- Trip summaries with AI-generated insights

### Real-Time Features

- Traffic-adjusted route optimization
- Dynamic rerouting based on current conditions
- Support station recommendations
- Smart vehicle assignment

## API Endpoints

The frontend communicates with these backend endpoints:

- `POST /api/login` - User authentication
- `POST /api/solve` - Route optimization with traffic data
- `GET /api/routes/latest` - Get the most recent route
- `GET /api/routes/{trip_id}` - Get specific route by ID

## Technical Details

### Frontend Stack

- **HTML5** with responsive design
- **Vanilla JavaScript** (no frameworks for simplicity)
- **Mapbox GL JS** for interactive maps
- **CSS3** with modern styling

### Backend Integration

- **Flask** API server
- **CORS** enabled for frontend-backend communication
- **JSON** data exchange format
- **RESTful** API design

### Map Features

- Interactive navigation controls
- Responsive legend
- Popup information windows
- Dynamic marker styling
- Route line visualization

## Customization

### Styling

Edit the CSS in `static/index.html` to customize:
- Color schemes
- Layout and spacing
- Map controls
- Button styles

### Map Configuration

Modify `static/app.js` to change:
- Default map center and zoom
- Marker colors and icons
- Popup content
- Route line styling

### Demo Data

Update `demo_app.py` to change:
- Sample locations
- Route structures
- Metrics and timing
- Support station data

## Troubleshooting

### Common Issues

1. **Map doesn't load**: Check that your Mapbox token is valid and properly configured
2. **CORS errors**: Ensure Flask-CORS is installed and configured
3. **API connection**: Verify the backend server is running on port 5000
4. **No routes displayed**: Check browser console for JavaScript errors

### Debug Mode

Enable debug logging by:
1. Opening browser developer tools (F12)
2. Checking the Console tab for error messages
3. Monitoring Network tab for API request/response data

## Contributing

When adding new features:

1. Follow the existing code structure
2. Add proper error handling
3. Update the demo data if needed
4. Test both demo and production modes
5. Update this README with new features

## License

This project is part of the Route Optimizer system. See the main project for license details.