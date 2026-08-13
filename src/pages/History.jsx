import React, { useState } from 'react';
import { listAnalyses } from '@/api/analyses';
import { useQuery } from '@tanstack/react-query';
import { Search, ArrowRight, SlidersHorizontal } from 'lucide-react';
import { Link } from 'react-router-dom';
import { format } from 'date-fns';

const demandDot = {
  very_low: 'bg-[hsl(4,55%,60%)]',
  low: 'bg-[hsl(25,65%,58%)]',
  moderate: 'bg-[hsl(38,65%,58%)]',
  high: 'bg-[hsl(140,40%,50%)]',
  very_high: 'bg-[hsl(150,45%,42%)]',
};

const strategyStyle = {
  aggressive: 'bg-[hsl(25,45%,91%)] text-[hsl(25,45%,32%)]',
  balanced: 'bg-[hsl(38,45%,90%)] text-[hsl(35,40%,30%)]',
  premium: 'bg-[hsl(25,30%,88%)] text-[hsl(25,35%,26%)]',
};

const fieldClass = "px-4 py-2.5 rounded-xl border border-[hsl(35,20%,84%)] bg-card text-[13px] text-[hsl(25,25%,18%)] placeholder:text-[hsl(25,15%,62%)] focus:outline-none focus:border-[hsl(25,40%,40%)] focus:ring-2 focus:ring-[hsl(25,40%,40%)]/10 transition-all duration-200";

export default function History() {
  const [search, setSearch] = useState('');
  const [strategyFilter, setStrategyFilter] = useState('all');
  const { data: listResponse, isLoading, isError, error } = useQuery({
    queryKey: ['analyses', { limit: 100 }],
    queryFn: () => listAnalyses({ limit: 100, offset: 0 }),
  });

  const analyses = listResponse?.items ?? [];

  const filtered = analyses.filter((a) => {
    const matchSearch = !search || a.product_name?.toLowerCase().includes(search.toLowerCase());
    const matchStrategy = strategyFilter === 'all' || a.strategy === strategyFilter;
    return matchSearch && matchStrategy;
  });

  return (
    <div className="max-w-5xl mx-auto space-y-8 animate-fade-up">
      {/* Header */}
      <div>
        <p className="text-[11px] font-medium text-[hsl(25,15%,52%)] uppercase tracking-[0.14em] mb-1.5">Archive</p>
        <h1 className="font-serif text-[hsl(25,40%,14%)] text-3xl leading-tight">Analysis History</h1>
        <p className="text-[13px] text-[hsl(25,15%,52%)] mt-2">Browse all past pricing analyses</p>
      </div>

      {/* Filters */}
      <div className="flex gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-[hsl(25,15%,55%)]" />
          <input
            className={`${fieldClass} w-full pl-10`}
            placeholder="Search by product name..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div className="relative">
          <SlidersHorizontal className="absolute left-3.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-[hsl(25,15%,55%)]" />
          <select
            className={`${fieldClass} pl-9 pr-8 appearance-none cursor-pointer`}
            value={strategyFilter}
            onChange={(e) => setStrategyFilter(e.target.value)}
          >
            <option value="all">All Strategies</option>
            <option value="aggressive">Aggressive</option>
            <option value="balanced">Balanced</option>
            <option value="premium">Premium</option>
          </select>
        </div>
      </div>

      {/* List */}
      {isLoading ? (
        <div className="space-y-3 animate-pulse">
          {[1,2,3,4].map(i => (
            <div key={i} className="h-20 bg-[hsl(38,30%,92%)] rounded-2xl" />
          ))}
        </div>
      ) : isError ? (
        <div className="bg-card rounded-2xl border border-[hsl(4,50%,82%)] shadow-warm p-14 text-center">
          <p className="font-serif text-2xl text-[hsl(25,25%,38%)] mb-2">Could not load history</p>
          <p className="text-[13px] text-[hsl(25,15%,55%)]">
            {error?.message || 'Unable to reach the PricePilot backend.'}
          </p>
        </div>
      ) : filtered.length === 0 ? (
        <div className="bg-card rounded-2xl border border-[hsl(35,20%,88%)] shadow-warm p-14 text-center">
          <p className="font-serif text-2xl text-[hsl(25,25%,38%)] mb-2">Nothing here yet</p>
          <p className="text-[13px] text-[hsl(25,15%,55%)] mb-6">Start by creating a pricing analysis</p>
          <Link to="/new-analysis">
            <button className="px-5 py-2.5 rounded-xl bg-[hsl(25,40%,22%)] text-[hsl(38,33%,95%)] text-[13px] font-medium hover:bg-[hsl(25,40%,18%)] transition-colors shadow-warm-sm">
              New Analysis
            </button>
          </Link>
        </div>
      ) : (
        <div className="bg-card rounded-2xl border border-[hsl(35,20%,88%)] shadow-warm overflow-hidden">
          <div className="divide-y divide-[hsl(35,20%,92%)]">
            {filtered.map((a) => {
              const createdAt = a.created_at || a.created_date;
              return (
                <Link key={a.id} to={`/results/${a.id}`}>
                  <div className="flex items-center justify-between px-6 py-5 hover:bg-[hsl(38,30%,95%)] transition-colors duration-200 group cursor-pointer">
                    <div className="flex items-center gap-4">
                      <div className="h-10 w-10 rounded-xl bg-[hsl(38,40%,90%)] border border-[hsl(35,20%,85%)] flex items-center justify-center flex-shrink-0">
                        <span className="text-[13px] font-semibold text-[hsl(25,40%,28%)]">
                          {(a.product_name || 'P')[0].toUpperCase()}
                        </span>
                      </div>
                      <div>
                        <p className="text-[14px] font-medium text-[hsl(25,25%,18%)] group-hover:text-[hsl(25,40%,20%)] transition-colors">
                          {a.product_name}
                        </p>
                        <div className="flex items-center gap-2 mt-0.5">
                          <span className="text-[11px] text-[hsl(25,15%,55%)] capitalize">{a.category?.replace(/_/g, ' ')}</span>
                          <span className="text-[hsl(35,20%,75%)]">·</span>
                          <span className="text-[11px] text-[hsl(25,15%,55%)]">
                            {createdAt ? format(new Date(createdAt), 'MMM d, yyyy') : ''}
                          </span>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-3.5">
                      <span className={`px-2.5 py-1 rounded-lg text-[11px] font-medium ${strategyStyle[a.strategy] || strategyStyle.balanced}`}>
                        {a.strategy?.charAt(0).toUpperCase() + a.strategy?.slice(1)}
                      </span>
                      {a.demand_signal && (
                        <span className={`h-2 w-2 rounded-full ${demandDot[a.demand_signal] || 'bg-[hsl(38,50%,60%)]'}`} />
                      )}
                      <div className="text-right">
                        <p className="text-[14px] font-semibold text-[hsl(25,40%,20%)] tabular-nums">${a.recommended_price?.toFixed(2)}</p>
                        <p className="text-[10px] text-[hsl(25,15%,55%)]">{a.confidence_score}% conf.</p>
                      </div>
                      <ArrowRight className="h-3.5 w-3.5 text-[hsl(25,20%,58%)] opacity-0 group-hover:opacity-100 group-hover:translate-x-0.5 transition-all duration-200" />
                    </div>
                  </div>
                </Link>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
