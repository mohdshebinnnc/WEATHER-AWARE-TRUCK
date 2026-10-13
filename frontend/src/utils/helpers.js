/**
 * Utility functions and design tokens for Weather-Aware Truck Routing.
 * Color palette: white + medium-blue (#3984E8) accent.
 */

export const PALETTE = {
  primary: '#3984E8',
  primaryHover: '#2F73D2',
  lightBlue: '#EAF3FF',
  paleBlue: '#F4F8FF',
  white: '#FFFFFF',
  textPrimary: '#202938',
  textSecondary: '#667085',
  textMuted: '#98A2B3',
  border: '#E4EAF2',
  borderLight: '#F1F5F9',
  surfaceSubtle: '#F8FAFD',

  // Risk
  low: '#16A36A',
  moderate: '#E9A23B',
  high: '#E97835',
  severe: '#D94848',
  noTravel: '#A92535',
  unknown: '#98A2B3',

  // Route colors
  routeRecommended: '#3984E8',
  routeAlt1: '#16A6A0',
  routeAlt2: '#E97835',
  routeAlt3: '#7C3AED',
};

/**
 * Get CSS class suffix for a risk level.
 */
export function getRiskClass(risk) {
  if (!risk) return 'unknown';
  const map = {
    'Low': 'low',
    'Moderate': 'moderate',
    'High': 'high',
    'Severe': 'severe',
    'No Travel': 'no-travel',
    'Unknown': 'unknown',
  };
  return map[risk] || 'unknown';
}

/**
 * Get the hex color for a risk level.
 */
export function getRiskColor(risk) {
  const map = {
    'Low': PALETTE.low,
    'Moderate': PALETTE.moderate,
    'High': PALETTE.high,
    'Severe': PALETTE.severe,
    'No Travel': PALETTE.noTravel,
    'Unknown': PALETTE.unknown,
  };
  return map[risk] || PALETTE.unknown;
}

/**
 * Format seconds as "Xh Ym".
 */
export function formatDuration(seconds) {
  if (!seconds && seconds !== 0) return '—';
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (h === 0) return `${m}m`;
  return `${h}h ${m}m`;
}

/**
 * Format miles with one decimal.
 */
export function formatMiles(miles) {
  if (miles == null) return '—';
  return `${miles.toFixed(1)} mi`;
}

/**
 * Format a date for display.
 */
export function formatDateTime(isoString) {
  if (!isoString) return '—';
  const d = new Date(isoString);
  return d.toLocaleString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  });
}

/**
 * Get the default departure time (next whole hour from now).
 */
export function getDefaultDepartureTime() {
  const now = new Date();
  now.setMinutes(0, 0, 0);
  now.setHours(now.getHours() + 1);
  const y = now.getFullYear();
  const mo = String(now.getMonth() + 1).padStart(2, '0');
  const d = String(now.getDate()).padStart(2, '0');
  const h = String(now.getHours()).padStart(2, '0');
  const mi = String(now.getMinutes()).padStart(2, '0');
  return `${y}-${mo}-${d}T${h}:${mi}`;
}

/**
 * Calculate the total risk-miles percentage for a route.
 */
export function getRiskDistribution(riskMiles, totalDistance) {
  if (!riskMiles || !totalDistance || totalDistance === 0) return [];

  const levels = [
    { key: 'low', label: 'Low', color: PALETTE.low },
    { key: 'moderate', label: 'Moderate', color: PALETTE.moderate },
    { key: 'high', label: 'High', color: PALETTE.high },
    { key: 'severe', label: 'Severe', color: PALETTE.severe },
    { key: 'no_travel', label: 'No Travel', color: PALETTE.noTravel },
    { key: 'unknown', label: 'Unknown', color: PALETTE.unknown },
  ];

  return levels
    .filter((l) => (riskMiles[l.key] || 0) > 0)
    .map((l) => ({
      ...l,
      miles: riskMiles[l.key],
      pct: ((riskMiles[l.key] / totalDistance) * 100).toFixed(1),
    }));
}

/**
 * Distinct route color mapping.
 * Recommended: #3984E8 (Medium Blue)
 * Alt 1: #16A6A0 (Teal)
 * Alt 2: #E97835 (Orange)
 * Alt 3: #7C3AED (Purple)
 */
export function getRouteColor(index, isRecommended) {
  if (isRecommended) return PALETTE.routeRecommended;
  const altPalette = [PALETTE.routeAlt1, PALETTE.routeAlt2, PALETTE.routeAlt3, '#475569'];
  return altPalette[index % altPalette.length];
}
