import React, { useEffect, useMemo, useState } from 'react';
import { listAnalyses } from '@/api/analyses';
import { useQuery } from '@tanstack/react-query';
import { DollarSign, BarChart2, TrendingUp, Zap, ArrowRight, Plus, Radio, TrendingDown, Minus, Activity, Brain, SlidersHorizontal } from 'lucide-react';
import { Link } from 'react-router-dom';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, PieChart, Pie, Legend } from 'recharts';
import PriceDistributionChart from '@/components/dashboard/PriceDistributionChart';
import RecentAnalysesList from '@/components/dashboard/RecentAnalysesList';
import {
  ALL_CATEGORIES,
  analysesCountLabel,
  categoryLabel,
  dashboardSummary,
  distinctRecentProducts,
  dominantDemandLevel,
  dominantMarketTrend,
  filterAnalysesByCategory,
  marketSummaryTitle,
  uniqueCategories,
} from '@/lib/dashboard-metrics';

const demandOrder = ['very_low', 'low', 'moderate', 'high', 'very_high'];
const demandLabel = { very_low: 'Very Low', low: 'Low', moderate: 'Moderate', high: 'High', very_high: 'Very High' };
const strategyColors = { aggressive: 'hsl(25,45%,40%)', balanced: 'hsl(38,55%,52%)', premium: 'hsl(25,30%,28%)' };
const barColors = ['hsl(25,40%,30%)', 'hsl(35,50%,48%)', 'hsl(25,35%,42%)', 'hsl(38,55%,55%)', 'hsl(20,30%,50%)', 'hsl(30,45%,38%)'];

const trendConfig = {
  surging:  { icon: Activity,     color: 'text-[hsl(150,42%,36%)]', bg: 'bg-[hsl(150,35%,92%)]', label: 'Surging' },
  growing:  { icon: TrendingUp,   color: 'text-[hsl(140,38%,40%)]', bg: 'bg-[hsl(140,30%,93%)]', label: 'Rising' },
  stable:   { icon: Minus,        color: 'text-[hsl(38,45%,42%)]',  bg: 'bg-[hsl(38,45%,93%)]',  label: 'Stable' },
  declining:{ icon: TrendingDown, color: 'text-[hsl(4,55%,48%)]',   bg: 'bg-[hsl(4,55%,95%)]',   label: 'Declining' },
};

const demandColors = {
  very_high: 'text-[hsl(150,42%,36%)] bg-[hsl(150,35%,92%)]',
  high:      'text-[hsl(140,38%,40%)] bg-[hsl(140,30%,93%)]',
  moderate:  'text-[hsl(38,45%,42%)] bg-[hsl(38,45%,93%)]',
  low:       'text-[hsl(25,55%,42%)] bg-[hsl(25,55%,93%)]',
  very_low:  'text-[hsl(4,55%,48%)] bg-[hsl(4,55%,95%)]',
};

const fieldClass = "px-4 py-2.5 rounded-xl border border-[hsl(35,20%,84%)] bg-card text-[13px] text-[hsl(25,25%,18%)] focus:outline-none focus:border-[hsl(25,40%,40%)] focus:ring-2 focus:ring-[hsl(25,40%,40%)]/10 transition-all duration-200";

/**
 * @param {{ active?: boolean; payload?: Array<{ name?: string; value?: number; color?: string }>; label?: string }} props
 */
const ChartTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-[hsl(36,40%,97%)] border border-[hsl(35,18%,84%)] rounded-xl px-3 py-2 shadow-warm-md text-[12px]">
      <p className="text-[hsl(25,15%,52%)] mb-0.5">{label}</p>
      {payload.map((entry, index) => (
        <p key={index} className="font-semibold" style={{ color: entry.color }}>
          {entry.name === 'count' ? entry.value : `$${Number(entry.value).toFixed(2)}`}
        </p>
      ))}
    </div>
  );
};

function KpiCard({ title, value, sub, icon: Icon }) {
  return (
    <div className="bg-card rounded-2xl p-5 shadow-warm border border-[hsl(35,20%,88%)] relative overflow-hidden group hover:shadow-warm-md transition-all duration-300">
      <div className="absolute top-0 right-0 w-20 h-20 rounded-full bg-[hsl(38,50%,88%)] opacity-20 translate-x-6 -translate-y-6 group-hover:opacity-35 transition-opacity" />
      <div className="relative">
        <div className="h-8 w-8 rounded-xl bg-[hsl(38,45%,90%)] border border-[hsl(35,20%,84%)] flex items-center justify-center mb-3">
          <Icon className="h-3.5 w-3.5 text-[hsl(25,40%,30%)]" />
        </div>
        <p className="text-[10px] font-medium text-[hsl(25,15%,52%)] uppercase tracking-[0.12em] mb-1">{title}</p>
        <p className="font-serif text-[hsl(25,40%,14%)] text-2xl leading-none mb-1">{value}</p>
        {sub && <p className="text-[11px] text-[hsl(25,15%,58%)]">{sub}</p>}
      </div>
    </div>
  );
}

function buildRecommendation(analysis) {
  if (!analysis.recommended_price || !analysis.competitor_avg_price) return null;
  const diff = ((analysis.recommended_price - analysis.competitor_avg_price) / analysis.competitor_avg_price) * 100;
  const demand = analysis.demand_signal;
  const highDemand = demand === 'high' || demand === 'very_high';
  const lowDemand  = demand === 'low'  || demand === 'very_low';

  if (diff > 5 && highDemand) {
    return { action: 'hold', text: `Hold at $${analysis.recommended_price.toFixed(2)} — demand is ${demandLabel[demand]?.toLowerCase()} and your price is above market, justified.`, type: 'above' };
  }
  if (diff < -5 && lowDemand) {
    return { action: 'hold', text: `Hold at $${analysis.recommended_price.toFixed(2)} — demand is ${demandLabel[demand]?.toLowerCase()}, pricing below market is the right call.`, type: 'below' };
  }
  if (diff < -5) {
    return { action: 'increase', text: `Increase price by ~${Math.abs(diff).toFixed(0)}% — you're below competitor average ($${analysis.competitor_avg_price.toFixed(2)}) with ${demandLabel[demand]?.toLowerCase()} demand.`, type: 'below' };
  }
  if (diff > 10 && !highDemand) {
    return { action: 'decrease', text: `Lower price by ~${(diff / 2).toFixed(0)}% — currently above competitor average and demand is ${demandLabel[demand]?.toLowerCase()}.`, type: 'above' };
  }
  return { action: 'hold', text: `Aligned with market at $${analysis.recommended_price.toFixed(2)} — competitor avg is $${analysis.competitor_avg_price.toFixed(2)}.`, type: 'aligned' };
}

function marketPositionLabel(diff) {
  if (diff > 5)  return { label: 'Above market',   cls: 'bg-[hsl(38,55%,90%)] text-[hsl(38,50%,32%)]' };
  if (diff < -5) return { label: 'Below market',   cls: 'bg-[hsl(4,55%,93%)] text-[hsl(4,55%,38%)]' };
  return           { label: 'Aligned with market', cls: 'bg-[hsl(140,30%,92%)] text-[hsl(140,40%,32%)]' };
}

export default function Dashboard() {
  const [category, setCategory] = useState(ALL_CATEGORIES);
  const { data: listResponse, isLoading, isError, error } = useQuery({
    queryKey: ['analyses', { limit: 100 }],
    queryFn: () => listAnalyses({ limit: 100, offset: 0 }),
  });

  const analyses = /** @type {import('@/lib/dashboard-metrics').AnalysisSummary[]} */ (listResponse?.items ?? []);
  const categories = useMemo(() => uniqueCategories(analyses), [analyses]);

  useEffect(() => {
    if (category !== ALL_CATEGORIES && !categories.includes(category)) {
      setCategory(ALL_CATEGORIES);
    }
  }, [categories, category]);

  const filteredAnalyses = useMemo(
    () => filterAnalysesByCategory(analyses, category),
    [analyses, category]
  );

  const summary = useMemo(() => dashboardSummary(filteredAnalyses), [filteredAnalyses]);
  const demandAgg = useMemo(() => dominantDemandLevel(filteredAnalyses), [filteredAnalyses]);
  const trendAgg = useMemo(() => dominantMarketTrend(filteredAnalyses), [filteredAnalyses]);
  const recentProducts = useMemo(() => distinctRecentProducts(filteredAnalyses, 6), [filteredAnalyses]);

  const demandChart = useMemo(() => {
    const demandMap = {};
    filteredAnalyses.forEach((analysis) => {
      demandMap[analysis.demand_signal] = (demandMap[analysis.demand_signal] || 0) + 1;
    });
    return demandOrder.filter((key) => demandMap[key]).map((key) => ({ label: demandLabel[key], count: demandMap[key] }));
  }, [filteredAnalyses]);

  const stratChart = useMemo(() => {
    const stratMap = {};
    filteredAnalyses.forEach((analysis) => {
      stratMap[analysis.strategy] = (stratMap[analysis.strategy] || 0) + 1;
    });
    return Object.entries(stratMap).map(([key, value]) => ({
      name: key,
      value,
      fill: strategyColors[key] || 'hsl(38,50%,52%)',
    }));
  }, [filteredAnalyses]);

  const aiRecs = useMemo(() => (
    filteredAnalyses.slice(0, 5).map((analysis) => {
      const rec = buildRecommendation(analysis);
      if (!rec) return null;
      const diff = analysis.competitor_avg_price
        ? ((analysis.recommended_price - analysis.competitor_avg_price) / analysis.competitor_avg_price) * 100
        : 0;
      return { ...rec, id: analysis.id, name: analysis.product_name, price: analysis.recommended_price, diff, confidence: analysis.confidence_score };
    }).filter(Boolean)
  ), [filteredAnalyses]);

  if (isLoading) return (
    <div className="max-w-6xl animate-pulse space-y-6">
      <div className="h-8 w-48 bg-[hsl(38,30%,88%)] rounded-xl" />
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[1, 2, 3, 4].map((i) => <div key={i} className="h-28 bg-[hsl(38,30%,90%)] rounded-2xl" />)}
      </div>
    </div>
  );

  if (isError) {
    return (
      <div className="max-w-6xl animate-fade-up">
        <div className="bg-card rounded-2xl border border-[hsl(4,50%,82%)] shadow-warm p-10 text-center">
          <p className="font-serif text-2xl text-[hsl(25,25%,38%)] mb-2">Could not load dashboard</p>
          <p className="text-[13px] text-[hsl(25,15%,55%)]">
            {error instanceof Error ? error.message : 'Unable to reach the PricePilot backend.'}
          </p>
        </div>
      </div>
    );
  }

  const trendCfg = trendConfig[trendAgg.value] || trendConfig.stable;
  const TrendIcon = trendCfg.icon;
  const empty = analyses.length === 0;
  const filteredEmpty = !empty && filteredAnalyses.length === 0;

  return (
    <div className="max-w-6xl space-y-8 animate-fade-up">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-[10px] font-medium text-[hsl(25,15%,52%)] uppercase tracking-[0.14em] mb-1">Overview</p>
          <h1 className="font-serif text-[hsl(25,40%,14%)] text-3xl">Pricing Intelligence</h1>
          <p className="text-[13px] text-[hsl(25,15%,52%)] mt-1">Product-level pricing history from your analyses</p>
        </div>
        <div className="flex flex-col-reverse sm:flex-row items-stretch sm:items-center gap-3">
          <div className="relative">
            <SlidersHorizontal className="absolute left-3.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-[hsl(25,15%,55%)]" />
            <select
              className={`${fieldClass} pl-9 pr-8 appearance-none cursor-pointer w-full sm:min-w-[200px]`}
              value={category}
              onChange={(event) => setCategory(event.target.value)}
              aria-label="Filter by category"
              disabled={empty}
            >
              <option value={ALL_CATEGORIES}>All Categories</option>
              {categories.map((value) => (
                <option key={value} value={value}>{categoryLabel(value)}</option>
              ))}
            </select>
          </div>
          <Link to="/new-analysis">
            <button className="w-full sm:w-auto flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-[hsl(25,40%,22%)] text-[hsl(38,33%,95%)] text-[13px] font-medium hover:bg-[hsl(25,40%,17%)] transition-colors shadow-warm-sm">
              <Plus className="h-3.5 w-3.5" /> New Analysis
            </button>
          </Link>
        </div>
      </div>

      {empty ? (
        <div className="bg-card rounded-2xl border border-[hsl(35,20%,88%)] shadow-warm p-16 text-center">
          <p className="font-serif text-2xl text-[hsl(25,25%,38%)] mb-2">No analyses yet</p>
          <p className="text-[13px] text-[hsl(25,15%,55%)] mb-6">Generate your first pricing analysis to see intelligence here</p>
          <Link to="/new-analysis">
            <button className="px-5 py-2.5 rounded-xl bg-[hsl(25,40%,22%)] text-[hsl(38,33%,95%)] text-[13px] font-medium hover:bg-[hsl(25,40%,18%)] transition-colors shadow-warm-sm">
              Get Started
            </button>
          </Link>
        </div>
      ) : (
        <>
          <div className="rounded-2xl border border-[hsl(35,22%,82%)] bg-gradient-to-br from-[hsl(35,30%,93%)] to-[hsl(38,40%,96%)] shadow-warm overflow-hidden">
            <div className="px-6 py-4 border-b border-[hsl(35,20%,86%)] flex items-center justify-between gap-3">
              <div className="min-w-0">
                <p className="text-[11px] font-semibold text-[hsl(25,35%,25%)] uppercase tracking-[0.14em] mb-1">Aggregate view</p>
                <h2 className="font-serif text-[hsl(25,40%,16%)] text-xl leading-tight">
                  {marketSummaryTitle(category)}
                </h2>
              </div>
              <span className="text-[10px] text-[hsl(25,15%,55%)] flex items-center gap-1 flex-shrink-0">
                <Radio className="h-3 w-3" /> {analysesCountLabel(filteredAnalyses.length)}
              </span>
            </div>

            {filteredEmpty ? (
              <div className="p-8 text-center">
                <p className="text-[13px] text-[hsl(25,15%,55%)]">No analyses in this category.</p>
              </div>
            ) : (
              <>
                <div className="p-6 grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <div className="bg-card/70 rounded-xl border border-[hsl(35,20%,88%)] p-4">
                    <p className="text-[10px] font-medium text-[hsl(25,15%,55%)] uppercase tracking-[0.1em] mb-2">Market Demand Level</p>
                    {demandAgg.value ? (
                      <>
                        <span className={`inline-block px-3 py-1.5 rounded-lg text-[13px] font-semibold ${demandColors[demandAgg.value]}`}>
                          {demandLabel[demandAgg.value]}
                        </span>
                        <p className="text-[11px] text-[hsl(25,15%,55%)] mt-2">
                          Most common across {analysesCountLabel(demandAgg.total)}
                        </p>
                      </>
                    ) : (
                      <p className="text-[13px] text-[hsl(25,15%,55%)]">No demand data yet</p>
                    )}
                  </div>

                  <div className="bg-card/70 rounded-xl border border-[hsl(35,20%,88%)] p-4">
                    <p className="text-[10px] font-medium text-[hsl(25,15%,55%)] uppercase tracking-[0.1em] mb-2">Market Trend</p>
                    {trendAgg.value ? (
                      <>
                        <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg ${trendCfg.bg}`}>
                          <TrendIcon className={`h-4 w-4 ${trendCfg.color}`} />
                          <span className={`text-[13px] font-semibold ${trendCfg.color}`}>{trendCfg.label}</span>
                        </div>
                        <p className="text-[11px] text-[hsl(25,15%,55%)] mt-2">
                          Based on {analysesCountLabel(trendAgg.total)}
                        </p>
                      </>
                    ) : (
                      <p className="text-[13px] text-[hsl(25,15%,55%)]">No trend data yet</p>
                    )}
                  </div>

                  <div className="bg-card/70 rounded-xl border border-[hsl(35,20%,88%)] p-4">
                    <p className="text-[10px] font-medium text-[hsl(25,15%,55%)] uppercase tracking-[0.1em] mb-2">Reliable Market Data</p>
                    {summary.reliablePercent != null ? (
                      <>
                        <p className="font-serif text-[hsl(25,40%,14%)] text-xl leading-none">{summary.reliablePercent}%</p>
                        <p className="text-[11px] text-[hsl(25,15%,55%)] mt-2">
                          {summary.reliableCount} of {analysesCountLabel(summary.total)}
                        </p>
                      </>
                    ) : (
                      <p className="text-[13px] text-[hsl(25,15%,55%)]">No data yet</p>
                    )}
                  </div>
                </div>

                <div className="px-6 pb-5">
                  <p className="text-[10px] text-[hsl(25,15%,55%)] uppercase tracking-[0.1em] mb-2.5 font-medium">Products Analyzed</p>
                  {recentProducts.names.length === 0 ? (
                    <p className="text-[13px] text-[hsl(25,15%,55%)]">No products in this view</p>
                  ) : (
                    <div className="flex flex-wrap gap-2">
                      {recentProducts.names.map((name) => (
                        <span
                          key={name}
                          title={name}
                          className="text-[11px] px-2.5 py-1 rounded-lg bg-card/80 border border-[hsl(35,20%,86%)] text-[hsl(25,25%,35%)] truncate max-w-[220px]"
                        >
                          {name}
                        </span>
                      ))}
                      {recentProducts.extraCount > 0 && (
                        <span className="text-[11px] px-2.5 py-1 rounded-lg bg-[hsl(38,35%,90%)] border border-[hsl(35,20%,84%)] text-[hsl(25,25%,38%)]">
                          +{recentProducts.extraCount} more
                        </span>
                      )}
                    </div>
                  )}
                </div>
              </>
            )}
          </div>

          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <KpiCard title="Total Analyses" value={String(summary.total)} sub={category === ALL_CATEGORIES ? 'Your pricing history' : categoryLabel(category)} icon={BarChart2} />
            <KpiCard title="Avg Recommended" value={summary.avgRecommended != null ? `$${summary.avgRecommended.toFixed(2)}` : '—'} sub="AI-set price" icon={DollarSign} />
            <KpiCard title="Avg Confidence" value={summary.avgConfidence != null ? `${summary.avgConfidence}%` : '—'} sub="Signal strength" icon={Zap} />
            <KpiCard
              title="Reliable Market Data"
              value={summary.reliablePercent != null ? `${summary.reliablePercent}%` : '—'}
              sub={`${summary.reliableCount} of ${summary.total} with strong comps`}
              icon={TrendingUp}
            />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <PriceDistributionChart analyses={filteredAnalyses} />

            <div className="bg-card rounded-2xl shadow-warm border border-[hsl(35,20%,88%)] p-6">
              <p className="text-[10px] font-medium text-[hsl(25,15%,52%)] uppercase tracking-[0.12em] mb-1">Strategy Mix</p>
              <h3 className="font-serif text-[hsl(25,40%,18%)] mb-4">Distribution</h3>
              <div className="h-40">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={stratChart} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={60} innerRadius={32} paddingAngle={3}>
                      {stratChart.map((entry, index) => <Cell key={index} fill={entry.fill} />)}
                    </Pie>
                    <Tooltip content={({ active, payload }) => active && payload?.length ? (
                      <div className="bg-[hsl(36,40%,97%)] border border-[hsl(35,18%,84%)] rounded-xl px-3 py-2 shadow-warm-md text-[12px]">
                        <p className="font-semibold text-[hsl(25,40%,18%)] capitalize">{payload[0].name}</p>
                        <p className="text-[hsl(25,15%,52%)]">{payload[0].value} {payload[0].value === 1 ? 'analysis' : 'analyses'}</p>
                      </div>
                    ) : null} />
                    <Legend wrapperStyle={{ fontSize: 11, fontFamily: 'DM Sans', textTransform: 'capitalize' }} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          {demandChart.length > 0 && (
            <div className="bg-card rounded-2xl shadow-warm border border-[hsl(35,20%,88%)] p-6">
              <p className="text-[10px] font-medium text-[hsl(25,15%,52%)] uppercase tracking-[0.12em] mb-1">Demand Signals</p>
              <h3 className="font-serif text-[hsl(25,40%,18%)] mb-5">Demand Distribution Across Products</h3>
              <div className="h-44">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={demandChart} barSize={36} margin={{ top: 4, right: 8, left: -10, bottom: 0 }}>
                    <XAxis dataKey="label" tick={{ fontSize: 11, fill: 'hsl(25,15%,52%)', fontFamily: 'DM Sans' }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fontSize: 10, fill: 'hsl(25,15%,52%)', fontFamily: 'DM Sans' }} axisLine={false} tickLine={false} allowDecimals={false} />
                    <Tooltip content={ChartTooltip} cursor={{ fill: 'hsl(38,35%,92%)', radius: 6 }} />
                    <Bar dataKey="count" name="count" radius={[6, 6, 0, 0]}>
                      {demandChart.map((_, index) => <Cell key={index} fill={barColors[index % barColors.length]} />)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          <RecentAnalysesList analyses={filteredAnalyses} />

          <div className="bg-card rounded-2xl shadow-warm border border-[hsl(35,20%,88%)] overflow-hidden">
            <div className="px-6 py-5 border-b border-[hsl(35,20%,90%)] flex items-center justify-between">
              <div className="flex items-start gap-3">
                <div className="h-8 w-8 rounded-xl bg-[hsl(25,40%,22%)] flex items-center justify-center mt-0.5 flex-shrink-0">
                  <Brain className="h-3.5 w-3.5 text-[hsl(38,33%,92%)]" />
                </div>
                <div>
                  <p className="text-[10px] font-medium text-[hsl(25,15%,52%)] uppercase tracking-[0.12em] mb-0.5">AI Action Center</p>
                  <h3 className="font-serif text-[hsl(25,40%,18%)]">What Should You Do Now?</h3>
                </div>
              </div>
              <Link to="/history" className="text-[12px] text-[hsl(25,15%,52%)] hover:text-[hsl(25,40%,22%)] flex items-center gap-1 transition-colors group">
                All analyses <ArrowRight className="h-3 w-3 group-hover:translate-x-0.5 transition-transform" />
              </Link>
            </div>

            <div className="divide-y divide-[hsl(35,20%,92%)]">
              {aiRecs.length === 0 && (
                <div className="px-6 py-8 text-center">
                  <p className="text-[13px] text-[hsl(25,15%,55%)]">Need competitor data to generate AI recommendations. Run a new analysis.</p>
                </div>
              )}
              {aiRecs.map((rec) => {
                const pos = marketPositionLabel(rec.diff);
                const actionColor = rec.action === 'increase'
                  ? 'text-[hsl(140,40%,36%)]'
                  : rec.action === 'decrease'
                  ? 'text-[hsl(4,55%,46%)]'
                  : 'text-[hsl(38,45%,38%)]';
                const actionIcon = rec.action === 'increase' ? '↑' : rec.action === 'decrease' ? '↓' : '→';
                return (
                  <Link key={rec.id} to={`/results/${rec.id}`}>
                    <div className="flex items-start justify-between px-6 py-4 hover:bg-[hsl(38,30%,95%)] transition-colors group cursor-pointer gap-4">
                      <div className="flex items-start gap-3.5 min-w-0">
                        <div className={`h-7 w-7 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5 text-[15px] font-bold ${actionColor}`}>
                          {actionIcon}
                        </div>
                        <div className="min-w-0">
                          <p className="text-[12px] font-semibold text-[hsl(25,30%,22%)] mb-0.5">{rec.name}</p>
                          <p className="text-[13px] text-[hsl(25,25%,28%)] leading-snug">{rec.text}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        <span className={`text-[10px] font-medium px-2 py-0.5 rounded-md whitespace-nowrap ${pos.cls}`}>
                          {pos.label}
                        </span>
                        <span className="text-[13px] font-semibold text-[hsl(25,40%,20%)] tabular-nums">${rec.price?.toFixed(2)}</span>
                        <ArrowRight className="h-3.5 w-3.5 text-[hsl(25,15%,60%)] opacity-0 group-hover:opacity-100 transition-opacity" />
                      </div>
                    </div>
                  </Link>
                );
              })}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
