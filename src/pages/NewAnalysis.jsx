import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { createAnalysis } from '@/api/analyses';
import { ApiError } from '@/api/errors';
import { Loader2, Sparkles } from 'lucide-react';
import { toast } from 'sonner';
import ProductForm from '../components/analysis/ProductForm';

const initialForm = {
  name: '',
  category: '',
  cost: '',
  target_margin: 30,
  target_market: '',
  strategy: 'balanced',
};

export default function NewAnalysis() {
  const [form, setForm] = useState(initialForm);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const cost = Number(form.cost);
  const targetMargin = Number(form.target_margin);
  const canSubmit = Boolean(form.name && form.category && cost > 0 && form.strategy);

  const handleGenerate = async () => {
    if (!canSubmit || loading) return;
    setLoading(true);
    setErrorMessage('');

    try {
      const analysis = await createAnalysis({
        product_name: form.name.trim(),
        category: form.category,
        cost,
        target_margin: Number.isFinite(targetMargin) ? targetMargin : 30,
        target_market: (form.target_market || '').trim() || 'United States',
        strategy: form.strategy,
      });

      await queryClient.invalidateQueries({ queryKey: ['analyses'] });
      toast.success('Analysis complete');
      navigate(`/results/${analysis.id}`);
    } catch (error) {
      const message =
        error instanceof ApiError
          ? error.message
          : error?.message || 'Failed to generate analysis.';
      setErrorMessage(message);
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto animate-fade-up">
      {/* Header */}
      <div className="mb-10">
        <p className="text-[11px] font-medium text-[hsl(25,15%,52%)] uppercase tracking-[0.14em] mb-1.5">New Report</p>
        <h1 className="font-serif text-[hsl(25,40%,14%)] text-3xl leading-tight">Pricing Analysis</h1>
        <p className="text-[13px] text-[hsl(25,15%,52%)] mt-2">Enter your product details to generate an AI-powered pricing recommendation</p>
      </div>

      {/* Form card */}
      <div className="bg-card rounded-2xl shadow-warm border border-[hsl(35,20%,88%)] p-8 mb-6">
        <ProductForm form={form} setForm={setForm} />
      </div>

      {/* Loading state — single in-progress experience (no SSE stage stream) */}
      {loading && (
        <div className="bg-[hsl(38,45%,95%)] rounded-2xl border border-[hsl(35,25%,84%)] p-5 mb-6">
          <div className="flex items-center gap-3 mb-3">
            <Loader2 className="h-4 w-4 text-[hsl(25,40%,35%)] animate-spin" />
            <span className="text-[13px] font-medium text-[hsl(25,40%,25%)]">
              Running market research and pricing analysis...
            </span>
          </div>
          <div className="h-1 w-full rounded-full bg-[hsl(35,25%,82%)] overflow-hidden">
            <div className="h-full w-2/3 rounded-full bg-[hsl(25,40%,35%)] animate-pulse" />
          </div>
          <p className="text-[11px] text-[hsl(25,15%,52%)] mt-2.5">
            This usually takes a few seconds. Please keep this tab open.
          </p>
        </div>
      )}

      {errorMessage && !loading && (
        <div className="rounded-2xl border border-[hsl(4,50%,82%)] bg-[hsl(4,55%,96%)] p-4 mb-6">
          <p className="text-[13px] font-medium text-[hsl(4,45%,32%)] mb-0.5">Could not create analysis</p>
          <p className="text-[12px] text-[hsl(4,40%,38%)] leading-relaxed">{errorMessage}</p>
        </div>
      )}

      {/* Submit */}
      <button
        onClick={handleGenerate}
        disabled={!canSubmit || loading}
        className={`w-full h-14 rounded-2xl text-[14px] font-semibold flex items-center justify-center gap-2.5 transition-all duration-300 ${
          canSubmit && !loading
            ? 'bg-[hsl(25,40%,22%)] text-[hsl(38,33%,95%)] hover:bg-[hsl(25,40%,17%)] shadow-warm hover:shadow-warm-md hover:-translate-y-0.5'
            : 'bg-[hsl(35,20%,84%)] text-[hsl(25,15%,55%)] cursor-not-allowed'
        }`}
      >
        {loading ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" />
            Generating analysis...
          </>
        ) : (
          <>
            <Sparkles className="h-4 w-4" />
            Generate Pricing Analysis
          </>
        )}
      </button>

      {!canSubmit && !loading && (
        <p className="text-center text-[12px] text-[hsl(25,15%,58%)] mt-3">
          Fill in all required fields to continue
        </p>
      )}
    </div>
  );
}
