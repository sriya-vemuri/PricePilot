import React from 'react';

const MODE_CONFIG = {
  market_led:          { label: 'Market-led',          bg: 'bg-[hsl(140,30%,93%)]',  text: 'text-[hsl(140,40%,32%)]',  border: 'border-[hsl(140,30%,82%)]' },
  baseline_led:        { label: 'Baseline-led',         bg: 'bg-[hsl(38,45%,90%)]',   text: 'text-[hsl(35,40%,30%)]',   border: 'border-[hsl(38,40%,80%)]' },
  feasibility_override:{ label: 'Feasibility override', bg: 'bg-[hsl(4,55%,93%)]',    text: 'text-[hsl(4,55%,36%)]',    border: 'border-[hsl(4,40%,82%)]' },
};

const BASELINE_STATUS = {
  implausible: { label: 'Implausible baseline', bg: 'bg-[hsl(4,55%,93%)]', text: 'text-[hsl(4,55%,36%)]', border: 'border-[hsl(4,40%,82%)]' },
  plausible:   { label: 'Plausible baseline',   bg: 'bg-[hsl(140,30%,93%)]', text: 'text-[hsl(140,40%,32%)]', border: 'border-[hsl(140,30%,82%)]' },
};

export default function PricingRationale({ analysis }) {
  if (!analysis) return null;

  const mode = MODE_CONFIG[analysis.recommendation_mode] || MODE_CONFIG.baseline_led;
  const baselineTag = BASELINE_STATUS[analysis.baseline_status] || BASELINE_STATUS.plausible;

  // Build a concise 3–5 line summary from structured fields
  const lines = [];

  // 1. Baseline line
  if (analysis.baseline_price) {
    lines.push(
      analysis.baseline_status === 'implausible'
        ? `Cost-plus baseline of $${analysis.baseline_price?.toFixed(2)} was flagged as implausible for this market. ${analysis.baseline_conflict_reason || ''}`
        : `Cost-plus baseline: $${analysis.baseline_price?.toFixed(2)}. This aligns with expected pricing for this category.`
    );
  }

  // 2. Market evidence line
  if (analysis.trace_filtered_count >= 3) {
    lines.push(
      analysis.baseline_status === 'implausible'
        ? `Market evidence (${analysis.trace_filtered_count} validated prices, range $${analysis.trace_filtered_low?.toFixed(2)}–$${analysis.trace_filtered_high?.toFixed(2)}) was used as the primary anchor instead.`
        : `Market evidence from ${analysis.trace_filtered_count} validated comparable prices was incorporated (range $${analysis.trace_filtered_low?.toFixed(2)}–$${analysis.trace_filtered_high?.toFixed(2)}).`
    );
  } else if (analysis.trace_prices_found > 0) {
    lines.push(`Only ${analysis.trace_filtered_count ?? 0} clean price${analysis.trace_filtered_count !== 1 ? 's' : ''} found — below the 3-source threshold. Market evidence was not used.`);
  } else {
    lines.push('No comparable market prices found. Recommendation is based entirely on cost and margin inputs.');
  }

  // 3. Sanity / override note
  if (analysis.sanity_triggered) {
    lines.push('Market data showed inconsistencies — the recommendation was pulled conservatively toward the cost-plus baseline.');
  }

  // 4. Demand/trend context (brief)
  if (analysis.demand_signal && analysis.demand_signal !== 'moderate') {
    const demandLabel = analysis.demand_signal.replace('_', ' ');
    const trendLabel = analysis.trace_market_trend?.replace('_', ' ');
    lines.push(`Demand signal: ${demandLabel}${trendLabel ? ` · Market trend: ${trendLabel}` : ''}.`);
  }

  return (
    <div className="bg-card rounded-2xl border border-[hsl(35,20%,88%)] p-7 shadow-warm">
      {/* Header row */}
      <div className="flex items-center justify-between mb-5">
        <p className="text-[11px] font-medium text-[hsl(25,15%,52%)] uppercase tracking-[0.14em]">Why this price?</p>
        <div className="flex items-center gap-2">
          <span className={`text-[10px] font-semibold px-2.5 py-1 rounded-lg border ${baselineTag.bg} ${baselineTag.text} ${baselineTag.border}`}>
            {baselineTag.label}
          </span>
          <span className={`text-[10px] font-semibold px-2.5 py-1 rounded-lg border ${mode.bg} ${mode.text} ${mode.border}`}>
            {mode.label}
          </span>
        </div>
      </div>

      {/* Summary lines */}
      <div className="space-y-2.5">
        {lines.map((line, i) => (
          <p key={i} className="text-[13.5px] text-[hsl(25,25%,20%)] leading-relaxed">
            {line}
          </p>
        ))}
      </div>
    </div>
  );
}