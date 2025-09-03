// Route Optimizer Frontend - Mapbox Integration
// ⚠️ IMPORTANT: You need to add your Mapbox access token below
// Get your free token at: https://account.mapbox.com/access-tokens/
let mapboxgl_available = true;
try {
    if (typeof mapboxgl !== 'undefined') {
        mapboxgl.accessToken = 'YOUR_MAPBOX_ACCESS_TOKEN_HERE'; // Replace with your actual token
    } else {
        mapboxgl_available = false;
    }
} catch (error) {
    mapboxgl_available = false;
}

let map;
let isLoggedIn = false;
let currentRoutes = null;

// Initialize the map
function initMap() {
    if (!mapboxgl_available || typeof mapboxgl === 'undefined') {
        // Handle case where Mapbox is not available (e.g., in demo/test environment)
        console.log('Mapbox not available, running in demo mode');
        const mapContainer = document.getElementById('map');
        mapContainer.innerHTML = `
            <div style="display: flex; align-items: center; justify-content: center; height: 100%; background: #f0f0f0; color: #666;">
                <div style="text-align: center;">
                    <h3>🗺️ Map Demo Mode</h3>
                    <p>Add your Mapbox token to see the interactive map</p>
                    <p>Routes will be displayed here with real traffic data</p>
                </div>
            </div>
        `;
        map = null; // Set map to null to handle in other functions
        return;
    }
    
    try {
        map = new mapboxgl.Map({
            container: 'map',
            style: 'mapbox://styles/mapbox/streets-v11',
            center: [-0.1278, 51.5074], // London coordinates as default
            zoom: 10
        });
        
        map.addControl(new mapboxgl.NavigationControl());
    } catch (error) {
        // Handle case where Mapbox is not available (e.g., in demo/test environment)
        console.log('Mapbox initialization failed, running in demo mode');
        const mapContainer = document.getElementById('map');
        mapContainer.innerHTML = `
            <div style="display: flex; align-items: center; justify-content: center; height: 100%; background: #f0f0f0; color: #666;">
                <div style="text-align: center;">
                    <h3>🗺️ Map Demo Mode</h3>
                    <p>Mapbox initialization failed</p>
                    <p>Routes will be displayed in text format</p>
                </div>
            </div>
        `;
        map = null; // Set map to null to handle in other functions
    }
}

// Login function
async function login() {
    const email = document.getElementById('auth-email').value;
    const password = document.getElementById('auth-password').value;
    
    if (!email || !password) {
        showError('Please enter both email and password');
        return;
    }
    
    try {
        const response = await fetch('/api/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ email, password })
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            isLoggedIn = true;
            document.getElementById('optimize-btn').disabled = false;
            document.getElementById('load-btn').disabled = false;
            showSuccess('Login successful! You can now optimize routes.');
        } else {
            showError('Login failed: ' + data.message);
        }
    } catch (error) {
        showError('Login error: ' + error.message);
    }
}

// Optimize routes function
async function optimizeRoutes() {
    if (!isLoggedIn) {
        showError('Please login first');
        return;
    }
    
    const numVehicles = document.getElementById('num-vehicles').value;
    const vehicleCapacity = document.getElementById('vehicle-capacity').value;
    const preferences = document.getElementById('preferences').value;
    
    showLoading('Optimizing routes with real-time traffic data...');
    
    try {
        const response = await fetch('/api/solve', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                num_vehicles: parseInt(numVehicles),
                vehicle_capacity: parseInt(vehicleCapacity),
                preferences: preferences
            })
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            showSuccess(`Routes optimized! Trip ID: ${data.trip_id}`);
            // Load the newly created route
            loadRoute(data.trip_id);
        } else {
            showError('Route optimization failed: ' + data.message);
        }
    } catch (error) {
        showError('Optimization error: ' + error.message);
    }
}

// Load latest route
async function loadLatestRoute() {
    if (!isLoggedIn) {
        showError('Please login first');
        return;
    }
    
    showLoading('Loading latest route...');
    
    try {
        const response = await fetch('/api/routes/latest');
        const data = await response.json();
        
        if (data.status === 'success') {
            displayRoute(data.route_detail);
            showRouteDetails(data);
        } else {
            showError('Failed to load route: ' + data.message);
        }
    } catch (error) {
        showError('Error loading route: ' + error.message);
    }
}

// Load specific route by trip_id
async function loadRoute(tripId) {
    showLoading('Loading route details...');
    
    try {
        const response = await fetch(`/api/routes/${tripId}`);
        const data = await response.json();
        
        if (data.status === 'success') {
            displayRoute(data.route_detail);
            showRouteDetails(data);
        } else {
            showError('Failed to load route: ' + data.message);
        }
    } catch (error) {
        showError('Error loading route: ' + error.message);
    }
}

// Display route on map
function displayRoute(routeData) {
    currentRoutes = routeData;
    
    if (!map) {
        // Show route data in text format when map is not available
        showRouteDataAsText(routeData);
        return;
    }
    
    // Clear existing layers
    clearMap();
    
    if (!routeData || !routeData.refined_routes) {
        showError('Invalid route data');
        return;
    }
    
    // Colors for different vehicles
    const vehicleColors = ['#45b7d1', '#96ceb4', '#feca57', '#ff9ff3', '#f8b500'];
    
    // Add depot marker
    if (routeData.depot) {
        addDepotMarker(routeData.depot);
    }
    
    // Process each vehicle route
    routeData.refined_routes.forEach((route, index) => {
        const color = vehicleColors[index % vehicleColors.length];
        const vehicleId = route.vehicle || `Vehicle ${index + 1}`;
        
        if (route.sequence && route.sequence.length > 0) {
            // Add customer markers
            route.sequence.forEach((stop, stopIndex) => {
                if (stop.id !== routeData.depot?.id) {
                    addCustomerMarker(stop, vehicleId, color);
                    
                    // Add support stations if available
                    if (stop.nearby_petrol_stations) {
                        stop.nearby_petrol_stations.forEach(station => {
                            addSupportStationMarker(station, 'petrol');
                        });
                    }
                    
                    if (stop.nearby_repair_shops) {
                        stop.nearby_repair_shops.forEach(shop => {
                            addSupportStationMarker(shop, 'repair');
                        });
                    }
                }
            });
            
            // Draw route line
            drawRouteLine(route.sequence, color, vehicleId);
        }
    });
    
    // Fit map to show all points
    fitMapToBounds();
    
    hideLoading();
}

// Add depot marker
function addDepotMarker(depot) {
    const popup = new mapboxgl.Popup().setHTML(`
        <div>
            <h3>🏭 Depot</h3>
            <p><strong>ID:</strong> ${depot.id}</p>
            <p><strong>Location:</strong> ${depot.lat.toFixed(4)}, ${depot.lon.toFixed(4)}</p>
        </div>
    `);
    
    new mapboxgl.Marker({ color: '#ff6b6b' })
        .setLngLat([depot.lon, depot.lat])
        .setPopup(popup)
        .addTo(map);
}

// Add customer marker
function addCustomerMarker(stop, vehicleId, color) {
    const popup = new mapboxgl.Popup().setHTML(`
        <div>
            <h3>📦 Customer</h3>
            <p><strong>ID:</strong> ${stop.id}</p>
            <p><strong>Vehicle:</strong> ${vehicleId}</p>
            <p><strong>Location:</strong> ${stop.lat.toFixed(4)}, ${stop.lon.toFixed(4)}</p>
            ${stop.weight ? `<p><strong>Weight:</strong> ${stop.weight} kg</p>` : ''}
            ${stop.time_window ? `<p><strong>Time Window:</strong> ${stop.time_window}</p>` : ''}
        </div>
    `);
    
    new mapboxgl.Marker({ color: '#4ecdc4' })
        .setLngLat([stop.lon, stop.lat])
        .setPopup(popup)
        .addTo(map);
}

// Add support station marker
function addSupportStationMarker(station, type) {
    const icon = type === 'petrol' ? '⛽' : '🔧';
    const popup = new mapboxgl.Popup().setHTML(`
        <div>
            <h3>${icon} ${station.name}</h3>
            <p><strong>Address:</strong> ${station.address}</p>
            <p><strong>Distance:</strong> ${station.distance_km} km</p>
        </div>
    `);
    
    new mapboxgl.Marker({ color: '#ff9ff3' })
        .setLngLat([station.lon, station.lat])
        .setPopup(popup)
        .addTo(map);
}

// Draw route line
function drawRouteLine(sequence, color, vehicleId) {
    const coordinates = sequence.map(stop => [stop.lon, stop.lat]);
    
    const lineId = `route-${vehicleId}`;
    
    map.addSource(lineId, {
        type: 'geojson',
        data: {
            type: 'Feature',
            properties: {},
            geometry: {
                type: 'LineString',
                coordinates: coordinates
            }
        }
    });
    
    map.addLayer({
        id: lineId,
        type: 'line',
        source: lineId,
        layout: {
            'line-join': 'round',
            'line-cap': 'round'
        },
        paint: {
            'line-color': color,
            'line-width': 3,
            'line-opacity': 0.8
        }
    });
}

// Clear map of existing route data
function clearMap() {
    // Remove all existing markers and layers
    const existingMarkers = document.querySelectorAll('.mapboxgl-marker');
    existingMarkers.forEach(marker => marker.remove());
    
    // Remove route layers
    if (map.isStyleLoaded()) {
        map.getStyle().layers.forEach(layer => {
            if (layer.id.startsWith('route-')) {
                map.removeLayer(layer.id);
                map.removeSource(layer.id);
            }
        });
    }
}

// Fit map to show all route points
function fitMapToBounds() {
    if (!currentRoutes || !currentRoutes.refined_routes) return;
    
    const bounds = new mapboxgl.LngLatBounds();
    
    // Add depot to bounds
    if (currentRoutes.depot) {
        bounds.extend([currentRoutes.depot.lon, currentRoutes.depot.lat]);
    }
    
    // Add all customer locations to bounds
    currentRoutes.refined_routes.forEach(route => {
        if (route.sequence) {
            route.sequence.forEach(stop => {
                bounds.extend([stop.lon, stop.lat]);
            });
        }
    });
    
    map.fitBounds(bounds, { padding: 50 });
}

// Show route details in sidebar
function showRouteDetails(routeData) {
    const detailsDiv = document.getElementById('route-details');
    let html = '';
    
    if (routeData.route_detail && routeData.route_detail.refined_routes) {
        routeData.route_detail.refined_routes.forEach((route, index) => {
            const metrics = route.metrics || {};
            
            html += `
                <div class="route-info">
                    <h3>🚛 ${route.vehicle || `Vehicle ${index + 1}`}</h3>
                    <div class="metric">
                        <span class="label">Stops:</span>
                        <span class="value">${route.sequence ? route.sequence.length - 1 : 0}</span>
                    </div>
                    ${metrics.total_distance_km ? `
                    <div class="metric">
                        <span class="label">Distance:</span>
                        <span class="value">${metrics.total_distance_km} km</span>
                    </div>` : ''}
                    ${metrics.total_traffic_duration_mins ? `
                    <div class="metric">
                        <span class="label">Traffic Duration:</span>
                        <span class="value">${metrics.total_traffic_duration_mins} min</span>
                    </div>` : ''}
                    ${metrics.total_normal_duration_mins ? `
                    <div class="metric">
                        <span class="label">Normal Duration:</span>
                        <span class="value">${metrics.total_normal_duration_mins} min</span>
                    </div>` : ''}
                </div>
            `;
        });
    }
    
    if (routeData.summary) {
        html += `
            <div class="route-info">
                <h3>📋 Trip Summary</h3>
                <p style="font-size: 0.85rem; line-height: 1.4;">${routeData.summary}</p>
            </div>
        `;
    }
    
    detailsDiv.innerHTML = html;
}

// Utility functions for UI feedback
function showLoading(message) {
    const detailsDiv = document.getElementById('route-details');
    detailsDiv.innerHTML = `<div class="loading">${message}</div>`;
}

function hideLoading() {
    // Loading will be replaced by route details or error message
}

function showError(message) {
    const detailsDiv = document.getElementById('route-details');
    detailsDiv.innerHTML = `<div class="error">❌ ${message}</div>`;
}

function showSuccess(message) {
    const detailsDiv = document.getElementById('route-details');
    detailsDiv.innerHTML = `<div class="route-info"><h3>✅ Success</h3><p>${message}</p></div>`;
}

// Show route data in text format (when map is not available)
function showRouteDataAsText(routeData) {
    const mapContainer = document.getElementById('map');
    let html = `
        <div style="padding: 2rem; background: #f8f9fa; height: 100%; overflow-y: auto;">
            <h3>📊 Route Data (Demo Mode)</h3>
    `;
    
    if (routeData.depot) {
        html += `
            <div style="margin-bottom: 1rem; padding: 1rem; background: white; border-radius: 4px;">
                <h4>🏭 Depot: ${routeData.depot.id}</h4>
                <p>Location: ${routeData.depot.lat.toFixed(4)}, ${routeData.depot.lon.toFixed(4)}</p>
            </div>
        `;
    }
    
    routeData.refined_routes.forEach((route, index) => {
        const colors = ['#45b7d1', '#96ceb4', '#feca57', '#ff9ff3'];
        const color = colors[index % colors.length];
        
        html += `
            <div style="margin-bottom: 1rem; padding: 1rem; background: white; border-radius: 4px; border-left: 4px solid ${color};">
                <h4>🚛 ${route.vehicle || `Vehicle ${index + 1}`}</h4>
        `;
        
        if (route.metrics) {
            html += `
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; margin-bottom: 1rem; font-size: 0.9rem;">
                    ${route.metrics.total_distance_km ? `<div><strong>Distance:</strong> ${route.metrics.total_distance_km} km</div>` : ''}
                    ${route.metrics.total_traffic_duration_mins ? `<div><strong>Traffic Time:</strong> ${route.metrics.total_traffic_duration_mins} min</div>` : ''}
                </div>
            `;
        }
        
        if (route.sequence) {
            html += `<div><strong>Route Sequence:</strong></div><ol style="margin: 0.5rem 0;">`;
            route.sequence.forEach(stop => {
                const isDepot = stop.id === routeData.depot?.id;
                html += `
                    <li style="margin: 0.25rem 0;">
                        ${isDepot ? '🏭' : '📦'} ${stop.id}
                        ${stop.weight ? ` (${stop.weight} kg)` : ''}
                        ${stop.nearby_petrol_stations ? ` - ⛽ ${stop.nearby_petrol_stations.length} stations nearby` : ''}
                    </li>
                `;
            });
            html += `</ol>`;
        }
        
        html += `</div>`;
    });
    
    html += `</div>`;
    mapContainer.innerHTML = html;
    hideLoading();
}

// Initialize the application
window.onload = function() {
    initMap();
    
    // Add some sample instructions
    showSuccess('Welcome! Please login to start optimizing routes with real-time traffic data.');
};