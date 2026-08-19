import React from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { productPricingChartData } from '@/lib/dashboard-metrics';

/**
 * @param {{ active?: boolean; payload?: Array<{ name?: string; value?: number; color?: string; payload?: { product?: string; label?: string } }>; label?: string }} props
 */
function ProductPriceTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const product = payload[0]?.payload?.product || payload[0]?.payload?.label;
  return (
    <div className="bg-[hsl(36,40%,97%)] border border-[hsl(35,18%,84%)] rounded-xl px-3 py-2 shadow-warm-md text-[12px] max-w-[240px]">
      <p className="text-[hsl(25,25%,22%)] font-medium mb-1 truncate" title={product}>{product}</p>
      {payload.map((entry, index) => (
        <p key={index} className="font-semibold tabular-nums" style={{ color: entry.color }}>
          {entry.name}: ${Number(entry.value).toFixed(2)}
        </p>
      ))}
    </div>
  );
}

/**
 * @param {{ analyses?: import('@/lib/dashboard-metrics').AnalysisSummary[] }} props
 */
export default function PriceDistributionChart({ analyses }) {
  const chartData = productPricingChartData(analyses);

  return (
    <div className="lg:col-span-2 bg-card rounded-2xl shadow-warm border border-[hsl(35,20%,88%)] p-6">
      <p className="text-[10px] font-medium text-[hsl(25,15%,52%)] uppercase tracking-[0.12em] mb-1">Price Intelligence</p>
      <h3 className="font-serif text-[hsl(25,40%,18%)] mb-1">Recommended vs Baseline</h3>
      <p className="text-[12px] text-[hsl(25,15%,55%)] mb-5">
        How PricePilot’s recommended price compares with the cost-plus baseline for each product
      </p>
      {chartData.length === 0 ? (
        <div className="h-52 flex items-center justify-center">
          <p className="text-[13px] text-[hsl(25,15%,55%)] text-center px-4">
            No product analyses in this view yet. Run an analysis to compare recommended and baseline prices.
          </p>
        </div>
      ) : (
        <div className="h-52">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} barSize={16} barGap={3} margin={{ top: 4, right: 8, left: -10, bottom: 8 }}>
              <XAxis
                dataKey="label"
                tick={{ fontSize: 10, fill: 'hsl(25,15%,52%)', fontFamily: 'DM Sans' }}
                axisLine={false}
                tickLine={false}
                interval={0}
              />
              <YAxis
                tick={{ fontSize: 10, fill: 'hsl(25,15%,52%)', fontFamily: 'DM Sans' }}
                axisLine={false}
                tickLine={false}
                tickFormatter={(value) => `$${value}`}
              />
              <Tooltip content={<ProductPriceTooltip />} cursor={{ fill: 'hsl(38,35%,92%)', radius: 6 }} />
              <Legend wrapperStyle={{ fontSize: 11, fontFamily: 'DM Sans', color: 'hsl(25,15%,52%)' }} />
              <Bar dataKey="baseline" name="Baseline" radius={[4, 4, 0, 0]} fill="hsl(38,50%,65%)" />
              <Bar dataKey="recommended" name="Recommended" radius={[4, 4, 0, 0]} fill="hsl(25,40%,28%)" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
