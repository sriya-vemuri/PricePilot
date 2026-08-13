/**
 * Shared HTTP client for the PricePilot FastAPI backend.
 * Base URL comes from VITE_API_BASE_URL (default: http://127.0.0.1:8000).
 */

import { ApiError, messageForApiError } from './errors';

const DEFAULT_BASE_URL = 'http://127.0.0.1:8000';

export function getApiBaseUrl() {
  const meta = /** @type {{ env?: { VITE_API_BASE_URL?: string } }} */ (import.meta);
  const configured = meta.env?.VITE_API_BASE_URL;
  if (typeof configured === 'string' && configured.trim()) {
    return configured.trim().replace(/\/$/, '');
  }
  return DEFAULT_BASE_URL;
}

/**
 * @param {string} path
 * @param {RequestInit & { params?: Record<string, string | number | undefined> }} [options]
 */
export async function apiRequest(path, options = {}) {
  const { params, headers, ...init } = options;
  const url = new URL(path.startsWith('http') ? path : `${getApiBaseUrl()}${path}`);

  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        url.searchParams.set(key, String(value));
      }
    });
  }

  let response;
  try {
    response = await fetch(url.toString(), {
      ...init,
      headers: {
        Accept: 'application/json',
        ...(init.body ? { 'Content-Type': 'application/json' } : {}),
        ...headers,
      },
    });
  } catch (cause) {
    throw new ApiError({
      status: 0,
      error: 'network_error',
      message: 'Could not reach the PricePilot backend. Is it running on the configured API URL?',
      cause,
    });
  }

  const text = await response.text();
  let data = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = null;
    }
  }

  if (!response.ok) {
    const errorCode = data && typeof data.error === 'string' ? data.error : 'http_error';
    const message =
      data && typeof data.message === 'string'
        ? data.message
        : `Request failed with status ${response.status}`;
    throw new ApiError({
      status: response.status,
      error: errorCode,
      message: messageForApiError(errorCode, message, response.status),
      details: data?.details ?? null,
    });
  }

  return data;
}
