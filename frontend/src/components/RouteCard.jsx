import { CheckCircle2, AlertTriangle, ShieldCheck, ShieldAlert } from 'lucide-react';
import { formatDuration, formatMiles, getRiskDistribution, formatDateTime, getRouteColor, PALETTE } from '../utils/helpers';

/**
 * Route comparison card adhering strictly to Section 3 of the prompt.
 * Features:
 * - Color-coded corridor indicator matching map polyline
 * - Clean non-redundant header
 * - 4-column balanced metrics grid
 * - Proportional risk distribution breakdown
 * - Clear recommendation rationale or safety alert
 */
export default function RouteCard({
  route,
  routeIndex,
  isRecommended,
  isSelected,
  recommendationExplanation,
  onClick,
}) {
  const { risk_stats: stats } = route;
  const distribution = getRiskDistribution(stats?.risk_miles, stats?.total_distance_miles);

  const severeMiles = stats?.risk_miles?.severe ?? 0;
  const highMiles = stats?.risk_miles?.high ?? 0;
  const noTravelMiles = stats?.risk_miles?.no_travel ?? 0;
  const isEligible = stats?.is_eligible !== false && noTravelMiles === 0;

  // Exact color of this route matching the map polyline
  const routeColor = getRouteColor(routeIndex, isRecommended);

  return (
    <div
      id={`route-card-${route.route_id}`}
      className={`card route-card p-4 sm:p-5 cursor-pointer transition-all ${
        isRecommended ? 'route-card--recommended' : ''
      } ${isSelected ? 'route-card--selected' : ''} ${
        !isEligible ? 'route-card--ineligible' : ''
      }`}
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onClick();
        }
      }}
    >
      {/* 1. Header Row: Route Name, Status, Distance & Duration */}
      <div className="flex items-center justify-between gap-3 pb-3 border-b border-[#F1F5F9]">
        <div className="flex items-center gap-2.5 min-w-0">
          {/* Corridor Color Swatch Indicator (matches map polyline) */}
          <span
            className="w-3.5 h-3.5 rounded-full shrink-0 shadow-xs border border-white"
            style={{ backgroundColor: routeColor }}
            title={`Corridor color: ${route.name}`}
          />

          <h3 className="font-bold text-sm text-[#1E293B] truncate">
            {route.name}
          </h3>

          {isRecommended && isEligible && (
            <span
              className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold shrink-0"
              style={{
                background: 'var(--color-accent-light)',
                color: 'var(--color-accent)',
                border: '1px solid rgba(57, 132, 232, 0.25)',
              }}
            >
              <CheckCircle2 size={12} strokeWidth={2.5} />
              Recommended
            </span>
          )}

          {!isEligible && (
            <span className="risk-badge risk-badge--no-travel text-[10px] shrink-0">
              <ShieldAlert size={11} /> Unsafe
            </span>
          )}
        </div>

        {/* Distance & Duration */}
        <div className="text-right shrink-0">
          <span className="font-bold text-sm text-[#1E293B]">
            {formatMiles(route.distance_miles)}
          </span>
          <span className="text-xs text-[#64748B] ml-2">
            ({formatDuration(route.duration_s)})
          </span>
        </div>
      </div>

      {/* 2. Metrics Section (4 Equal Columns on Desktop, 2 on Mobile) */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 my-3.5">
        <div className="p-2.5 rounded-md bg-[#F8FAFC] border border-[#E2E8F0]">
          <div className="text-[10px] font-medium text-[#94A3B8]">Estimated Arrival</div>
          <div className="text-xs font-semibold text-[#1E293B] mt-0.5 truncate">
            {route.eta ? formatDateTime(route.eta) : '—'}
          </div>
        </div>

        <div className="p-2.5 rounded-md bg-[#F8FAFC] border border-[#E2E8F0]">
          <div className="text-[10px] font-medium text-[#94A3B8]">Average Risk</div>
          <div className="text-xs font-semibold text-[#1E293B] mt-0.5">
            {stats?.average_risk?.toFixed(2) ?? '1.00'} <span className="text-[10px] font-normal text-[#94A3B8]">/ 5</span>
          </div>
        </div>

        <div className="p-2.5 rounded-md bg-[#F8FAFC] border border-[#E2E8F0]">
          <div className="text-[10px] font-medium text-[#94A3B8]">High-Risk Miles</div>
          <div
            className="text-xs font-semibold mt-0.5"
            style={{ color: highMiles > 0 ? PALETTE.high : '#1E293B' }}
          >
            {formatMiles(highMiles)}
          </div>
        </div>

        <div className="p-2.5 rounded-md bg-[#F8FAFC] border border-[#E2E8F0]">
          <div className="text-[10px] font-medium text-[#94A3B8]">Severe / No Travel</div>
          <div
            className="text-xs font-semibold mt-0.5"
            style={{ color: (severeMiles + noTravelMiles) > 0 ? PALETTE.severe : '#1E293B' }}
          >
            {formatMiles(severeMiles + noTravelMiles)}
          </div>
        </div>
      </div>

      {/* 3. Risk Breakdown: Segmented Bar + Legend + Checkpoint Count */}
      {distribution.length > 0 && (
        <div className="space-y-1.5 pt-1">
          <div className="flex items-center justify-between text-[11px] text-[#64748B]">
            <span className="font-medium text-[10px] uppercase tracking-wider text-[#94A3B8]">Risk Distribution</span>
            <span>{stats?.num_checkpoints || 0} checkpoints</span>
          </div>

          <div className="risk-bar">
            {distribution.map((d) => (
              <div
                key={d.key}
                className="risk-bar__segment"
                style={{
                  width: `${d.pct}%`,
                  backgroundColor: d.color,
                }}
                title={`${d.label}: ${d.miles.toFixed(1)} mi (${d.pct}%)`}
              />
            ))}
          </div>

          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 pt-1">
            {distribution.map((d) => (
              <div key={d.key} className="flex items-center gap-1.5 text-[11px] text-[#475569]">
                <span className="w-2 h-2 rounded-full shrink-0" style={{ background: d.color }} />
                <span>{d.label}: {d.miles.toFixed(1)} mi</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 4. Footer: Recommendation Explanation or Safety Notice */}
      {isRecommended && isEligible && recommendationExplanation && (
        <div className="mt-3.5 p-2.5 rounded-md bg-[#F0FDF4] border border-[#BBF7D0] flex items-start gap-2">
          <ShieldCheck size={15} className="shrink-0 mt-0.5 text-[#16A34A]" />
          <span className="text-[11px] text-[#166534] leading-relaxed">
            {recommendationExplanation}
          </span>
        </div>
      )}

      {!isEligible && (
        <div className="mt-3.5 p-2.5 rounded-md bg-[#FEF2F2] border border-[#FECACA] flex items-start gap-2">
          <AlertTriangle size={15} className="shrink-0 mt-0.5 text-[#DC2626]" />
          <span className="text-[11px] text-[#991B1B] leading-relaxed">
            {stats?.eligibility_reason || 'Severe weather conditions or extreme crosswinds exceed safe operating limits.'}
          </span>
        </div>
      )}
    </div>
  );
}
