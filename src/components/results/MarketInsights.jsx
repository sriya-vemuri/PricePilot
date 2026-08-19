import React from 'react';
import { TrendingUp, TrendingDown, Minus, Activity } from 'lucide-react';

const trendConfig = {
  declining: { icon: TrendingDown, color: 'text-[hsl(4,55%,48%)]', bg: 'bg-[hsl(4,55%,95%)]', label: 'Declining' },
  stable: { icon: Minus, color: 'text-[hsl(38,45%,42%)]', bg: 'bg-[hsl(38,45%,93%)]', label: 'Stable' },
  growing: { icon: TrendingUp, color: 'text-[hsl(140,38%,40%)]', bg: 'bg-[hsl(140,30%,93%)]', label: 'Growing' },
  surging: { icon: Activity, color: 'text-[hsl(150,42%,36%)]', bg: 'bg-[hsl(150,35%,92%)]', label: 'Surging' },
};

const demandConfig = {
  very_low: { width: '10%', label: 'Very Low', color: 'bg-[hsl(4,55%,58%)]' },
  low: { width: '25%', label: 'Low', color: 'bg-[hsl(25,55%,55%)]' },
  moderate: { width: '50%', label: 'Moderate', color: 'bg-[hsl(38,55%,52%)]' },
  high: { width: '75%', label: 'High', color: 'bg-[hsl(140,38%,48%)]' },
  very_high: { width: '95%', label: 'Very High', color: 'bg-[hsl(150,42%,40%)]' },
};

/**
 * Split backend summaries like "Pricing: ... | Trend: ... | Demand: ..."
 * into labeled sections for display. Unlabeled paragraphs stay as a single block.
 *
 * @param {unknown} raw
 * @returns {{ label: string | null; body: string }[]}
 */
function parseMarketSummary(raw) {
  const text = typeof raw === 'string' ? raw.trim() : '';
  if (!text) return [];

  const parts = text.includes('|')
    ? text.split('|').map((part) => part.trim()).filter(Boolean)
    : text.split(/(?=\b(?:Pricing|Trend|Demand)\s*:)/i).map((part) => part.trim()).filter(Boolean);

  return parts.map((part) => {
    const labeled = part.match(/^([A-Za-z][A-Za-z0-9 /&-]{0,24}):\s*([\s\S]*)$/);
    if (labeled && labeled[2].trim()) {
      return { label: labeled[1].trim(), body: labeled[2].trim() };
    }
    return { label: null, body: part };
  }).filter((segment) => segment.body);
}

export default function MarketInsights({ marketData }) {
  if (!marketData) return null;

  const trend = trendConfig[marketData.market_trend] || trendConfig.stable;
  const TrendIcon = trend.icon;
  const demand = demandConfig[marketData.demand_level] || demandConfig.moderate;
  const competitors = [
    marketData.competitor_price_1,
    marketData.competitor_price_2,
    marketData.competitor_price_3,
  ].filter(Boolean);
  const summarySegments = parseMarketSummary(marketData.summary);
  const summaryContext = summarySegments.filter(
    (segment) => !segment.label || !/^(trend|demand)$/i.test(segment.label),
  );
  const summarySignals = summarySegments.filter(
    (segment) => segment.label && /^(trend|demand)$/i.test(segment.label),
  );

  return (
    <div className="bg-card rounded-2xl shadow-warm border border-[hsl(35,20%,88%)] overflow-hidden">
      <div className="px-8 py-6 border-b border-[hsl(35,20%,90%)]">
        <p className="text-[11px] font-medium text-[hsl(25,15%,52%)] uppercase tracking-[0.12em] mb-1">External Intelligence</p>
        <h2 className="font-serif text-[hsl(25,40%,18%)] text-xl">Market Insights</h2>
      </div>

      <div className="p-8 space-y-8">
        {summarySegments.length > 0 ? (
          <div>
            <p className="text-[11px] font-medium text-[hsl(25,20%,48%)] uppercase tracking-[0.1em] mb-3">Market Summary</p>
            <div className="space-y-3">
              {summaryContext.map((segment, i) => (
                <div
                  key={`${segment.label ?? 'summary'}-${i}`}
                  className="rounded-xl bg-[hsl(38,35%,93%)] border border-[hsl(35,20%,87%)] p-4"
                >
                  {segment.label ? (
                    <p className="text-[10px] font-medium text-[hsl(25,15%,52%)] uppercase tracking-[0.1em] mb-2">
                      {segment.label}
                    </p>
                  ) : null}
                  <p className="text-[13px] text-[hsl(25,25%,22%)] leading-relaxed">{segment.body}</p>
                </div>
              ))}
              {summarySignals.length > 0 ? (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {summarySignals.map((segment, i) => (
                    <div
                      key={`${segment.label}-${i}`}
                      className="rounded-xl bg-[hsl(38,35%,93%)] border border-[hsl(35,20%,87%)] p-4"
                    >
                      <p className="text-[10px] font-medium text-[hsl(25,15%,52%)] uppercase tracking-[0.1em] mb-2">
                        {segment.label}
                      </p>
                      <p className="text-[13px] text-[hsl(25,25%,22%)] leading-relaxed">{segment.body}</p>
                    </div>
                  ))}
                </div>
              ) : null}
            </div>
          </div>
        ) : null}

        {summarySegments.length > 0 ? <div className="h-px bg-[hsl(35,20%,90%)]" /> : null}

        {/* Trend + Demand */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <p className="text-[11px] font-medium text-[hsl(25,20%,48%)] uppercase tracking-[0.1em] mb-3">Market Trend</p>
            <div className={`inline-flex items-center gap-2.5 px-4 py-2.5 rounded-xl ${trend.bg}`}>
              <TrendIcon className={`h-4 w-4 ${trend.color}`} />
              <span className={`text-[13px] font-semibold ${trend.color}`}>{trend.label}</span>
            </div>
          </div>

          <div>
            <p className="text-[11px] font-medium text-[hsl(25,20%,48%)] uppercase tracking-[0.1em] mb-3">Demand Level</p>
            <p className="text-[13px] font-medium text-[hsl(25,25%,25%)] mb-2">{demand.label}</p>
            <div className="h-2 bg-[hsl(35,20%,86%)] rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full ${demand.color} transition-all duration-1000`}
                style={{ width: demand.width }}
              />
            </div>
          </div>
        </div>

        <div className="h-px bg-[hsl(35,20%,90%)]" />

        {/* Competitor prices */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <p className="text-[11px] font-medium text-[hsl(25,20%,48%)] uppercase tracking-[0.1em]">Competitor Prices (US Retail, USD)</p>
            {marketData.outliers_removed > 0 && (
              <span className="text-[10px] px-2.5 py-1 rounded-lg bg-[hsl(38,55%,90%)] text-[hsl(38,50%,32%)] font-medium">
                {marketData.outliers_removed} outlier{marketData.outliers_removed > 1 ? 's' : ''} removed
              </span>
            )}
          </div>

          {competitors.length >= 3 ? (
            <>
              <div className="grid grid-cols-3 gap-3">
                {competitors.map((price, i) => (
                  <div key={i} className="rounded-xl bg-[hsl(38,35%,93%)] border border-[hsl(35,20%,87%)] p-4 text-center">
                    <p className="text-[10px] text-[hsl(25,15%,55%)] uppercase tracking-wider mb-1.5">
                      {i === 0 ? 'Low' : i === 1 ? 'Mid' : 'High'}
                    </p>
                    <p className="font-serif text-[hsl(25,40%,20%)] text-xl">${price?.toFixed(2)}</p>
                  </div>
                ))}
              </div>
              <p className="text-[10px] text-[hsl(25,15%,58%)] mt-2.5">
                Filtered US comparable price range · {marketData.raw_prices_found ?? 0} USD prices found · {competitors.length} kept
              </p>
            </>
          ) : (
            <div className="rounded-xl border border-[hsl(38,50%,82%)] bg-[hsl(38,55%,93%)] p-4">
              <p className="text-[13px] text-[hsl(38,45%,30%)] font-medium mb-1">Limited reliable US pricing data found</p>
              <p className="text-[12px] text-[hsl(38,40%,38%)]">Recommendation is baseline-driven. Only {marketData.filtered_prices_count ?? 0} clean USD price{marketData.filtered_prices_count !== 1 ? 's' : ''} could be verified from US retail sources.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}