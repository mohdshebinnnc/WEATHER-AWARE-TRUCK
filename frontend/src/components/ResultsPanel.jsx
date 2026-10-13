import { CheckCircle2, AlertTriangle, ShieldAlert } from 'lucide-react';
import RouteCard from './RouteCard';

/**
 * Results panel adhering strictly to Section 3 of the prompt:
 * Reorganizes content into:
 * 1. Recommendation summary
 * 2. API / data availability warnings (compact separate region)
 * 3. Route comparison heading
 * 4. Route comparison cards
 */
export default function ResultsPanel({
  routes,
  recommendation,
  warnings,
  selectedRouteId,
  onSelectRoute,
}) {
  if (!routes || routes.length === 0) return null;

  const hasRecommendedRoute = Boolean(recommendation?.recommended_route_id);

  return (
    <div className="space-y-5 animate-slide-up">
      {/* 1. Recommendation Summary */}
      {recommendation && (
        <div
          className="card p-4 sm:p-5 transition-all shadow-sm"
          style={{
            background: hasRecommendedRoute ? 'var(--color-accent-pale)' : '#FEF2F2',
            borderColor: hasRecommendedRoute ? 'rgba(57, 132, 232, 0.3)' : 'rgba(239, 68, 68, 0.3)',
          }}
        >
          <div className="flex items-start gap-3">
            <div
              className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0 mt-0.5"
              style={{
                background: hasRecommendedRoute ? 'var(--color-accent-light)' : '#FEE2E2',
                color: hasRecommendedRoute ? 'var(--color-accent)' : '#DC2626',
              }}
            >
              {hasRecommendedRoute ? (
                <CheckCircle2 size={18} strokeWidth={2.5} />
              ) : (
                <ShieldAlert size={18} strokeWidth={2.5} />
              )}
            </div>

            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <h3 className="font-bold text-sm text-[#1E293B]">
                  {hasRecommendedRoute ? 'Optimal Route Recommendation' : 'No Safe Route Available'}
                </h3>
                {hasRecommendedRoute && (
                  <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-[#3984E8] text-white">
                    Verified Safe
                  </span>
                )}
              </div>
              <p className="text-xs mt-1.5 leading-relaxed text-[#475569]">
                {recommendation.explanation ||
                  (hasRecommendedRoute
                    ? 'This route minimizes atmospheric risk exposure and complies with commercial truck constraints.'
                    : 'All evaluated corridors exceed safe operating limits. Consider delaying departure.')}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* 2. API or Data Availability Warnings (Separate compact alert region) */}
      {warnings && warnings.length > 0 && (
        <div className="p-3.5 rounded-lg text-xs space-y-1.5 bg-[#FFFBEB] border border-[#FDE68A] shadow-xs">
          {warnings.map((w, i) => (
            <div key={i} className="flex items-start gap-2 text-[#B45309]">
              <AlertTriangle size={15} className="shrink-0 mt-0.5 text-[#D97706]" />
              <span className="leading-relaxed">{w}</span>
            </div>
          ))}
        </div>
      )}

      {/* 3. Route Comparison Heading & 4. Route Cards */}
      <div className="space-y-3.5">
        <div className="flex items-center justify-between pb-1 border-b border-[#E2E8F0]">
          <h3 className="text-xs font-bold uppercase tracking-wider text-[#64748B]">
            Evaluated Corridors ({routes.length})
          </h3>
          <span className="text-[11px] text-[#94A3B8]">
            Click card to highlight on map
          </span>
        </div>

        {routes.map((route, idx) => (
          <RouteCard
            key={route.route_id}
            route={route}
            routeIndex={idx}
            isRecommended={route.route_id === recommendation?.recommended_route_id}
            isSelected={route.route_id === selectedRouteId}
            recommendationExplanation={
              route.route_id === recommendation?.recommended_route_id
                ? recommendation?.explanation
                : null
            }
            onClick={() => onSelectRoute(route.route_id)}
          />
        ))}
      </div>
    </div>
  );
}
