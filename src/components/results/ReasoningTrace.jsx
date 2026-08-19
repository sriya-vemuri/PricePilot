import React from 'react';
import { Search, Filter, TrendingUp, TrendingDown, Minus, Activity, BarChart2, GitBranch, AlertCircle, CheckCircle2 } from 'lucide-react';

const demandLabels = { very_low: 'Very Low', low: 'Low', moderate: 'Moderate', high: 'High', very_high: 'Very High' };
const demandColors = {
  very_high: 'text-[hsl(150,42%,36%)] bg-[hsl(150,35%,92%)]',
  high:      'text-[hsl(140,38%,40%)] bg-[hsl(140,30%,93%)]',
  moderate:  'text-[hsl(38,45%,42%)] bg-[hsl(38,45%,93%)]',
  low:       'text-[hsl(25,55%,42%)] bg-[hsl(25,55%,93%)]',
  very_low:  'text-[hsl(4,55%,48%)] bg-[hsl(4,55%,95%)]',
};
const trendCfg = {
  surging:  { icon: Activity,     color: 'text-[hsl(150,42%,36%)]', label: 'Surging',  note: 'Upward pressure supports higher pricing.' },
  growing:  { icon: TrendingUp,   color: 'text-[hsl(140,38%,40%)]', label: 'Growing',  note: 'Growing market supports holding or raising price.' },
  stable:   { icon: Minus,        color: 'text-[hsl(38,45%,42%)]',  label: 'Stable',   note: 'Stable market — no trend adjustment.' },
  declining:{ icon: TrendingDown, color: 'text-[hsl(4,55%,48%)]',   label: 'Declining',note: 'Declining market applied conservative pressure.' },
};

/**
 * @param {{ label: string; value: string; note?: string; highlight?: boolean }} props
 */
function DataRow({ label, value, note, highlight }) {
  return (
    <div className={`flex items-start justify-between gap-4 py-2.5 border-b border-[hsl(35,20%,91%)] last:border-0 ${highlight ? 'bg-[hsl(25,40%,22%)] -mx-5 px-5 rounded-xl my-1' : ''}`}>
      <span className={`text-[12px] ${highlight ? 'text-[hsl(38,25%,75%)]' : 'text-[hsl(25,20%,48%)]'}`}>{label}</span>
      <div className="text-right">
        <span className={`text-[13px] font-semibold tabular-nums ${highlight ? 'text-[hsl(38,33%,95%)] font-serif text-[15px]' : 'text-[hsl(25,35%,20%)]'}`}>{value}</span>
        {note && <p className="text-[11px] text-[hsl(25,15%,58%)] mt-0.5">{note}</p>}
      </div>
    </div>
  );
}

/**
 * @param {{ stepNum: number; icon: import('react').ComponentType<{ className?: string }>; iconColor?: string; label: string; value: string; sub?: string; pill?: string; pillColor?: string; done?: boolean }} props
 */
function TraceStep({ stepNum, icon: Icon, iconColor, label, value, sub, pill, pillColor, done }) {
  return (
    <div className="flex items-start gap-3">
      <div className="flex flex-col items-center flex-shrink-0">
        <div className={`h-7 w-7 rounded-full flex items-center justify-center border text-[10px] font-bold ${done ? 'bg-[hsl(140,35%,45%)] border-[hsl(140,35%,45%)] text-white' : 'bg-[hsl(38,35%,93%)] border-[hsl(35,20%,84%)] text-[hsl(25,25%,45%)]'}`}>
          {done ? <CheckCircle2 className="h-3.5 w-3.5" /> : stepNum}
        </div>
      </div>
      <div className="flex-1 min-w-0 pb-5">
        <p className="text-[11px] font-medium text-[hsl(25,15%,52%)] uppercase tracking-[0.1em] mb-0.5">{label}</p>
        <div className="flex items-center gap-2 flex-wrap">
          <span className={`text-[13px] text-[hsl(25,25%,20%)]`}>{value}</span>
          {pill && (
            <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-md ${pillColor || 'bg-[hsl(38,40%,90%)] text-[hsl(25,35%,32%)]'}`}>{pill}</span>
          )}
        </div>
        {sub && <p className="text-[11px] text-[hsl(25,15%,56%)] mt-0.5 leading-relaxed">{sub}</p>}
      </div>
    </div>
  );
}

export default function ReasoningTrace({ analysis }) {
  const {
    trace_tavily_query, trace_prices_found, trace_filtered_low, trace_filtered_high,
    trace_filtered_count, trace_used_fallback, trace_market_trend, trace_demand_level,
    trace_competitor_avg_used, baseline_price, recommended_price, strategy,
    confidence_score, confidence_explanation,
    number_of_valid_prices, price_variance, pricing_basis,
  } = analysis;

  const hasTrace = trace_tavily_query || trace_demand_level || trace_market_trend || baseline_price;
  if (!hasTrace) return null;

  const trend = trendCfg[trace_market_trend] || trendCfg.stable;
  const TrendIcon = trend.icon;
  const demand = trace_demand_level || analysis.demand_signal;
  const demandCls = demandColors[demand] || demandColors.moderate;

  const confidenceLabel = confidence_score >= 65 ? 'High' : confidence_score >= 42 ? 'Medium' : 'Low';
  const confidenceColor = confidence_score >= 65
    ? 'text-[hsl(140,38%,40%)] bg-[hsl(140,30%,93%)]'
    : confidence_score >= 42
    ? 'text-[hsl(38,45%,42%)] bg-[hsl(38,45%,93%)]'
    : 'text-[hsl(4,55%,48%)] bg-[hsl(4,55%,95%)]';

  const validPrices = number_of_valid_prices ?? trace_filtered_count ?? 0;
  const rejected = (trace_prices_found ?? 0) - validPrices;
  const cvLabel = (() => {
    if (price_variance === null || price_variance === undefined) return null;
    if (price_variance <= 0.10) return 'Low variance';
    if (price_variance <= 0.25) return 'Moderate variance';
    return 'High variance';
  })();

  // Backend sends snake_case enums; map to the existing display labels.
  const basisKey = (pricing_basis || '').toLowerCase();
  const pricingBasisDisplay =
    basisKey === 'market_driven' ? 'Market-driven'
    : basisKey === 'market_aligned' ? 'Market-aligned'
    : basisKey === 'baseline_driven' ? 'Baseline-driven'
    : pricing_basis
      || (trace_used_fallback ? 'Baseline-driven' : validPrices >= 11 ? 'Market-driven' : validPrices >= 5 ? 'Market-aligned' : 'Baseline-driven');
  const basisColor = pricingBasisDisplay === 'Market-driven'
    ? 'text-[hsl(140,40%,32%)] bg-[hsl(140,30%,92%)]'
    : pricingBasisDisplay === 'Market-aligned'
    ? 'text-[hsl(38,50%,32%)] bg-[hsl(38,55%,90%)]'
    : 'text-[hsl(25,40%,32%)] bg-[hsl(25,35%,91%)]';

  const steps = [
    {
      label: 'Baseline Price',
      icon: BarChart2, iconColor: 'text-[hsl(25,40%,38%)]',
      value: `$${baseline_price?.toFixed(2)}`,
      sub: `Formula: cost ÷ (1 − margin%). Unaffected by market data.`,
    },
    {
      label: 'Competitor Data (US Retail, USD)',
      icon: Filter, iconColor: trace_used_fallback ? 'text-[hsl(38,50%,38%)]' : 'text-[hsl(140,38%,40%)]',
      value: trace_used_fallback
        ? 'Limited comparable pricing data'
        : trace_competitor_avg_used
          ? `$${trace_filtered_low?.toFixed(2)} – $${trace_filtered_high?.toFixed(2)} (avg $${trace_competitor_avg_used?.toFixed(2)})`
          : `$${trace_filtered_low?.toFixed(2)} – $${trace_filtered_high?.toFixed(2)} (avg suppressed — near-baseline)`,
      sub: trace_used_fallback
        ? `Only ${validPrices} comparable USD price${validPrices !== 1 ? 's' : ''} found from ${trace_prices_found ?? 0} raw — below the 3-price threshold for market-informed pricing.`
        : `${validPrices} of ${trace_prices_found ?? '?'} USD prices kept · ${rejected > 0 ? `${rejected} rejected · ` : ''}${cvLabel || ''}`,
      pill: trace_used_fallback ? 'Baseline-driven' : `${validPrices} prices`,
      pillColor: trace_used_fallback ? 'bg-[hsl(38,55%,90%)] text-[hsl(38,50%,32%)]' : 'bg-[hsl(140,30%,92%)] text-[hsl(140,40%,32%)]',
    },
    {
      label: 'Demand Signal',
      icon: TrendingUp, iconColor: demandColors[demand]?.split(' ')[0],
      value: `Demand is ${demandLabels[demand] || demand}`,
      sub: demand === 'high' || demand === 'very_high'
        ? `High demand → price premium applied.`
        : demand === 'low' || demand === 'very_low'
        ? `Low demand → downward pressure on price.`
        : `Moderate demand → no adjustment.`,
      pill: demandLabels[demand],
      pillColor: demandCls,
    },
    {
      label: 'Market Trend',
      icon: TrendIcon, iconColor: trend.color,
      value: `Market is ${trend.label}`,
      sub: trend.note,
    },
    {
      label: 'Strategy Applied',
      icon: GitBranch, iconColor: 'text-[hsl(25,35%,38%)]',
      value: `${strategy?.charAt(0).toUpperCase() + strategy?.slice(1)} strategy`,
      sub: strategy === 'aggressive'
        ? `Anchored toward lower end of filtered range to gain share.`
        : strategy === 'premium'
        ? `Anchored toward upper end of filtered range to signal quality.`
        : `Anchored near midpoint of filtered range.`,
      pill: strategy?.charAt(0).toUpperCase() + strategy?.slice(1),
      pillColor: 'bg-[hsl(25,35%,90%)] text-[hsl(25,35%,30%)]',
    },
  ].filter(Boolean);

  return (
    <div className="bg-card rounded-2xl shadow-warm border border-[hsl(35,20%,88%)] overflow-hidden">
      <div className="px-8 py-6 border-b border-[hsl(35,20%,90%)]">
        <p className="text-[11px] font-medium text-[hsl(25,15%,52%)] uppercase tracking-[0.12em] mb-1">Reasoning Trace</p>
        <h2 className="font-serif text-[hsl(25,40%,18%)] text-xl">How this price was calculated</h2>
        <p className="text-[12px] text-[hsl(25,15%,55%)] mt-1">Key signals used to arrive at ${recommended_price?.toFixed(2)}</p>
      </div>

      <div className="p-8 space-y-8">
        {/* ── Tavily query ── */}
        {trace_tavily_query && (
          <div className="rounded-xl border border-[hsl(35,20%,86%)] bg-[hsl(38,25%,97%)] p-4 flex items-start gap-3">
            <Search className="h-3.5 w-3.5 text-[hsl(25,35%,40%)] mt-0.5 flex-shrink-0" />
            <div>
              <p className="text-[10px] font-medium text-[hsl(25,15%,52%)] uppercase tracking-[0.1em] mb-1">Tavily Search Query</p>
              <p className="text-[13px] text-[hsl(25,25%,25%)] italic">"{trace_tavily_query}"</p>
              {trace_prices_found != null && (
                <p className="text-[11px] text-[hsl(25,15%,55%)] mt-1">{trace_prices_found} price{trace_prices_found !== 1 ? 's' : ''} found — {trace_filtered_count ?? 0} kept after filtering</p>
              )}
            </div>
          </div>
        )}

        {/* ── Sanity / fallback warnings ── */}
        {(trace_used_fallback || analysis.sanity_triggered) && (
          <div className="space-y-2">
            {trace_used_fallback && (
              <div className="rounded-xl border border-[hsl(38,50%,82%)] bg-[hsl(38,55%,93%)] p-4 flex items-start gap-2.5">
                <AlertCircle className="h-4 w-4 text-[hsl(38,50%,38%)] flex-shrink-0 mt-0.5" />
                <p className="text-[12px] text-[hsl(38,45%,30%)] leading-relaxed">
                  Market data was limited. This recommendation relies primarily on your cost-plus baseline rather than competitor pricing.
                </p>
              </div>
            )}
            {analysis.sanity_triggered && (
              <div className="rounded-xl border border-[hsl(4,50%,80%)] bg-[hsl(4,55%,95%)] p-4 flex items-start gap-2.5">
                <AlertCircle className="h-4 w-4 text-[hsl(4,55%,48%)] flex-shrink-0 mt-0.5" />
                <p className="text-[12px] text-[hsl(4,45%,30%)] leading-relaxed">
                  Recommendation adjusted conservatively due to inconsistent market evidence — final price kept closer to baseline.
                </p>
              </div>
            )}
          </div>
        )}

        {/* ── Pricing Basis indicator ── */}
        <div className="rounded-xl border border-[hsl(35,20%,86%)] bg-[hsl(38,25%,98%)] p-4 flex items-center justify-between gap-4">
          <div>
            <p className="text-[10px] font-medium text-[hsl(25,15%,52%)] uppercase tracking-[0.1em] mb-0.5">Pricing Basis</p>
            <p className="text-[12px] text-[hsl(25,25%,30%)] leading-snug">
              {pricingBasisDisplay === 'Market-driven'
                ? `${validPrices} comparable prices — recommendation primarily market-derived.`
                : pricingBasisDisplay === 'Market-aligned'
                ? `${validPrices} comparable prices — market data blended with cost baseline.`
                : `Fewer than 5 comparable prices — recommendation driven by cost-plus baseline.`}
            </p>
          </div>
          <span className={`flex-shrink-0 text-[11px] font-semibold px-3 py-1.5 rounded-lg ${basisColor}`}>
            {pricingBasisDisplay}
          </span>
        </div>

        {/* ── Numeric breakdown table ── */}
        <div>
          <p className="text-[11px] font-medium text-[hsl(25,15%,52%)] uppercase tracking-[0.1em] mb-3">Pricing Breakdown</p>
          <div className="rounded-xl border border-[hsl(35,20%,86%)] bg-[hsl(38,25%,98%)] px-5 py-1">
            <DataRow label="Baseline price" value={`$${baseline_price?.toFixed(2)}`} note="cost ÷ (1 − margin%)" />
            {!trace_used_fallback && trace_filtered_low && trace_filtered_high ? (
              <DataRow
                label="Filtered US comparable range (USD)"
                value={`$${trace_filtered_low?.toFixed(2)} – $${trace_filtered_high?.toFixed(2)}`}
                note={trace_competitor_avg_used ? `avg $${trace_competitor_avg_used?.toFixed(2)} · ${validPrices} prices · ${cvLabel || ''}` : `${validPrices} prices · ${cvLabel || ''} · no avg (near-baseline)`}
              />
            ) : (
              <DataRow label="Competitor data" value="Limited comparable pricing data" note={`${validPrices} price${validPrices !== 1 ? 's' : ''} found — below threshold`} />
            )}
            {rejected > 0 && (
              <DataRow label="Prices rejected" value={`${rejected}`} note="Outliers removed for accuracy" />
            )}
            <DataRow label="Price variance" value={cvLabel || '—'} note={price_variance != null ? `CV = ${(price_variance * 100).toFixed(0)}%` : undefined} />
            <DataRow label="Demand level" value={demandLabels[demand] || demand} />
            <DataRow label="Market trend" value={trend.label} />
            <DataRow label="Strategy" value={strategy?.charAt(0).toUpperCase() + strategy?.slice(1)} />
            <DataRow
              label="Confidence"
              value={`${confidenceLabel} (${confidence_score})`}
              note={confidence_explanation || `Based on ${validPrices} comparable price${validPrices !== 1 ? 's' : ''} and signal strength`}
            />
            <DataRow label="Final recommended price" value={`$${recommended_price?.toFixed(2)}`} highlight />
          </div>
        </div>

        {/* ── Step-by-step reasoning ── */}
        <div>
          <p className="text-[11px] font-medium text-[hsl(25,15%,52%)] uppercase tracking-[0.1em] mb-4">Step-by-Step Reasoning</p>
          <div className="space-y-0">
            {steps.map((step, i) => (
              <TraceStep key={i} stepNum={i + 1} done {...step} />
            ))}
          </div>
        </div>

      </div>
    </div>
  );
}