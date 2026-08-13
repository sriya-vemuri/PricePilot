import React from 'react';
import { ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { format } from 'date-fns';

const demandDot = {
  very_low: 'bg-[hsl(4,55%,60%)]',
  low: 'bg-[hsl(25,65%,58%)]',
  moderate: 'bg-[hsl(38,65%,58%)]',
  high: 'bg-[hsl(140,40%,50%)]',
  very_high: 'bg-[hsl(150,45%,42%)]',
};

const strategyLabel = {
  aggressive: { text: 'Aggressive', cls: 'bg-[hsl(25,45%,90%)] text-[hsl(25,45%,32%)]' },
  balanced: { text: 'Balanced', cls: 'bg-[hsl(38,45%,88%)] text-[hsl(35,40%,30%)]' },
  premium: { text: 'Premium', cls: 'bg-[hsl(25,30%,86%)] text-[hsl(25,35%,28%)]' },
};

export default function RecentAnalysesList({ analyses }) {
  if (!analyses || analyses.length === 0) {
    return (
      <div className="bg-card rounded-2xl p-10 text-center shadow-warm border border-[hsl(35,20%,88%)]">
        <p className="font-serif text-xl text-[hsl(25,25%,40%)] mb-2">No analyses yet</p>
        <p className="text-[13px] text-[hsl(25,15%,55%)] mb-5">Generate your first pricing intelligence report</p>
        <Link to="/new-analysis">
          <button className="px-5 py-2.5 rounded-xl bg-[hsl(25,40%,22%)] text-[hsl(38,33%,95%)] text-[13px] font-medium hover:bg-[hsl(25,40%,18%)] transition-colors duration-200 shadow-warm-sm">
            New Analysis
          </button>
        </Link>
      </div>
    );
  }

  return (
    <div className="bg-card rounded-2xl shadow-warm border border-[hsl(35,20%,88%)] overflow-hidden">
      <div className="px-6 py-5 border-b border-[hsl(35,20%,90%)] flex items-center justify-between">
        <h2 className="font-serif text-[hsl(25,40%,18%)] text-base">Recent Analyses</h2>
        <Link to="/history" className="text-[12px] text-[hsl(25,15%,52%)] hover:text-[hsl(25,40%,22%)] flex items-center gap-1 transition-colors duration-200 group">
          View all
          <ArrowRight className="h-3 w-3 group-hover:translate-x-0.5 transition-transform duration-200" />
        </Link>
      </div>

      <div className="divide-y divide-[hsl(35,20%,92%)]">
        {analyses.slice(0, 6).map((a) => {
          const strat = strategyLabel[a.strategy] || strategyLabel.balanced;
          return (
            <Link key={a.id} to={`/results/${a.id}`}>
              <div className="flex items-center justify-between px-6 py-4 hover:bg-[hsl(38,30%,95%)] transition-colors duration-200 group cursor-pointer">
                <div className="flex items-center gap-3.5">
                  <div className="h-9 w-9 rounded-xl bg-[hsl(38,40%,90%)] border border-[hsl(35,20%,85%)] flex items-center justify-center flex-shrink-0">
                    <span className="text-[13px] font-semibold text-[hsl(25,40%,28%)]">
                      {(a.product_name || 'P')[0].toUpperCase()}
                    </span>
                  </div>
                  <div>
                    <p className="text-[13px] font-medium text-[hsl(25,25%,18%)] group-hover:text-[hsl(25,40%,22%)] transition-colors">
                      {a.product_name || 'Product'}
                    </p>
                    <p className="text-[11px] text-[hsl(25,15%,55%)] mt-0.5">
                      {a.created_date ? format(new Date(a.created_date), 'MMM d, yyyy') : ''}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <span className={`px-2.5 py-1 rounded-lg text-[11px] font-medium ${strat.cls}`}>
                    {strat.text}
                  </span>
                  {a.demand_signal && (
                    <div className="flex items-center gap-1.5">
                      <span className={`h-1.5 w-1.5 rounded-full ${demandDot[a.demand_signal] || 'bg-[hsl(38,50%,60%)]'}`} />
                    </div>
                  )}
                  <span className="text-[14px] font-semibold text-[hsl(25,40%,20%)] tabular-nums min-w-[60px] text-right">
                    ${a.recommended_price?.toFixed(2)}
                  </span>
                  <ArrowRight className="h-3.5 w-3.5 text-[hsl(25,15%,60%)] opacity-0 group-hover:opacity-100 group-hover:translate-x-0.5 transition-all duration-200" />
                </div>
              </div>
            </Link>
          );
        })}
      </div>
    </div>
  );
}