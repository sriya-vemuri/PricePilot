/**
 * Client-side helpers for the authenticated user's dashboard.
 * Operates on analysis list items already returned by GET /api/analyses.
 */

/**
 * @typedef {object} AnalysisSummary
 * @property {string} [id]
 * @property {string} [product_name]
 * @property {string} [category]
 * @property {string} [strategy]
 * @property {string} [created_at]
 * @property {number} [baseline_price]
 * @property {number} [recommended_price]
 * @property {number} [competitor_avg_price]
 * @property {number} [confidence_score]
 * @property {string} [demand_signal]
 * @property {{ has_reliable_data?: boolean; market_trend?: string; tavily_query?: string; competitor_price_1?: number; competitor_price_2?: number; competitor_price_3?: number }} [market_data]
 */

export const ALL_CATEGORIES = 'all';

export const CATEGORY_LABELS = {
  electronics: 'Electronics',
  software: 'Software',
  clothing: 'Clothing',
  food_beverage: 'Food & Beverage',
  health_beauty: 'Health & Beauty',
  home_garden: 'Home & Garden',
  automotive: 'Automotive',
  services: 'Services',
  other: 'Other',
};

/** @param {string | undefined} category */
export function categoryLabel(category) {
  if (!category) return 'Other';
  return CATEGORY_LABELS[category] || String(category).replace(/_/g, ' ');
}

/**
 * Unique category values present in the user's analyses, sorted by label.
 * @param {AnalysisSummary[]} analyses
 * @returns {string[]}
 */
export function uniqueCategories(analyses) {
  const seen = new Set();
  for (const analysis of analyses || []) {
    if (analysis?.category) seen.add(analysis.category);
  }
  return [...seen].sort((a, b) => categoryLabel(a).localeCompare(categoryLabel(b)));
}

/**
 * @param {AnalysisSummary[]} analyses
 * @param {string} category
 * @returns {AnalysisSummary[]}
 */
export function filterAnalysesByCategory(analyses, category) {
  const items = Array.isArray(analyses) ? analyses : [];
  if (!category || category === ALL_CATEGORIES) return items;
  return items.filter((analysis) => analysis.category === category);
}

/**
 * Keep the newest analysis for each product name (list is newest-first).
 * @param {AnalysisSummary[]} analyses
 * @returns {AnalysisSummary[]}
 */
export function mostRecentAnalysisPerProduct(analyses) {
  const items = Array.isArray(analyses) ? analyses : [];
  const byProduct = new Map();
  for (const analysis of items) {
    const key = String(analysis?.product_name || '').trim().toLowerCase();
    if (!key || byProduct.has(key)) continue;
    byProduct.set(key, analysis);
  }
  return [...byProduct.values()];
}

/**
 * Most frequent non-empty value in a list.
 * @param {(string | undefined | null)[]} values
 * @returns {{ value: string | null; count: number }}
 */
function dominantValue(values) {
  /** @type {Record<string, number>} */
  const counts = {};
  for (const value of values) {
    if (!value) continue;
    counts[value] = (counts[value] || 0) + 1;
  }
  const ranked = Object.entries(counts).sort((a, b) => b[1] - a[1]);
  if (!ranked.length) return { value: null, count: 0 };
  return { value: ranked[0][0], count: ranked[0][1] };
}

/**
 * @param {AnalysisSummary[]} analyses
 * @returns {{ value: string | null; count: number; total: number }}
 */
export function dominantDemandLevel(analyses) {
  const items = Array.isArray(analyses) ? analyses : [];
  return { ...dominantValue(items.map((analysis) => analysis.demand_signal)), total: items.length };
}

/**
 * @param {AnalysisSummary[]} analyses
 * @returns {{ value: string | null; count: number; total: number }}
 */
export function dominantMarketTrend(analyses) {
  const items = Array.isArray(analyses) ? analyses : [];
  return {
    ...dominantValue(items.map((analysis) => analysis.market_data?.market_trend)),
    total: items.length,
  };
}

/**
 * Distinct product names, newest first. List payloads are already newest-first.
 * @param {AnalysisSummary[]} analyses
 * @param {number} [limit]
 * @returns {{ names: string[]; extraCount: number }}
 */
export function distinctRecentProducts(analyses, limit = 6) {
  const unique = mostRecentAnalysisPerProduct(analyses);
  const names = unique
    .map((analysis) => String(analysis.product_name || '').trim())
    .filter(Boolean);
  return {
    names: names.slice(0, limit),
    extraCount: Math.max(0, names.length - limit),
  };
}

/** @param {string} category */
export function marketSummaryTitle(category) {
  if (!category || category === ALL_CATEGORIES) return 'Overall Market Summary';
  return `${categoryLabel(category)} Market Summary`;
}

/** @param {number} count */
export function analysesCountLabel(count) {
  return count === 1 ? '1 analysis' : `${count} analyses`;
}

/**
 * @param {AnalysisSummary[]} analyses
 */
export function dashboardSummary(analyses) {
  const items = Array.isArray(analyses) ? analyses : [];
  const total = items.length;
  if (total === 0) {
    return {
      total: 0,
      avgRecommended: null,
      avgConfidence: null,
      reliableCount: 0,
      reliablePercent: null,
    };
  }

  const avgRecommended =
    items.reduce((sum, analysis) => sum + (Number(analysis.recommended_price) || 0), 0) / total;
  const avgConfidence = Math.round(
    items.reduce((sum, analysis) => sum + (Number(analysis.confidence_score) || 0), 0) / total
  );
  const reliableCount = items.filter((analysis) => analysis.market_data?.has_reliable_data).length;

  return {
    total,
    avgRecommended,
    avgConfidence,
    reliableCount,
    reliablePercent: Math.round((reliableCount / total) * 100),
  };
}

/**
 * @param {string} name
 * @param {number} max
 */
export function truncateLabel(name, max = 16) {
  const text = String(name || 'Product').trim() || 'Product';
  if (text.length <= max) return text;
  return `${text.slice(0, max - 1)}…`;
}

/**
 * Chart rows: one product, baseline vs recommended.
 * @param {AnalysisSummary[]} analyses
 * @param {number} [limit]
 */
export function productPricingChartData(analyses, limit = 12) {
  return mostRecentAnalysisPerProduct(analyses)
    .slice(0, limit)
    .map((analysis) => {
      const product = analysis.product_name || 'Product';
      return {
        id: analysis.id,
        product,
        label: truncateLabel(product),
        baseline: Number(analysis.baseline_price) || 0,
        recommended: Number(analysis.recommended_price) || 0,
      };
    });
}
