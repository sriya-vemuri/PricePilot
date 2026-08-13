import React from 'react';
import { listAnalyses } from '@/api/analyses';
import { useQuery } from '@tanstack/react-query';
import { DollarSign, BarChart2, TrendingUp, Zap, ArrowRight, Plus, Radio, TrendingDown, Minus, Activity, Brain } from 'lucide-react';
import { Link } from 'react-router-dom';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, PieChart, Pie, Legend } from 'recharts';

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

/**
 * @param {{ active?: boolean; payload?: Array<{ name?: string; value?: number; color?: string }>; label?: string }} props
 */
const ChartTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-[hsl(36,40%,97%)] border border-[hsl(35,18%,84%)] rounded-xl px-3 py-2 shadow-warm-md text-[12px]">
      <p className="text-[hsl(25,15%,52%)] mb-0.5">{label}</p>
      {payload.map((p, i) => (
        <p key={i} className="font-semibold" style={{ color: p.color }}>
          {p.name === 'count' ? p.value : `$${Number(p.value).toFixed(2)}`}
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

// Derive an AI-style action recommendation from an analysis record
function buildRecommendation(a) {
  if (!a.recommended_price || !a.competitor_avg_price) return null;
  const diff = ((a.recommended_price - a.competitor_avg_price) / a.competitor_avg_price) * 100;
  const demand = a.demand_signal;
  const highDemand = demand === 'high' || demand === 'very_high';
  const lowDemand  = demand === 'low'  || demand === 'very_low';

  if (diff > 5 && highDemand) {
    return { action: 'hold', text: `Hold at $${a.recommended_price.toFixed(2)} — demand is ${demandLabel[demand]?.toLowerCase()} and your price is above market, justified.`, type: 'above' };
  }
  if (diff < -5 && lowDemand) {
    return { action: 'hold', text: `Hold at $${a.recommended_price.toFixed(2)} — demand is ${demandLabel[demand]?.toLowerCase()}, pricing below market is the right call.`, type: 'below' };
  }
  if (diff < -5) {
    return { action: 'increase', text: `Increase price by ~${Math.abs(diff).toFixed(0)}% — you're below competitor average ($${a.competitor_avg_price.toFixed(2)}) with ${demandLabel[demand]?.toLowerCase()} demand.`, type: 'below' };
  }
  if (diff > 10 && !highDemand) {
    return { action: 'decrease', text: `Lower price by ~${(diff / 2).toFixed(0)}% — currently above competitor average and demand is ${demandLabel[demand]?.toLowerCase()}.`, type: 'above' };
  }
  return { action: 'hold', text: `Aligned with market at $${a.recommended_price.toFixed(2)} — competitor avg is $${a.competitor_avg_price.toFixed(2)}.`, type: 'aligned' };
}

function marketPositionLabel(diff) {
  if (diff > 5)  return { label: 'Above market',   cls: 'bg-[hsl(38,55%,90%)] text-[hsl(38,50%,32%)]' };
  if (diff < -5) return { label: 'Below market',   cls: 'bg-[hsl(4,55%,93%)] text-[hsl(4,55%,38%)]' };
  return           { label: 'Aligned with market', cls: 'bg-[hsl(140,30%,92%)] text-[hsl(140,40%,32%)]' };
}

export default function Dashboard() {
  // Market intel is nested on each analysis summary (market_data).
  // There is no separate market-data list endpoint — derive banner stats from analyses.
  const { data: listResponse, isLoading, isError, error } = useQuery({
    queryKey: ['analyses', { limit: 50 }],
    queryFn: () => listAnalyses({ limit: 50, offset: 0 }),
  });

  const analyses = listResponse?.items ?? [];

  if (isLoading) return (
    <div className="max-w-6xl animate-pulse space-y-6">
      <div className="h-8 w-48 bg-[hsl(38,30%,88%)] rounded-xl" />
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[1,2,3,4].map(i => <div key={i} className="h-28 bg-[hsl(38,30%,90%)] rounded-2xl" />)}
      </div>
    </div>
  );

  if (isError) {
    return (
      <div className="max-w-6xl animate-fade-up">
        <div className="bg-card rounded-2xl border border-[hsl(4,50%,82%)] shadow-warm p-10 text-center">
          <p className="font-serif text-2xl text-[hsl(25,25%,38%)] mb-2">Could not load dashboard</p>
          <p className="text-[13px] text-[hsl(25,15%,55%)]">
            {error?.message || 'Unable to reach the PricePilot backend.'}
          </p>
        </div>
      </div>
    );
  }

  // KPIs
  const avgRecommended = analyses.length ? analyses.reduce((s, a) => s + (a.recommended_price || 0), 0) / analyses.length : null;
  const withComp = analyses.filter(a => a.competitor_avg_price);
  const avgCompetitor = withComp.length ? withComp.reduce((s, a) => s + a.competitor_avg_price, 0) / withComp.length : null;
  const avgConfidence = analyses.length ? Math.round(analyses.reduce((s, a) => s + (a.confidence_score || 0), 0) / analyses.length) : null;
  const topDemand = analyses.length ? (() => {
    const counts = {};
    analyses.forEach(a => { counts[a.demand_signal] = (counts[a.demand_signal] || 0) + 1; });
    return Object.entries(counts).sort((a, b) => b[1] - a[1])[0]?.[0];
  })() : null;

  // Nested market_data on summary items replaces the old separate ExternalMarketData list.
  const marketDataList = analyses.map((a) => a.market_data).filter(Boolean);
  const recentMarketItems = marketDataList.slice(0, 4);

  // Aggregated market trend across recent data
  const trendCounts = {};
  marketDataList.forEach(m => { trendCounts[m.market_trend] = (trendCounts[m.market_trend] || 0) + 1; });
  const dominantTrend = Object.entries(trendCounts).sort((a, b) => b[1] - a[1])[0]?.[0] || 'stable';
  const trendCfg = trendConfig[dominantTrend] || trendConfig.stable;
  const TrendIcon = trendCfg.icon;

  // Competitor price range across nested market summaries
  const allCompPrices = marketDataList.flatMap(m => [m.competitor_price_1, m.competitor_price_2, m.competitor_price_3].filter(Boolean));
  const compMin = allCompPrices.length ? Math.min(...allCompPrices) : null;
  const compMax = allCompPrices.length ? Math.max(...allCompPrices) : null;

  // Chart data
  const categoryMap = {};
  analyses.forEach(a => {
    const cat = (a.category || 'other').replace(/_/g, ' ');
    if (!categoryMap[cat]) categoryMap[cat] = { category: cat, recommended: [], competitor: [] };
    if (a.recommended_price) categoryMap[cat].recommended.push(a.recommended_price);
    if (a.competitor_avg_price) categoryMap[cat].competitor.push(a.competitor_avg_price);
  });
  const priceChart = Object.values(categoryMap).map(d => ({
    category: d.category,
    recommended: d.recommended.length ? Math.round(d.recommended.reduce((s, v) => s + v, 0) / d.recommended.length) : 0,
    competitor: d.competitor.length ? Math.round(d.competitor.reduce((s, v) => s + v, 0) / d.competitor.length) : 0,
  }));

  const demandMap = {};
  analyses.forEach(a => { demandMap[a.demand_signal] = (demandMap[a.demand_signal] || 0) + 1; });
  const demandChart = demandOrder.filter(k => demandMap[k]).map(k => ({ label: demandLabel[k], count: demandMap[k] }));

  const stratMap = {};
  analyses.forEach(a => { stratMap[a.strategy] = (stratMap[a.strategy] || 0) + 1; });
  const stratChart = Object.entries(stratMap).map(([k, v]) => ({ name: k, value: v, fill: strategyColors[k] || 'hsl(38,50%,52%)' }));

  // AI recommendations
  const aiRecs = analyses.slice(0, 5).map(a => {
    const rec = buildRecommendation(a);
    if (!rec) return null;
    const diff = a.competitor_avg_price ? ((a.recommended_price - a.competitor_avg_price) / a.competitor_avg_price) * 100 : 0;
    return { ...rec, id: a.id, name: a.product_name, price: a.recommended_price, diff, confidence: a.confidence_score };
  }).filter(Boolean);

  const empty = analyses.length === 0;

  return (
    <div className="max-w-6xl space-y-8 animate-fade-up">
      {/* Header */}
      <div className="flex items-end justify-between">
        <div>
          <p className="text-[10px] font-medium text-[hsl(25,15%,52%)] uppercase tracking-[0.14em] mb-1">Overview</p>
          <h1 className="font-serif text-[hsl(25,40%,14%)] text-3xl">Pricing Intelligence</h1>
          <p className="text-[13px] text-[hsl(25,15%,52%)] mt-1">AI-powered pricing decisions using real-time market intelligence</p>
        </div>
        <Link to="/new-analysis">
          <button className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-[hsl(25,40%,22%)] text-[hsl(38,33%,95%)] text-[13px] font-medium hover:bg-[hsl(25,40%,17%)] transition-colors shadow-warm-sm">
            <Plus className="h-3.5 w-3.5" /> New Analysis
          </button>
        </Link>
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
          {/* ── MARKET INTELLIGENCE BANNER ── */}
          <div className="rounded-2xl border border-[hsl(35,22%,82%)] bg-gradient-to-br from-[hsl(35,30%,93%)] to-[hsl(38,40%,96%)] shadow-warm overflow-hidden">
            <div className="px-6 py-4 border-b border-[hsl(35,20%,86%)] flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full bg-[hsl(140,40%,48%)] animate-pulse" />
                  <span className="h-2 w-2 rounded-full bg-[hsl(140,40%,48%)] opacity-50" />
                </div>
                <p className="text-[11px] font-semibold text-[hsl(25,35%,25%)] uppercase tracking-[0.14em]">Market Intelligence</p>
              </div>
              <span className="text-[10px] text-[hsl(25,15%,55%)] flex items-center gap-1">
                <Radio className="h-3 w-3" /> Real-time market data
              </span>
            </div>

            <div className="p-6 grid grid-cols-1 sm:grid-cols-3 gap-4">
              {/* Competitor price range */}
              <div className="bg-card/70 rounded-xl border border-[hsl(35,20%,88%)] p-4">
                <p className="text-[10px] font-medium text-[hsl(25,15%,55%)] uppercase tracking-[0.1em] mb-2">Competitor Price Range</p>
                {compMin !== null ? (
                  <>
                    <p className="font-serif text-[hsl(25,40%,14%)] text-xl leading-none">
                      ${compMin.toFixed(2)} — ${compMax.toFixed(2)}
                    </p>
                    <p className="text-[11px] text-[hsl(25,15%,55%)] mt-1.5">
                      Across {allCompPrices.length} data points
                    </p>
                  </>
                ) : (
                  <p className="text-[13px] text-[hsl(25,15%,55%)]">No data yet</p>
                )}
              </div>

              {/* Dominant demand */}
              <div className="bg-card/70 rounded-xl border border-[hsl(35,20%,88%)] p-4">
                <p className="text-[10px] font-medium text-[hsl(25,15%,55%)] uppercase tracking-[0.1em] mb-2">Market Demand Level</p>
                {topDemand ? (
                  <>
                    <span className={`inline-block px-3 py-1.5 rounded-lg text-[13px] font-semibold ${demandColors[topDemand]}`}>
                      {demandLabel[topDemand]}
                    </span>
                    <p className="text-[11px] text-[hsl(25,15%,55%)] mt-2">Most common across products</p>
                  </>
                ) : (
                  <p className="text-[13px] text-[hsl(25,15%,55%)]">No data yet</p>
                )}
              </div>

              {/* Market trend */}
              <div className="bg-card/70 rounded-xl border border-[hsl(35,20%,88%)] p-4">
                <p className="text-[10px] font-medium text-[hsl(25,15%,55%)] uppercase tracking-[0.1em] mb-2">Market Trend</p>
                <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg ${trendCfg.bg}`}>
                  <TrendIcon className={`h-4 w-4 ${trendCfg.color}`} />
                  <span className={`text-[13px] font-semibold ${trendCfg.color}`}>{trendCfg.label}</span>
                </div>
                <p className="text-[11px] text-[hsl(25,15%,55%)] mt-2">
                  {marketDataList.length > 0 ? `Based on ${marketDataList.length} recent searches` : 'Awaiting data'}
                </p>
              </div>
            </div>

            {/* Recent search queries */}
            {recentMarketItems.length > 0 && (
              <div className="px-6 pb-5">
                <p className="text-[10px] text-[hsl(25,15%,55%)] uppercase tracking-[0.1em] mb-2.5 font-medium">Recent Queries</p>
                <div className="flex flex-wrap gap-2">
                  {recentMarketItems.map((m, i) => m.tavily_query && (
                    <span key={i} className="text-[11px] px-2.5 py-1 rounded-lg bg-card/80 border border-[hsl(35,20%,86%)] text-[hsl(25,25%,35%)] truncate max-w-xs">
                      "{m.tavily_query.length > 60 ? m.tavily_query.slice(0, 60) + '…' : m.tavily_query}"
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* KPIs */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <KpiCard title="Avg Recommended" value={avgRecommended ? `$${avgRecommended.toFixed(2)}` : '—'} sub="Your AI-set price" icon={DollarSign} />
            <KpiCard title="Avg Competitor" value={avgCompetitor ? `$${avgCompetitor.toFixed(2)}` : '—'} sub="Market benchmark" icon={BarChart2} />
            <KpiCard title="Dominant Demand" value={topDemand ? demandLabel[topDemand] : '—'} sub="Most common signal" icon={TrendingUp} />
            <KpiCard title="Avg Confidence" value={avgConfidence ? `${avgConfidence}%` : '—'} sub="AI signal strength" icon={Zap} />
          </div>

          {/* Charts row */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 bg-card rounded-2xl shadow-warm border border-[hsl(35,20%,88%)] p-6">
              <p className="text-[10px] font-medium text-[hsl(25,15%,52%)] uppercase tracking-[0.12em] mb-1">Price Intelligence</p>
              <h3 className="font-serif text-[hsl(25,40%,18%)] mb-5">Your Price vs Competitor</h3>
              <div className="h-52">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={priceChart} barSize={20} barGap={4} margin={{ top: 4, right: 8, left: -10, bottom: 0 }}>
                    <XAxis dataKey="category" tick={{ fontSize: 10, fill: 'hsl(25,15%,52%)', fontFamily: 'DM Sans' }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fontSize: 10, fill: 'hsl(25,15%,52%)', fontFamily: 'DM Sans' }} axisLine={false} tickLine={false} tickFormatter={v => `$${v}`} />
                    <Tooltip content={ChartTooltip} cursor={{ fill: 'hsl(38,35%,92%)', radius: 6 }} />
                    <Bar dataKey="recommended" name="Recommended" radius={[4,4,0,0]} fill="hsl(25,40%,28%)" />
                    <Bar dataKey="competitor" name="Competitor Avg" radius={[4,4,0,0]} fill="hsl(38,50%,65%)" />
                    <Legend wrapperStyle={{ fontSize: 11, fontFamily: 'DM Sans', color: 'hsl(25,15%,52%)' }} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="bg-card rounded-2xl shadow-warm border border-[hsl(35,20%,88%)] p-6">
              <p className="text-[10px] font-medium text-[hsl(25,15%,52%)] uppercase tracking-[0.12em] mb-1">Strategy Mix</p>
              <h3 className="font-serif text-[hsl(25,40%,18%)] mb-4">Distribution</h3>
              <div className="h-40">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={stratChart} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={60} innerRadius={32} paddingAngle={3}>
                      {stratChart.map((entry, i) => <Cell key={i} fill={entry.fill} />)}
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

          {/* Demand chart */}
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
                    <Bar dataKey="count" name="count" radius={[6,6,0,0]}>
                      {demandChart.map((_, i) => <Cell key={i} fill={barColors[i % barColors.length]} />)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {/* ── AI RECOMMENDATIONS ── */}
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