/**
 * Frontend API error helpers.
 * Backend ErrorResponse shape: { error, message, details? }
 */

export class ApiError extends Error {
  /**
   * @param {{ status: number; error: string; message: string; details?: unknown; cause?: unknown }} opts
   */
  constructor({ status, error, message, details = null, cause }) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.error = error;
    this.details = details;
    if (cause !== undefined) {
      this.cause = cause;
    }
  }
}

const USER_MESSAGES = {
  tavily_not_configured:
    'Market research is not configured. Set TAVILY_API_KEY on the backend and try again.',
  pricing_calculation_error:
    'Pricing analysis could not be completed. Please try again.',
  database_error:
    'The analysis could not be saved. Please try again in a moment.',
  analysis_not_found:
    'This analysis could not be found. It may have been deleted.',
  validation_error:
    'Some of the submitted details were invalid. Check the form and try again.',
  network_error:
    'Could not reach the PricePilot backend. Confirm it is running and try again.',
};

/**
 * Prefer a stable user-facing message for known backend error codes.
 * @param {string} errorCode
 * @param {string} fallbackMessage
 * @param {number} [status]
 */
export function messageForApiError(errorCode, fallbackMessage, status) {
  if (USER_MESSAGES[errorCode]) {
    return USER_MESSAGES[errorCode];
  }
  if (status === 404) {
    return USER_MESSAGES.analysis_not_found;
  }
  if (status === 422) {
    return USER_MESSAGES.validation_error;
  }
  if (!status) {
    return USER_MESSAGES.network_error;
  }
  return fallbackMessage || 'Something went wrong. Please try again.';
}

/**
 * Convert market_warnings codes into short readable labels.
 * @param {string[] | null | undefined} warnings
 * @returns {string[]}
 */
export function formatMarketWarnings(warnings) {
  if (!Array.isArray(warnings) || warnings.length === 0) return [];
  const labels = {
    insufficient_market_data: 'Limited reliable market pricing data was available.',
    stage3_low_trust: 'Market data came from a broader low-trust search stage.',
    tavily_unavailable: 'Live market search was temporarily unavailable; baseline pricing was used.',
    trend_unavailable: 'Market trend could not be determined from search results.',
    demand_unavailable: 'Demand signal could not be determined from search results.',
    tavily_partial_failure: 'Some market search queries failed; results may be incomplete.',
  };
  const seen = new Set();
  const out = [];
  for (const code of warnings) {
    if (!code || seen.has(code)) continue;
    seen.add(code);
    out.push(labels[code] || String(code).replace(/_/g, ' '));
  }
  return out;
}
