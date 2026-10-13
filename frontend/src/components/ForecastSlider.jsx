import { useState, useCallback } from 'react';
import { Clock, Info, Loader2 } from 'lucide-react';
import { getForecast } from '../services/api';
import { getRiskColor, getRouteColor, PALETTE } from '../utils/helpers';

/**
 * 0-48 hour forecast slider and weather-risk heatmap along the trip corridor.
 * Strictly adheres to Section 7 of the Prompt.
 */
export default function ForecastSlider({
  routes,
  loadWeight,
  departureTime,
  onForecastUpdate,
}) {
  const [hour, setHour] = useState(0);
  const [loading, setLoading] = useState(false);
  const [forecastData, setForecastData] = useState(null);
  const [error, setError] = useState(null);

  const handleSliderChange = useCallback(
    async (e) => {
      const newHour = parseInt(e.target.value, 10);
      setHour(newHour);

      if (!routes || routes.length === 0) return;

      setLoading(true);
      setError(null);

      try {
        const result = await getForecast({
          forecast_hour: newHour,
          departure_time: departureTime || new Date().toISOString(),
          routes: routes.map((r) => ({
            route_id: r.route_id,
            name: r.name,
            checkpoints: r.checkpoints.map((cp, idx) => ({
              checkpoint_id: cp.checkpoint_id ?? idx,
              lat: cp.lat,
              lon: cp.lon,
              cumulative_distance_miles: cp.cumulative_distance_miles,
              segment_distance_miles: cp.segment_distance_miles,
            })),
          })),
          load_weight_lb: loadWeight,
        });

        setForecastData(result);
        if (onForecastUpdate) {
          onForecastUpdate(result);
        }
      } catch (err) {
        console.error('Forecast error:', err);
        setError('Unable to fetch atmospheric forecast data for this horizon');
        setForecastData(null);
      } finally {
        setLoading(false);
      }
    },
    [routes, loadWeight, departureTime, onForecastUpdate]
  );

  const formatHourLabel = (h) => {
    if (h === 0) return 'Departure Hour (+0h)';
    if (h < 24) return `+${h} Hours`;
    const days = Math.floor(h / 24);
    const rem = h % 24;
    return rem === 0 ? `+${days} Day${days > 1 ? 's' : ''}` : `+${days}d ${rem}h`;
  };

  if (!routes || routes.length === 0) return null;

  return (
    <div className="card p-5 animate-fade-in space-y-4 shadow-sm">
      {/* 1. Header with Selected Hour Badge */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div
            className="w-7 h-7 rounded-md flex items-center justify-center shrink-0"
            style={{ background: 'var(--color-accent-light)', color: 'var(--color-accent)' }}
          >
            <Clock size={15} strokeWidth={2.2} />
          </div>
          <div>
            <h3 className="font-bold text-sm text-[#1E293B]">
              Corridor Weather Forecast (0–48h)
            </h3>
            <p className="text-[11px] text-[#64748B]">
              Preview weather risk evolution along corridors over time
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {loading && <Loader2 size={14} className="animate-spin text-[#3984E8]" />}
          <span
            className="px-3 py-1 rounded-md text-xs font-mono font-bold"
            style={{
              background: 'var(--color-accent-light)',
              color: 'var(--color-accent)',
              border: '1px solid rgba(57, 132, 232, 0.25)',
            }}
          >
            {formatHourLabel(hour)}
          </span>
        </div>
      </div>

      {/* 2. 0-48 Hour Slider Control */}
      <div className="space-y-1.5 px-0.5">
        <input
          type="range"
          id="forecast-timeline-slider"
          min="0"
          max="48"
          step="1"
          value={hour}
          onChange={handleSliderChange}
          className="w-full"
        />
        <div className="flex justify-between text-[11px] font-mono text-[#94A3B8]">
          <span>Departure (0h)</span>
          <span>+12h</span>
          <span>+24h</span>
          <span>+36h</span>
          <span>+48h Horizon</span>
        </div>
      </div>

      {/* 3. Heatmap Ribbon for each Route */}
      {forecastData?.routes ? (
        <div className="space-y-3 pt-1">
          {forecastData.routes.map((route, rIdx) => {
            const isRec = rIdx === 0;
            const rColor = getRouteColor(rIdx, isRec);
            return (
              <div key={route.route_id} className="space-y-1.5">
                <div className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full inline-block" style={{ backgroundColor: rColor }} />
                    <span className="font-semibold text-[#1E293B]">
                      {route.name || route.route_id}
                    </span>
                  </div>
                  <span className="text-[11px] text-[#94A3B8]">
                    {route.checkpoints?.length || 0} checkpoints
                  </span>
                </div>

                {/* Heatmap ribbon */}
                <div className="flex gap-px rounded-md overflow-hidden" style={{ height: 20, background: '#E2E8F0' }}>
                  {route.checkpoints &&
                    route.checkpoints.map((cp, idx) => {
                      const risk = cp.risk?.overall_risk || 'Unknown';
                      const color = getRiskColor(risk);
                      const wind = cp.weather?.wind_speed_mph;

                      return (
                        <div
                          key={idx}
                          className="flex-1 relative group cursor-pointer transition-opacity hover:opacity-85"
                          style={{ background: color, minWidth: 2 }}
                        >
                          {/* Tooltip on hover */}
                          <div
                            className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2.5 py-1.5 rounded text-[11px] whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-30 shadow-lg"
                            style={{
                              background: '#1E293B',
                              color: '#FFFFFF',
                            }}
                          >
                            <div className="font-semibold">Mile {cp.cumulative_distance_miles?.toFixed(0)} · {risk} Risk</div>
                            {wind != null && <div className="text-[10px] text-slate-300">Wind: {wind.toFixed(1)} mph</div>}
                          </div>
                        </div>
                      );
                    })}
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="text-center py-3 text-xs text-[#94A3B8] bg-[#F8FAFC] rounded-md border border-[#E2E8F0]">
          Move the slider above to query weather forecasts at future departure offsets
        </div>
      )}

      {/* 4. Explanatory Note & Compact Aligned Legend */}
      <div className="pt-3 border-t border-[#F1F5F9] flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-1.5 text-[11px] text-[#64748B]">
          <Info size={13} className="shrink-0 text-[#94A3B8]" />
          <span>Trip recommendation uses checkpoint arrival ETA; slider previews future atmospheric evolution.</span>
        </div>

        {/* Legend */}
        <div className="flex items-center gap-2.5 shrink-0">
          {[
            { label: 'Low', color: PALETTE.low },
            { label: 'Mod', color: PALETTE.moderate },
            { label: 'High', color: PALETTE.high },
            { label: 'Severe', color: PALETTE.severe },
            { label: 'No Travel', color: PALETTE.noTravel },
          ].map((item) => (
            <div key={item.label} className="flex items-center gap-1 text-[10px] text-[#475569]">
              <span className="w-2 h-2 rounded-full inline-block" style={{ background: item.color }} />
              <span>{item.label}</span>
            </div>
          ))}
        </div>
      </div>

      {error && (
        <div className="text-xs p-2.5 rounded-md bg-[#FEF2F2] border border-[#FECACA] text-[#DC2626]">
          {error}
        </div>
      )}
    </div>
  );
}
