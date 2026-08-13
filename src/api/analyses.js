/**
 * Analysis API — thin wrappers around FastAPI /api/analyses routes.
 */

import { apiRequest } from './client';

/**
 * Create a complete pricing analysis (market research + pricing + persistence).
 * @param {{
 *   product_name: string;
 *   category: string;
 *   cost: number;
 *   target_margin: number;
 *   target_market?: string;
 *   strategy: string;
 * }} payload
 */
export async function createAnalysis(payload) {
  return apiRequest('/api/analyses', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

/**
 * List analyses (newest first). Returns { items, total, limit, offset }.
 * @param {{ limit?: number; offset?: number }} [opts]
 */
export async function listAnalyses({ limit = 50, offset = 0 } = {}) {
  return apiRequest('/api/analyses', {
    method: 'GET',
    params: { limit, offset },
  });
}

/**
 * Fetch one analysis with nested market_data.
 * @param {string} id
 */
export async function getAnalysisById(id) {
  return apiRequest(`/api/analyses/${encodeURIComponent(id)}`, {
    method: 'GET',
  });
}
