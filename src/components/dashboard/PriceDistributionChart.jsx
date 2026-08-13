import React from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';

const barColors = [
  'hsl(25, 40%, 30%)',
  'hsl(35, 50%, 48%)',
  'hsl(25, 35%, 42%)',
  'hsl(38, 55%, 55%)',
  'hsl(20, 30%, 50%)',
  'hsl(30, 45%, 38%)',
];

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-[hsl(36,40%,97%)] border border-[hsl(35,18%,84%)] rounded-xl px-4 py-3 shadow-warm-md">
        <p className="text-[11px] text-[hsl(25,15%,52%)] uppercase tracking-wider mb-1">{label}</p>
        <p className="text-[15px] font-semibold text-[hsl(25,40%,18%)]">${payload[0].value}</p>
      </div>
    );
  }
  return null;
};

export default function PriceDistributionChart({ analyses }) {
  if (!analyses || analyses.length === 0) return null;

  const categoryData = {};
  analyses.forEach((a) => {
    const cat = a.category || 'other';
    if (!categoryData[cat]) categoryData[cat] = { category: cat, total: 0, count: 0 };
    categoryData[cat].total += a.recommended_price || 0;
    categoryData[cat].count += 1;
  });

  const chartData = Object.values(categoryData).map((d) => ({
    category: d.category.replace(/_/g, ' '),
    avg_price: Math.round((d.total / d.count) * 100) / 100,
  }));

  return (
    <div className="bg-card rounded-2xl shadow-warm border border-[hsl(35,20%,88%)] overflow-hidden">
      <div className="px-6 py-5 border-b border-[hsl(35,20%,90%)]">
        <h2 className="font-serif text-[hsl(25,40%,18%)] text-base">Avg. Price by Category</h2>
        <p className="text-[12px] text-[hsl(25,15%,55%)] mt-0.5">Recommended price distribution</p>
      </div>

      <div className="px-4 py-4 h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 4, right: 8, left: -10, bottom: 0 }} barSize={28}>
            <XAxis
              dataKey="category"
              tick={{ fontSize: 10, fill: 'hsl(25, 15%, 52%)', fontFamily: 'DM Sans' }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              tick={{ fontSize: 10, fill: 'hsl(25, 15%, 52%)', fontFamily: 'DM Sans' }}
              axisLine={false}
              tickLine={false}
              tickFormatter={(v) => `$${v}`}
            />
            <Tooltip content={<CustomTooltip />} cursor={{ fill: 'hsl(38, 35%, 92%)', radius: 8 }} />
            <Bar dataKey="avg_price" radius={[6, 6, 0, 0]}>
              {chartData.map((entry, index) => (
                <Cell key={index} fill={barColors[index % barColors.length]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}