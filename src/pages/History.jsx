import React, { useEffect, useMemo, useState } from 'react';
import { deleteAnalysis, listAnalyses } from '@/api/analyses';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowRight, Search, SlidersHorizontal, Trash2 } from 'lucide-react';
import { Link } from 'react-router-dom';
import { format } from 'date-fns';
import {
  ALL_CATEGORIES,
  categoryLabel,
  uniqueCategories,
} from '@/lib/dashboard-metrics';
import { toast } from '@/components/ui/use-toast';

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

const ANALYSES_QUERY_KEY = ['analyses', { limit: 100 }];

export default function History() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [strategyFilter, setStrategyFilter] = useState('all');
  const [categoryFilter, setCategoryFilter] = useState(ALL_CATEGORIES);
  const [pendingDelete, setPendingDelete] = useState(
    /** @type {import('@/lib/dashboard-metrics').AnalysisSummary | null} */ (null),
  );
  const { data: listResponse, isLoading, isError, error } = useQuery({
    queryKey: ANALYSES_QUERY_KEY,
    queryFn: () => listAnalyses({ limit: 100, offset: 0 }),
  });

  const analyses = /** @type {import('@/lib/dashboard-metrics').AnalysisSummary[]} */ (listResponse?.items ?? []);
  const categories = useMemo(() => uniqueCategories(analyses), [analyses]);

  useEffect(() => {
    if (categoryFilter !== ALL_CATEGORIES && !categories.includes(categoryFilter)) {
      setCategoryFilter(ALL_CATEGORIES);
    }
  }, [categories, categoryFilter]);

  const filtered = useMemo(() => {
    const query = search.trim().toLowerCase();
    return analyses.filter((analysis) => {
      const matchSearch = !query || analysis.product_name?.toLowerCase().includes(query);
      const matchStrategy = strategyFilter === 'all' || analysis.strategy === strategyFilter;
      const matchCategory = categoryFilter === ALL_CATEGORIES || analysis.category === categoryFilter;
      return matchSearch && matchStrategy && matchCategory;
    });
  }, [analyses, search, strategyFilter, categoryFilter]);

  const deleteMutation = useMutation({
    mutationFn: (/** @type {string} */ id) => deleteAnalysis(id),
    onSuccess: async () => {
      setPendingDelete(null);
      await queryClient.invalidateQueries({ queryKey: ['analyses'] });
    },
    onError: (err) => {
      toast({
        variant: 'destructive',
        title: 'Could not delete analysis',
        description: err instanceof Error ? err.message : 'Please try again.',
      });
    },
  });

  const deleting = deleteMutation.isPending;

  return (
    <div className="max-w-5xl mx-auto space-y-8 animate-fade-up">
      {/* Header */}
      <div>
        <p className="text-[11px] font-medium text-[hsl(25,15%,52%)] uppercase tracking-[0.14em] mb-1.5">Archive</p>
        <h1 className="font-serif text-[hsl(25,40%,14%)] text-3xl leading-tight">Analysis History</h1>
        <p className="text-[13px] text-[hsl(25,15%,52%)] mt-2">Browse all past pricing analyses</p>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3">
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
            className={`${fieldClass} pl-9 pr-8 appearance-none cursor-pointer w-full sm:min-w-[180px]`}
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            aria-label="Filter by category"
            disabled={analyses.length === 0}
          >
            <option value={ALL_CATEGORIES}>All Categories</option>
            {categories.map((value) => (
              <option key={value} value={value}>{categoryLabel(value)}</option>
            ))}
          </select>
        </div>
        <div className="relative">
          <select
            className={`${fieldClass} pl-4 pr-8 appearance-none cursor-pointer w-full sm:min-w-[160px]`}
            value={strategyFilter}
            onChange={(e) => setStrategyFilter(e.target.value)}
            aria-label="Filter by strategy"
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
            {error instanceof Error ? error.message : 'Unable to reach the PricePilot backend.'}
          </p>
        </div>
      ) : filtered.length === 0 ? (
        <div className="bg-card rounded-2xl border border-[hsl(35,20%,88%)] shadow-warm p-14 text-center">
          <p className="font-serif text-2xl text-[hsl(25,25%,38%)] mb-2">Nothing here yet</p>
          <p className="text-[13px] text-[hsl(25,15%,55%)] mb-6">
            {analyses.length === 0
              ? 'Start by creating a pricing analysis'
              : 'No analyses match these filters'}
          </p>
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
              const createdAt = a.created_at;
              return (
                <div
                  key={a.id}
                  className="flex items-center px-3 sm:px-4 hover:bg-[hsl(38,30%,95%)] transition-colors duration-200 group"
                >
                  <Link to={`/results/${a.id}`} className="flex-1 min-w-0 flex items-center justify-between px-3 py-5 cursor-pointer">
                    <div className="flex items-center gap-4 min-w-0">
                      <div className="h-10 w-10 rounded-xl bg-[hsl(38,40%,90%)] border border-[hsl(35,20%,85%)] flex items-center justify-center flex-shrink-0">
                        <span className="text-[13px] font-semibold text-[hsl(25,40%,28%)]">
                          {(a.product_name || 'P')[0].toUpperCase()}
                        </span>
                      </div>
                      <div className="min-w-0">
                        <p className="text-[14px] font-medium text-[hsl(25,25%,18%)] group-hover:text-[hsl(25,40%,20%)] transition-colors truncate">
                          {a.product_name}
                        </p>
                        <div className="flex items-center gap-2 mt-0.5">
                          <span className="text-[11px] text-[hsl(25,15%,55%)]">{categoryLabel(a.category)}</span>
                          <span className="text-[hsl(35,20%,75%)]">·</span>
                          <span className="text-[11px] text-[hsl(25,15%,55%)]">
                            {createdAt ? format(new Date(createdAt), 'MMM d, yyyy') : ''}
                          </span>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-3.5 flex-shrink-0 ml-3">
                      <span className={`hidden sm:inline px-2.5 py-1 rounded-lg text-[11px] font-medium ${strategyStyle[a.strategy] || strategyStyle.balanced}`}>
                        {a.strategy?.charAt(0).toUpperCase() + a.strategy?.slice(1)}
                      </span>
                      {a.demand_signal && (
                        <span className={`h-2 w-2 rounded-full ${demandDot[a.demand_signal] || 'bg-[hsl(38,50%,60%)]'}`} />
                      )}
                      <div className="text-right">
                        <p className="text-[14px] font-semibold text-[hsl(25,40%,20%)] tabular-nums">${a.recommended_price?.toFixed(2)}</p>
                        <p className="text-[10px] text-[hsl(25,15%,55%)]">{a.confidence_score}% conf.</p>
                      </div>
                      <ArrowRight className="h-3.5 w-3.5 text-[hsl(25,20%,58%)] opacity-0 group-hover:opacity-100 group-hover:translate-x-0.5 transition-all duration-200 hidden sm:block" />
                    </div>
                  </Link>
                  <button
                    type="button"
                    aria-label={`Delete analysis ${a.product_name}`}
                    className="flex-shrink-0 h-9 w-9 rounded-xl flex items-center justify-center text-[hsl(25,20%,58%)] hover:text-[hsl(4,55%,40%)] hover:bg-[hsl(4,55%,95%)] transition-colors duration-200"
                    onClick={() => setPendingDelete(a)}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {pendingDelete ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center px-4">
          <button
            type="button"
            className="absolute inset-0 bg-[hsl(25,20%,10%)]/40"
            aria-label="Close delete confirmation"
            disabled={deleting}
            onClick={() => {
              if (!deleting) setPendingDelete(null);
            }}
          />
          <div
            role="alertdialog"
            aria-modal="true"
            aria-labelledby="delete-analysis-title"
            aria-describedby="delete-analysis-description"
            className="relative z-10 w-full max-w-md rounded-2xl border border-[hsl(35,20%,88%)] bg-card p-6 shadow-warm"
          >
            <h2 id="delete-analysis-title" className="font-serif text-[hsl(25,40%,14%)] text-xl">
              Delete this analysis?
            </h2>
            <p id="delete-analysis-description" className="text-[13px] text-[hsl(25,15%,48%)] leading-relaxed mt-2">
              This will permanently remove this pricing analysis and its associated market data.
            </p>
            <div className="mt-5 flex flex-col-reverse sm:flex-row sm:justify-end gap-2">
              <button
                type="button"
                className="px-4 py-2.5 rounded-xl border border-[hsl(35,20%,82%)] text-[13px] text-[hsl(25,25%,35%)] hover:bg-[hsl(38,30%,93%)] transition-colors disabled:opacity-50"
                disabled={deleting}
                onClick={() => setPendingDelete(null)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="px-4 py-2.5 rounded-xl bg-[hsl(4,50%,42%)] text-[hsl(0,0%,98%)] text-[13px] font-medium hover:bg-[hsl(4,50%,36%)] transition-colors shadow-warm-sm disabled:opacity-50 disabled:pointer-events-none"
                disabled={deleting || !pendingDelete.id}
                onClick={() => {
                  if (!pendingDelete.id || deleting) return;
                  deleteMutation.mutate(pendingDelete.id);
                }}
              >
                {deleting ? 'Deleting…' : 'Delete Analysis'}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
