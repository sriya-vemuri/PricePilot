import React from 'react';

const STATUS_MESSAGES = {
  unavailable_insufficient_data:        'Limited comparable data',
  unavailable_suppressed_near_baseline: 'Avg suppressed — too close to baseline',
  unavailable_service_mode:             'Use range instead',
};

export default function PriceGauge({ recommended, low, high, baseline, competitorAvg, competitorAvgStatus, pricingMode = 'retail' }) {
  const isService = pricingMode === 'service';
  const compLabel = isService ? 'Typical Market Cost' : 'Competitor Avg';
  const rangeLabel = isService ? 'Market Cost Range' : 'Price Range Analysis';
  // Strict guard: treat 0, NaN, undefined, null all as "no value"
  const hasCompetitorAvg = typeof competitorAvg === 'number' && competitorAvg > 0;
  const range = (high || 0) - (low || 0);
  const getPosition = (val) => range > 0 ? Math.max(4, Math.min(96, ((val - low) / range) * 100)) : 50;

  return (
    <div className="bg-card rounded-2xl shadow-warm border border-[hsl(35,20%,88%)] p-8">
      <p className="text-[11px] font-medium text-[hsl(25,15%,52%)] uppercase tracking-[0.12em] mb-6">{rangeLabel}</p>

      {/* Hero price */}
      <div className="text-center mb-10">
        <p className="text-[11px] text-[hsl(25,15%,55%)] uppercase tracking-[0.12em] mb-2">Recommended</p>
        <p className="font-serif text-[hsl(25,40%,14%)] text-6xl leading-none">${recommended?.toFixed(2)}</p>
        <p className="text-[12px] text-[hsl(25,15%,58%)] mt-3">
          Range: <span className="font-medium text-[hsl(25,25%,30%)]">${low?.toFixed(2)} — ${high?.toFixed(2)}</span>
        </p>
      </div>

      {/* Track */}
      <div className="relative py-10">
        {/* Gradient track */}
        <div className="h-2 rounded-full bg-gradient-to-r from-[hsl(35,30%,82%)] via-[hsl(38,55%,72%)] to-[hsl(35,30%,82%)] relative">

          {/* Baseline marker */}
          {baseline && (
            <div className="absolute top-0 -translate-y-full pb-1.5 flex flex-col items-center"
              style={{ left: `${getPosition(baseline)}%`, transform: `translateX(-50%) translateY(-100%)` }}>
              <span className="text-[9px] font-medium text-[hsl(25,20%,55%)] uppercase tracking-wider whitespace-nowrap mb-1">Baseline</span>
              <div className="w-px h-4 bg-[hsl(35,25%,72%)]" />
            </div>
          )}

          {/* Competitor marker */}
          {hasCompetitorAvg && (
            <div className="absolute bottom-0 translate-y-full pt-1.5 flex flex-col items-center"
              style={{ left: `${getPosition(competitorAvg)}%`, transform: `translateX(-50%) translateY(100%)` }}>
              <div className="w-px h-4 bg-[hsl(25,35%,58%)]" />
              <span className="text-[9px] font-medium text-[hsl(25,35%,45%)] uppercase tracking-wider whitespace-nowrap mt-1">{isService ? 'Typical cost' : 'Comp. avg'}</span>
            </div>
          )}

          {/* Recommended dot */}
          <div
            className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2"
            style={{ left: `${getPosition(recommended)}%` }}
          >
            <div className="h-5 w-5 rounded-full bg-[hsl(25,40%,22%)] border-2 border-[hsl(36,40%,97%)] shadow-warm-md ring-2 ring-[hsl(25,40%,22%)]/20" />
          </div>
        </div>

        {/* Range labels */}
        <div className="flex justify-between mt-8">
          <span className="text-[11px] text-[hsl(25,15%,55%)]">${low?.toFixed(2)}</span>
          <span className="text-[11px] text-[hsl(25,15%,55%)]">${high?.toFixed(2)}</span>
        </div>
      </div>

      {/* Price grid */}
      <div className={`grid gap-3 mt-2 ${isService && !hasCompetitorAvg ? 'grid-cols-2' : 'grid-cols-3'}`}>
        {/* Baseline */}
        <div className="rounded-xl p-3 text-center bg-[hsl(38,30%,93%)] border border-[hsl(35,20%,87%)]">
          <p className="text-[10px] uppercase tracking-wider mb-1 text-[hsl(25,15%,55%)]">Baseline</p>
          <p className="text-[15px] font-semibold text-[hsl(25,35%,22%)]">${baseline?.toFixed(2)}</p>
        </div>

        {/* Competitor Avg / Typical Cost — never render 0 or blank */}
        {(!isService || hasCompetitorAvg) && (
          <div className="rounded-xl p-3 text-center bg-[hsl(38,30%,93%)] border border-[hsl(35,20%,87%)]">
            <p className="text-[10px] uppercase tracking-wider mb-1 text-[hsl(25,15%,55%)]">{compLabel}</p>
            {hasCompetitorAvg ? (
              <p className="text-[15px] font-semibold text-[hsl(25,35%,22%)]">${competitorAvg.toFixed(2)}</p>
            ) : (
              <div title="Average hidden because evidence was too limited or too close to baseline to be reliable.">
                <p className="text-[12px] font-medium text-[hsl(25,15%,55%)] leading-tight">
                  {STATUS_MESSAGES[competitorAvgStatus] || 'Limited comparable data'}
                </p>
                <p className="text-[9px] text-[hsl(25,15%,62%)] mt-0.5">Use range instead ↑</p>
              </div>
            )}
          </div>
        )}

        {/* Recommended */}
        <div className="rounded-xl p-3 text-center bg-[hsl(25,40%,22%)] border border-[hsl(25,40%,30%)]">
          <p className="text-[10px] uppercase tracking-wider mb-1 text-[hsl(38,25%,75%)]">Recommended</p>
          <p className="text-[15px] font-semibold text-[hsl(38,33%,95%)]">${recommended?.toFixed(2)}</p>
        </div>
      </div>
    </div>
  );
}