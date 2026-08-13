import React from 'react';
import { getAnalysisById } from '@/api/analyses';
import { ApiError, formatMarketWarnings } from '@/api/errors';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeft } from 'lucide-react';
import { Link, useParams } from 'react-router-dom';
import PriceGauge from '../components/results/PriceGauge';
import ConfidenceMeter from '../components/results/ConfidenceMeter';
import MarketInsights from '../components/results/MarketInsights';
import ReasoningTrace from '../components/results/ReasoningTrace';
import PricingRationale from '../components/results/PricingRationale';

const strategyStyle = {
  aggressive: 'bg-[hsl(25,45%,91%)] text-[hsl(25,45%,32%)]',
  balanced: 'bg-[hsl(38,45%,90%)] text-[hsl(35,40%,30%)]',
  premium: 'bg-[hsl(25,30%,88%)] text-[hsl(25,35%,26%)]',
};

export default function Results() {
  const { id: analysisId } = useParams();

  const { data: analysis, isLoading, isError, error } = useQuery({
    queryKey: ['analysis', analysisId],
    queryFn: () => getAnalysisById(analysisId),
    enabled: !!analysisId,
    retry: (failureCount, err) => {
      if (err instanceof ApiError && (err.status === 404 || err.error === 'analysis_not_found')) {
        return false;
      }
      return failureCount < 1;
    },
  });

  if (isLoading) {
    return (
      <div className="max-w-5xl mx-auto animate-pulse space-y-6">
        <div className="h-8 w-64 bg-[hsl(38,30%,88%)] rounded-xl" />
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 h-80 bg-[hsl(38,30%,90%)] rounded-2xl" />
          <div className="h-80 bg-[hsl(38,30%,90%)] rounded-2xl" />
        </div>
      </div>
    );
  }

  const notFound =
    !analysis ||
    (isError && error instanceof ApiError && (error.status === 404 || error.error === 'analysis_not_found'));

  if (notFound) {
    return (
      <div className="text-center py-24">
        <p className="font-serif text-2xl text-[hsl(25,25%,40%)] mb-3">Analysis not found</p>
        <p className="text-[13px] text-[hsl(25,15%,55%)] mb-4">
          This analysis does not exist or could not be loaded.
        </p>
        <Link to="/">
          <button className="mt-2 px-5 py-2.5 rounded-xl border border-[hsl(35,20%,82%)] text-[13px] text-[hsl(25,25%,35%)] hover:bg-[hsl(38,30%,93%)] transition-colors">
            Back to Dashboard
          </button>
        </Link>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="text-center py-24">
        <p className="font-serif text-2xl text-[hsl(25,25%,40%)] mb-3">Could not load analysis</p>
        <p className="text-[13px] text-[hsl(25,15%,55%)] mb-4">
          {error?.message || 'Unable to reach the PricePilot backend.'}
        </p>
        <Link to="/">
          <button className="mt-2 px-5 py-2.5 rounded-xl border border-[hsl(35,20%,82%)] text-[13px] text-[hsl(25,25%,35%)] hover:bg-[hsl(38,30%,93%)] transition-colors">
            Back to Dashboard
          </button>
        </Link>
      </div>
    );
  }

  const marketData = analysis.market_data ?? null;
  const warningMessages = formatMarketWarnings(analysis.market_warnings);

  return (
    <div className="max-w-5xl mx-auto animate-fade-up space-y-8">
      {/* Header */}
      <div className="flex items-start gap-4">
        <Link to="/history">
          <button className="mt-1 h-9 w-9 rounded-xl border border-[hsl(35,20%,84%)] bg-card flex items-center justify-center hover:bg-[hsl(38,30%,93%)] transition-all duration-200 shadow-warm-sm flex-shrink-0">
            <ArrowLeft className="h-3.5 w-3.5 text-[hsl(25,25%,35%)]" />
          </button>
        </Link>
        <div className="flex-1 flex items-start justify-between gap-4 flex-wrap">
          <div>
            <p className="text-[11px] font-medium text-[hsl(25,15%,52%)] uppercase tracking-[0.14em] mb-1">Results</p>
            <h1 className="font-serif text-[hsl(25,40%,14%)] text-3xl leading-tight">{analysis.product_name}</h1>
            <div className="flex items-center gap-2.5 mt-2">
              <span className={`px-2.5 py-1 rounded-lg text-[11px] font-medium ${strategyStyle[analysis.strategy] || strategyStyle.balanced}`}>
                {analysis.strategy?.charAt(0).toUpperCase() + analysis.strategy?.slice(1)} Strategy
              </span>
              <span className="text-[12px] text-[hsl(25,15%,52%)] capitalize">
                {analysis.category?.replace(/_/g, ' ')}
              </span>
            </div>
          </div>
        </div>
      </div>

      {warningMessages.length > 0 && (
        <div className="rounded-2xl border border-[hsl(38,50%,82%)] bg-[hsl(38,55%,94%)] p-4 space-y-1.5">
          <p className="text-[11px] font-semibold text-[hsl(38,45%,30%)] uppercase tracking-[0.1em]">Market notes</p>
          {warningMessages.map((msg) => (
            <p key={msg} className="text-[12px] text-[hsl(38,40%,32%)] leading-relaxed">
              {msg}
            </p>
          ))}
        </div>
      )}

      {/* Pricing Rationale — full width, above the numbers */}
      <PricingRationale analysis={analysis} />

      {/* Price + Confidence row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <PriceGauge
            recommended={analysis.recommended_price}
            low={analysis.price_range_low}
            high={analysis.price_range_high}
            baseline={analysis.baseline_price}
            competitorAvg={analysis.competitor_avg_price}
            competitorAvgStatus={analysis.competitor_avg_status}
            pricingMode={analysis.pricing_mode || 'retail'}
          />
        </div>
        <ConfidenceMeter score={analysis.confidence_score} explanation={analysis.confidence_explanation} />
      </div>

      {/* Reasoning trace — nested market_data replaces the old second fetch */}
      <ReasoningTrace analysis={analysis} marketData={marketData} />

      {/* Market insights */}
      <MarketInsights marketData={marketData} />
    </div>
  );
}
