import { useState, useCallback } from 'react';
import { Navigation, AlertCircle } from 'lucide-react';
import TripForm from './components/TripForm';
import RouteMap from './components/RouteMap';
import ResultsPanel from './components/ResultsPanel';
import ForecastSlider from './components/ForecastSlider';
import CheckpointTable from './components/CheckpointTable';
import { analyzeTrip } from './services/api';

export default function App() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const [selectedRouteId, setSelectedRouteId] = useState(null);
  const [selectedCheckpoint, setSelectedCheckpoint] = useState(null);
  const [forecastCheckpoints, setForecastCheckpoints] = useState(null);
  const [tripParams, setTripParams] = useState(null);

  const handleSubmit = useCallback(async (params) => {
    setLoading(true);
    setError(null);
    setResult(null);
    setSelectedRouteId(null);
    setSelectedCheckpoint(null);
    setForecastCheckpoints(null);
    setTripParams(params);

    try {
      const data = await analyzeTrip(params);
      setResult(data);

      const recId = data.recommendation?.recommended_route_id;
      const initialRouteId = recId || data.routes?.[0]?.route_id || null;
      setSelectedRouteId(initialRouteId);

      const activeRoute = data.routes?.find((r) => r.route_id === initialRouteId) || data.routes?.[0];
      if (activeRoute?.checkpoints?.length > 0) {
        setSelectedCheckpoint(activeRoute.checkpoints[0]);
      }
    } catch (err) {
      console.error('Analysis error:', err);
      const message =
        err.response?.data?.error ||
        err.response?.data?.detail ||
        err.message ||
        'An unexpected error occurred while analyzing routes. Please verify origin and destination and retry.';
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleSelectRoute = useCallback((routeId) => {
    setSelectedRouteId(routeId);
    if (result?.routes) {
      const route = result.routes.find((r) => r.route_id === routeId);
      if (route?.checkpoints?.length > 0) {
        setSelectedCheckpoint(route.checkpoints[0]);
      }
    }
  }, [result]);

  const handleForecastUpdate = useCallback((forecastData) => {
    if (!forecastData?.routes || !selectedRouteId) {
      setForecastCheckpoints(null);
      return;
    }
    const selectedForecast = forecastData.routes.find((r) => r.route_id === selectedRouteId);
    setForecastCheckpoints(selectedForecast?.checkpoints || null);
  }, [selectedRouteId]);

  const activeRoute = result?.routes?.find((r) => r.route_id === selectedRouteId) || result?.routes?.[0];
  const activeCheckpoints = forecastCheckpoints || activeRoute?.checkpoints || [];

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', background: '#F8FAFD' }}>
      {/* Header */}
      <header style={{
        background: '#FFFFFF',
        borderBottom: '1px solid #E4EAF2',
        position: 'sticky',
        top: 0,
        zIndex: 30,
      }}>
        <div style={{
          maxWidth: 1440,
          margin: '0 auto',
          padding: '0 24px',
          height: 56,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{
              width: 34,
              height: 34,
              borderRadius: 8,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              background: '#3984E8',
              color: '#FFFFFF',
              flexShrink: 0,
            }}>
              <Navigation size={16} strokeWidth={2.2} />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ fontWeight: 700, fontSize: 15, color: '#202938', letterSpacing: '-0.01em' }}>
                  Weather-Aware Routing
                </span>
                <span style={{
                  fontSize: 10,
                  fontWeight: 600,
                  padding: '2px 7px',
                  borderRadius: 4,
                  background: '#EAF3FF',
                  color: '#3984E8',
                  border: '1px solid rgba(57, 132, 232, 0.2)',
                }}>
                  Commercial Fleet
                </span>
              </div>
              <p style={{ fontSize: 12, color: '#667085', marginTop: 1 }} className="hidden sm:block">
                Real-time weather hazard mitigation for heavy vehicles
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: '#667085' }}>
              <span style={{ width: 7, height: 7, borderRadius: '50%', background: '#16A36A', display: 'inline-block' }} />
              <span style={{ fontWeight: 500 }} className="hidden md:inline">Open-Meteo & OSRM</span>
              <span style={{
                fontSize: 11,
                fontFamily: 'var(--font-mono)',
                padding: '2px 6px',
                borderRadius: 4,
                background: '#F4F8FF',
                color: '#667085',
                border: '1px solid #E4EAF2',
              }}>
                v1.0
              </span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main style={{
        flex: 1,
        maxWidth: 1440,
        margin: '0 auto',
        padding: '20px 24px 32px',
        width: '100%',
      }}>
        {/* Page Title */}
        <div style={{ marginBottom: 20 }}>
          <h1 style={{ fontSize: 26, fontWeight: 700, color: '#202938', letterSpacing: '-0.02em', lineHeight: 1.2 }}>
            Weather-aware route planning
          </h1>
          <p style={{ fontSize: 14, color: '#667085', marginTop: 4 }}>
            Compare alternative truck routes using forecast conditions, cargo weight, and estimated travel time.
          </p>
        </div>

        {/* Dashboard Grid */}
        <div className="dashboard-grid">
          {/* Left Column */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <TripForm onSubmit={handleSubmit} loading={loading} />

            {error && (
              <div className="card" style={{ padding: 14, background: '#FEF2F2', borderColor: '#FECACA' }}>
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
                  <AlertCircle size={16} style={{ flexShrink: 0, marginTop: 1, color: '#D94848' }} />
                  <div>
                    <div style={{ fontWeight: 600, fontSize: 13, color: '#D94848', marginBottom: 2 }}>
                      Analysis Failed
                    </div>
                    <p style={{ fontSize: 12, color: '#667085', lineHeight: 1.5 }}>
                      {error}
                    </p>
                  </div>
                </div>
              </div>
            )}

            {loading && (
              <div className="card" style={{ padding: 24, textAlign: 'center' }}>
                <div className="spinner" style={{ margin: '0 auto 12px' }} />
                <div style={{ fontWeight: 600, fontSize: 13, color: '#202938' }}>
                  Evaluating Corridors & Weather
                </div>
                <p style={{ fontSize: 12, color: '#667085', marginTop: 4 }}>
                  Sampling atmospheric points along routes…
                </p>
              </div>
            )}

            {result && (
              <ResultsPanel
                routes={result.routes}
                recommendation={result.recommendation}
                warnings={result.warnings}
                selectedRouteId={selectedRouteId}
                onSelectRoute={handleSelectRoute}
              />
            )}
          </div>

          {/* Right Column */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16, minWidth: 0 }}>
            <RouteMap
              routes={result?.routes}
              selectedRouteId={selectedRouteId}
              recommendedRouteId={result?.recommendation?.recommended_route_id}
              forecastCheckpoints={forecastCheckpoints}
              onSelectCheckpoint={setSelectedCheckpoint}
            />

            {result && (
              <ForecastSlider
                routes={result.routes}
                loadWeight={tripParams?.load_weight_lb || 45000}
                departureTime={tripParams?.departure_time}
                onForecastUpdate={handleForecastUpdate}
              />
            )}

            {result && (
              <CheckpointTable
                checkpoints={activeCheckpoints}
                routeName={activeRoute?.name}
                selectedCheckpoint={selectedCheckpoint}
                onSelectCheckpoint={setSelectedCheckpoint}
              />
            )}

            {result?.metadata && (
              <div style={{ fontSize: 11, textAlign: 'center', padding: '4px 0', color: '#98A2B3' }}>
                Analysis completed at{' '}
                {new Date(result.metadata.analysis_timestamp).toLocaleTimeString()}{' '}
                · {result.metadata.num_routes} routes · {result.metadata.forecast_horizon_note}
              </div>
            )}
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer style={{
        background: '#FFFFFF',
        borderTop: '1px solid #E4EAF2',
        padding: '14px 24px',
        marginTop: 'auto',
      }}>
        <div style={{ maxWidth: 1440, margin: '0 auto', textAlign: 'center', fontSize: 11, color: '#98A2B3' }}>
          Weather-Aware Truck Routing · Django, React, Leaflet, Open-Meteo & OSRM
        </div>
      </footer>
    </div>
  );
}
