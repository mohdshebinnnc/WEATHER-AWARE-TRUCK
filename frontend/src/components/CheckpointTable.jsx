import { useState } from 'react';
import { ChevronDown, FileSpreadsheet, AlertTriangle } from 'lucide-react';
import { getRiskColor, formatDateTime, PALETTE } from '../utils/helpers';

/**
 * Checkpoint details section and data table adhering strictly to Section 6 & 11.
 * Features:
 * - Unclipped spotlight card for selected checkpoint
 * - 3 clean weather metrics: Wind, Rain, Snow
 * - Functional expand/collapse toggle for full table
 * - Hazard filter toggle
 */
export default function CheckpointTable({
  checkpoints,
  routeName,
  selectedCheckpoint,
  onSelectCheckpoint,
}) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [filterMode, setFilterMode] = useState('all'); // 'all' | 'risks_only'

  if (!checkpoints || checkpoints.length === 0) return null;

  // Filter checkpoints if "risks_only" is selected
  const filteredCheckpoints = filterMode === 'risks_only'
    ? checkpoints.filter((cp) => {
        const risk = cp.risk?.overall_risk;
        return risk && risk !== 'Low';
      })
    : checkpoints;

  // Active checkpoint details (selected or first one with risk or first overall)
  const activeCp = selectedCheckpoint || checkpoints[0];
  const activeWeather = activeCp?.weather || {};
  const activeRisk = activeCp?.risk?.overall_risk || 'Low';
  const activeRiskColor = getRiskColor(activeRisk);
  const activeEta = activeCp?.eta || activeCp?.estimated_arrival_time;

  return (
    <div className="card p-5 animate-fade-in space-y-4 shadow-sm">
      {/* 1. Header with Expand/Collapse & Filter */}
      <div className="flex items-center justify-between pb-2 border-b border-[#F1F5F9]">
        <div className="flex items-center gap-2.5">
          <div
            className="w-7 h-7 rounded-md flex items-center justify-center shrink-0"
            style={{ background: 'var(--color-accent-light)', color: 'var(--color-accent)' }}
          >
            <FileSpreadsheet size={15} strokeWidth={2.2} />
          </div>
          <div>
            <h3 className="font-bold text-sm text-[#1E293B]">
              Route Checkpoint Analysis
              <span className="font-normal text-xs text-[#64748B]">
                {' '}· {routeName || 'Active Route'}
              </span>
            </h3>
            <p className="text-[11px] text-[#64748B]">
              {checkpoints.length} weather stations sampled along this corridor
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Hazards Only Toggle */}
          <div className="flex rounded-md p-0.5 bg-[#F1F5F9] border border-[#E2E8F0]">
            <button
              type="button"
              onClick={() => setFilterMode('all')}
              className="text-[11px] px-2 py-0.5 rounded font-medium transition-all"
              style={{
                background: filterMode === 'all' ? '#FFFFFF' : 'transparent',
                color: filterMode === 'all' ? '#1E293B' : '#64748B',
                boxShadow: filterMode === 'all' ? '0 1px 2px rgba(0,0,0,0.05)' : 'none',
              }}
            >
              All ({checkpoints.length})
            </button>
            <button
              type="button"
              onClick={() => setFilterMode('risks_only')}
              className="text-[11px] px-2 py-0.5 rounded font-medium transition-all"
              style={{
                background: filterMode === 'risks_only' ? '#FFFFFF' : 'transparent',
                color: filterMode === 'risks_only' ? PALETTE.high : '#64748B',
                boxShadow: filterMode === 'risks_only' ? '0 1px 2px rgba(0,0,0,0.05)' : 'none',
              }}
            >
              Hazards Only
            </button>
          </div>

          {/* Expand/Collapse Toggle */}
          <button
            type="button"
            onClick={() => setIsExpanded((prev) => !prev)}
            className="btn-secondary text-xs h-7 px-2.5 flex items-center gap-1.5 cursor-pointer"
          >
            <span>{isExpanded ? 'Collapse' : 'Table'}</span>
            <ChevronDown
              size={13}
              style={{ transform: isExpanded ? 'rotate(180deg)' : 'none', transition: 'transform 0.15s ease' }}
            />
          </button>
        </div>
      </div>

      {/* 2. Selected Checkpoint Spotlight Card (Always visible, unclipped) */}
      {activeCp && (
        <div className="p-4 rounded-lg bg-[#F8FAFC] border border-[#E2E8F0] space-y-3">
          <div className="flex items-start justify-between gap-3">
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-sm text-[#1E293B]">
                  Checkpoint at Mile {activeCp.cumulative_distance_miles?.toFixed(1) || '0.0'}
                </span>
                <span
                  className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider"
                  style={{
                    backgroundColor: `${activeRiskColor}15`,
                    color: activeRiskColor,
                    border: `1px solid ${activeRiskColor}35`,
                  }}
                >
                  {activeRisk} Risk
                </span>
              </div>
              <div className="text-xs text-[#64748B] mt-1">
                Estimated Arrival (ETA): {activeEta ? formatDateTime(activeEta) : '—'}
              </div>
            </div>

            <div className="text-[11px] font-mono text-[#94A3B8] text-right">
              Lat {activeCp.lat?.toFixed(3)}, Lon {activeCp.lon?.toFixed(3)}
            </div>
          </div>

          {/* 3 Core Weather Metrics Grid */}
          <div className="grid grid-cols-3 gap-2.5">
            <div className="p-2.5 rounded-md bg-white border border-[#E2E8F0]">
              <div className="text-[10px] font-medium text-[#94A3B8]">Wind Speed</div>
              <div className="font-bold text-sm text-[#1E293B] mt-0.5">
                {activeWeather.wind_speed_mph != null ? `${activeWeather.wind_speed_mph.toFixed(1)} mph` : 'Unavailable'}
              </div>
            </div>

            <div className="p-2.5 rounded-md bg-white border border-[#E2E8F0]">
              <div className="text-[10px] font-medium text-[#94A3B8]">Rainfall Rate</div>
              <div className="font-bold text-sm text-[#1E293B] mt-0.5">
                {activeWeather.rain_rate_in_hr != null && activeWeather.rain_rate_in_hr > 0
                  ? `${activeWeather.rain_rate_in_hr.toFixed(2)} in/h`
                  : '0.00 in/h'}
              </div>
            </div>

            <div className="p-2.5 rounded-md bg-white border border-[#E2E8F0]">
              <div className="text-[10px] font-medium text-[#94A3B8]">Snowfall Rate</div>
              <div className="font-bold text-sm text-[#1E293B] mt-0.5">
                {activeWeather.snow_rate_in_hr != null && activeWeather.snow_rate_in_hr > 0
                  ? `${activeWeather.snow_rate_in_hr.toFixed(2)} in/h`
                  : '0.00 in/h'}
              </div>
            </div>
          </div>

          {/* Explanation Text */}
          {activeCp.risk?.risk_explanation && (
            <div className="text-xs text-[#475569] leading-relaxed pt-1 border-t border-[#EEF2F6]">
              {activeCp.risk.risk_explanation}
            </div>
          )}
        </div>
      )}

      {/* 3. Full Checkpoint Table (When Expanded) */}
      {isExpanded && (
        <div className="overflow-x-auto rounded-lg border border-[#E2E8F0] max-h-72 overflow-y-auto">
          <table className="w-full text-left text-xs" style={{ borderCollapse: 'separate', borderSpacing: 0 }}>
            <thead className="sticky top-0 bg-[#F8FAFC] z-10 border-b border-[#E2E8F0]">
              <tr className="text-[#64748B]">
                <th className="py-2 px-3 font-semibold text-[11px]">#</th>
                <th className="py-2 px-3 font-semibold text-[11px]">Mile</th>
                <th className="py-2 px-3 font-semibold text-[11px]">ETA</th>
                <th className="py-2 px-3 font-semibold text-[11px]">Wind</th>
                <th className="py-2 px-3 font-semibold text-[11px]">Rain</th>
                <th className="py-2 px-3 font-semibold text-[11px]">Snow</th>
                <th className="py-2 px-3 font-semibold text-[11px]">Risk</th>
              </tr>
            </thead>
            <tbody>
              {filteredCheckpoints.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-6 text-center text-xs text-[#94A3B8]">
                    No hazardous checkpoints found along this corridor
                  </td>
                </tr>
              ) : (
                filteredCheckpoints.map((cp, idx) => {
                  const wx = cp.weather || {};
                  const riskLevel = cp.risk?.overall_risk || 'Low';
                  const riskColor = getRiskColor(riskLevel);
                  const etaTime = cp.eta || cp.estimated_arrival_time;
                  const isCurrentSelected = activeCp === cp;

                  return (
                    <tr
                      key={`row-${idx}-${cp.cumulative_distance_miles}`}
                      className="cursor-pointer transition-colors border-t border-[#EEF2F6] hover:bg-[#F8FAFC]"
                      style={{
                        background: isCurrentSelected ? 'var(--color-accent-pale)' : 'transparent',
                      }}
                      onClick={() => onSelectCheckpoint && onSelectCheckpoint(cp)}
                    >
                      <td className="py-2 px-3 font-mono text-[11px] text-[#94A3B8]">{idx + 1}</td>
                      <td className="py-2 px-3 font-bold text-[#1E293B]">
                        {cp.cumulative_distance_miles != null ? `${cp.cumulative_distance_miles.toFixed(1)} mi` : '—'}
                      </td>
                      <td className="py-2 px-3 whitespace-nowrap text-[#475569]">
                        {etaTime ? formatDateTime(etaTime) : '—'}
                      </td>
                      <td className="py-2 px-3">
                        <span
                          style={{
                            color: wx.wind_speed_mph >= 35 ? PALETTE.high : '#1E293B',
                            fontWeight: wx.wind_speed_mph >= 35 ? 600 : 400,
                          }}
                        >
                          {wx.wind_speed_mph != null ? `${wx.wind_speed_mph.toFixed(1)} mph` : '—'}
                        </span>
                      </td>
                      <td className="py-2 px-3" style={{ color: wx.rain_rate_in_hr > 0 ? PALETTE.primary : '#94A3B8' }}>
                        {wx.rain_rate_in_hr != null ? `${wx.rain_rate_in_hr.toFixed(2)}` : '0.00'}
                      </td>
                      <td className="py-2 px-3" style={{ color: wx.snow_rate_in_hr > 0 ? '#0284C7' : '#94A3B8', fontWeight: wx.snow_rate_in_hr > 0 ? 600 : 400 }}>
                        {wx.snow_rate_in_hr != null ? `${wx.snow_rate_in_hr.toFixed(2)}` : '0.00'}
                      </td>
                      <td className="py-2 px-3">
                        <span
                          className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-semibold"
                          style={{
                            backgroundColor: `${riskColor}15`,
                            color: riskColor,
                            border: `1px solid ${riskColor}30`,
                          }}
                        >
                          <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: riskColor }} />
                          {riskLevel}
                        </span>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
