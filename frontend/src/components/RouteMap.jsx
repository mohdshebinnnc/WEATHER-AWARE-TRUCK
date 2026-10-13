import { useEffect, useMemo } from 'react';
import { MapContainer, TileLayer, Polyline, CircleMarker, Popup, useMap } from 'react-leaflet';
import { getRiskColor, getRouteColor, formatMiles, formatDateTime, PALETTE } from '../utils/helpers';

/**
 * Automatically fits map viewport bounds when routes change.
 */
function FitBounds({ routes }) {
  const map = useMap();

  useEffect(() => {
    if (!routes || routes.length === 0) return;

    const allCoords = routes.flatMap((r) => r.geometry || []);
    if (allCoords.length === 0) return;

    const lats = allCoords.map((c) => c[0]);
    const lons = allCoords.map((c) => c[1]);

    map.fitBounds(
      [
        [Math.min(...lats), Math.min(...lons)],
        [Math.max(...lats), Math.max(...lons)],
      ],
      { padding: [50, 50], maxZoom: 12, animate: true }
    );
  }, [routes, map]);

  return null;
}

/**
 * Interactive Leaflet Map for truck routing and real-time weather risk visualization.
 * Uses full-color OpenStreetMap basemap with high-contrast route alternatives.
 */
export default function RouteMap({
  routes,
  selectedRouteId,
  recommendedRouteId,
  forecastCheckpoints,
  onSelectCheckpoint,
}) {
  const defaultCenter = [39.8283, -98.5795]; // Center of Continental US
  const hasRoutes = routes && routes.length > 0;

  // Center coordinate derived from active route or fallback
  const center = useMemo(() => {
    if (!hasRoutes) return defaultCenter;
    const selectedRoute = routes.find((r) => r.route_id === selectedRouteId) || routes[0];
    const firstCoord = selectedRoute?.geometry?.[0];
    return firstCoord ? [firstCoord[0], firstCoord[1]] : defaultCenter;
  }, [hasRoutes, routes, selectedRouteId]);

  // Determine checkpoints to render
  const visibleCheckpoints = useMemo(() => {
    if (forecastCheckpoints && forecastCheckpoints.length > 0) {
      return forecastCheckpoints;
    }
    if (!hasRoutes) return [];
    const activeRoute = routes.find((r) => r.route_id === selectedRouteId) || routes[0];
    return activeRoute?.checkpoints || [];
  }, [forecastCheckpoints, hasRoutes, routes, selectedRouteId]);

  // Origin & Destination coordinates for markers
  const { originCoord, destCoord } = useMemo(() => {
    if (!hasRoutes) return { originCoord: null, destCoord: null };
    const activeRoute = routes.find((r) => r.route_id === selectedRouteId) || routes[0];
    const geom = activeRoute?.geometry;
    if (!geom || geom.length === 0) return { originCoord: null, destCoord: null };
    return {
      originCoord: geom[0],
      destCoord: geom[geom.length - 1],
    };
  }, [hasRoutes, routes, selectedRouteId]);

  return (
    <div className="card overflow-hidden relative shadow-sm" style={{ height: 440 }}>
      {/* Full-color Interactive Map */}
      <MapContainer
        center={center}
        zoom={hasRoutes ? 6 : 4}
        style={{ height: '100%', width: '100%' }}
        scrollWheelZoom={true}
        zoomControl={true}
      >
        {/* Full-Color OpenStreetMap Navigation Tiles */}
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          maxZoom={19}
        />

        {hasRoutes && <FitBounds routes={routes} />}

        {/* Polylines: Alternative routes rendered first; Selected/active route on top */}
        {hasRoutes &&
          [...routes]
            .sort((a, b) => {
              if (a.route_id === selectedRouteId) return 1;
              if (b.route_id === selectedRouteId) return -1;
              return 0;
            })
            .map((route) => {
              const routeIdx = routes.findIndex((r) => r.route_id === route.route_id);
              const isSelected = route.route_id === selectedRouteId;
              const isRec = route.route_id === recommendedRouteId;
              const routeColor = getRouteColor(routeIdx, isRec);

              return (
                <Polyline
                  key={route.route_id}
                  positions={route.geometry}
                  pathOptions={{
                    color: routeColor,
                    weight: isSelected ? 6.5 : 4.5,
                    opacity: isSelected ? 1 : 0.75,
                    dashArray: route.risk_stats?.is_eligible === false ? '8 6' : null,
                  }}
                />
              );
            })}

        {/* Origin Pin Marker */}
        {originCoord && (
          <CircleMarker
            center={originCoord}
            radius={8}
            pathOptions={{
              color: '#FFFFFF',
              fillColor: '#16A34A',
              fillOpacity: 1,
              weight: 3,
            }}
          >
            <Popup>
              <div className="text-xs font-semibold py-0.5 text-[#16A34A]">
                Trip Origin Point
              </div>
            </Popup>
          </CircleMarker>
        )}

        {/* Destination Pin Marker */}
        {destCoord && (
          <CircleMarker
            center={destCoord}
            radius={8}
            pathOptions={{
              color: '#FFFFFF',
              fillColor: '#DC2626',
              fillOpacity: 1,
              weight: 3,
            }}
          >
            <Popup>
              <div className="text-xs font-semibold py-0.5 text-[#DC2626]">
                Trip Destination Point
              </div>
            </Popup>
          </CircleMarker>
        )}

        {/* Weather Checkpoint Markers */}
        {visibleCheckpoints.map((cp, idx) => {
          const risk = cp.risk?.overall_risk || 'Unknown';
          const color = getRiskColor(risk);
          const weather = cp.weather || {};
          const etaVal = cp.eta || cp.estimated_arrival_time;

          return (
            <CircleMarker
              key={`marker-${idx}-${cp.cumulative_distance_miles}`}
              center={[cp.lat, cp.lon]}
              radius={6}
              eventHandlers={{
                click: () => onSelectCheckpoint && onSelectCheckpoint(cp),
              }}
              pathOptions={{
                color: '#FFFFFF',
                fillColor: color,
                fillOpacity: 1,
                weight: 2.5,
              }}
            >
              <Popup>
                <div style={{ minWidth: 200, padding: '2px 0' }}>
                  {/* Header */}
                  <div className="flex items-center justify-between pb-2 mb-2" style={{ borderBottom: '1px solid var(--color-border)' }}>
                    <span className="text-xs font-semibold" style={{ color: 'var(--color-text-primary)' }}>
                      Mile {cp.cumulative_distance_miles != null ? cp.cumulative_distance_miles.toFixed(1) : '—'}
                    </span>
                    <span
                      className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider"
                      style={{
                        backgroundColor: `${color}18`,
                        color: color,
                        border: `1px solid ${color}35`,
                      }}
                    >
                      {risk} Risk
                    </span>
                  </div>

                  {/* Weather Metrics */}
                  <div className="grid grid-cols-3 gap-1.5 text-xs mb-2 text-center">
                    <div className="p-1.5 rounded" style={{ background: 'var(--color-bg-secondary)' }}>
                      <div className="text-[10px]" style={{ color: 'var(--color-text-muted)' }}>Wind</div>
                      <div className="font-semibold text-xs mt-0.5" style={{ color: 'var(--color-text-primary)' }}>
                        {weather.wind_speed_mph != null ? `${weather.wind_speed_mph.toFixed(0)} mph` : '—'}
                      </div>
                    </div>

                    <div className="p-1.5 rounded" style={{ background: 'var(--color-bg-secondary)' }}>
                      <div className="text-[10px]" style={{ color: 'var(--color-text-muted)' }}>Rain</div>
                      <div className="font-semibold text-xs mt-0.5" style={{ color: 'var(--color-text-primary)' }}>
                        {weather.rain_rate_in_hr != null ? `${weather.rain_rate_in_hr.toFixed(2)}` : '0.00'}
                      </div>
                    </div>

                    <div className="p-1.5 rounded" style={{ background: 'var(--color-bg-secondary)' }}>
                      <div className="text-[10px]" style={{ color: 'var(--color-text-muted)' }}>Snow</div>
                      <div className="font-semibold text-xs mt-0.5" style={{ color: 'var(--color-text-primary)' }}>
                        {weather.snow_rate_in_hr != null ? `${weather.snow_rate_in_hr.toFixed(2)}` : '0.00'}
                      </div>
                    </div>
                  </div>

                  {/* ETA */}
                  {etaVal && (
                    <div className="text-[11px] mb-2" style={{ color: 'var(--color-text-secondary)' }}>
                      ETA: {formatDateTime(etaVal)}
                    </div>
                  )}

                  {/* Risk Explanation */}
                  {cp.risk?.risk_explanation && (
                    <div
                      className="text-[10px] p-1.5 rounded leading-tight"
                      style={{
                        background: `${color}10`,
                        color: 'var(--color-text-secondary)',
                        border: `1px solid ${color}25`,
                      }}
                    >
                      {cp.risk.risk_explanation}
                    </div>
                  )}
                </div>
              </Popup>
            </CircleMarker>
          );
        })}
      </MapContainer>

      {/* Floating Ready State Badge when no routes loaded */}
      {!hasRoutes && (
        <div className="absolute top-4 left-1/2 -translate-x-1/2 z-[400] pointer-events-none">
          <div
            className="flex items-center gap-2 px-3.5 py-2 rounded-full text-xs font-medium backdrop-blur-md shadow-md"
            style={{
              background: 'rgba(255, 255, 255, 0.95)',
              color: 'var(--color-text-secondary)',
              border: '1px solid var(--color-border)',
            }}
          >
            <div className="w-2 h-2 rounded-full animate-ping" style={{ background: 'var(--color-accent)' }} />
            <span>Ready for corridor routing · Enter trip parameters to evaluate weather risks</span>
          </div>
        </div>
      )}

      {/* Floating Map Legend (Bottom Right) */}
      <div
        className="absolute bottom-4 right-4 z-[400] card px-3.5 py-2.5 text-[11px] backdrop-blur-md shadow-md space-y-1.5"
        style={{
          background: 'rgba(255, 255, 255, 0.96)',
          border: '1px solid var(--color-border)',
        }}
      >
        {/* Route Color Key */}
        {hasRoutes && (
          <div className="flex items-center gap-3 pb-1.5 border-b border-[#E2E8F0]">
            <span className="font-semibold text-[10px] uppercase tracking-wider text-[#64748B]">Routes:</span>
            {routes.map((r, i) => {
              const isRec = r.route_id === recommendedRouteId;
              const color = getRouteColor(i, isRec);
              const isSelected = r.route_id === selectedRouteId;
              return (
                <div key={r.route_id} className="flex items-center gap-1.5">
                  <span
                    className="w-3 h-1 rounded-full inline-block"
                    style={{
                      background: color,
                      height: isSelected ? 3.5 : 2,
                    }}
                  />
                  <span className={`text-[11px] ${isSelected ? 'font-bold text-[#1E293B]' : 'text-[#64748B]'}`}>
                    {r.name}
                  </span>
                </div>
              );
            })}
          </div>
        )}

        {/* Risk Classification Key */}
        <div className="flex items-center gap-3">
          <span className="font-semibold text-[10px] uppercase tracking-wider text-[#64748B]">Risk:</span>
          {[
            { label: 'Low', color: PALETTE.low },
            { label: 'Mod', color: PALETTE.moderate },
            { label: 'High', color: PALETTE.high },
            { label: 'Severe', color: PALETTE.severe },
            { label: 'No Travel', color: PALETTE.noTravel },
          ].map((item) => (
            <div key={item.label} className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full inline-block" style={{ background: item.color }} />
              <span style={{ color: 'var(--color-text-secondary)' }}>{item.label}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
