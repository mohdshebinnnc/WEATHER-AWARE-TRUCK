import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  timeout: 120000, // 2 min — route analysis can be slow
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * Geocode an address string to coordinates.
 * @param {string} query - Address or place name
 * @returns {Promise<Array>} List of geocode results
 */
export async function geocodeAddress(query) {
  const { data } = await api.get('/geocode/', { params: { q: query } });
  return data.results;
}

/**
 * Analyze a trip: generate routes, weather, risk, recommendation.
 * @param {Object} params
 * @param {Object} params.origin - { lat, lon, name }
 * @param {Object} params.destination - { lat, lon, name }
 * @param {string} params.departure_time - ISO 8601 datetime
 * @param {number} params.load_weight_lb - Cargo weight in pounds
 * @param {number} params.sampling_interval_miles - 10, 25, or 50
 * @returns {Promise<Object>} Analysis result
 */
export async function analyzeTrip(params) {
  const { data } = await api.post('/trips/analyze/', params);
  return data;
}

/**
 * Get forecast data for a specific hour offset (heatmap slider).
 * @param {Object} params
 * @param {number} params.forecast_hour - Hour offset from now (0-48)
 * @param {Array} params.routes - Route data with checkpoints
 * @param {number} params.load_weight_lb - Cargo weight
 * @returns {Promise<Object>} Forecast risk data
 */
export async function getForecast(params) {
  const { data } = await api.post('/trips/forecast/', params);
  return data;
}

/**
 * Health check
 */
export async function healthCheck() {
  const { data } = await api.get('/health/');
  return data;
}

export default api;
