/**
 * Shared HTTP client for the PricePilot FastAPI backend.
 *
 * Base URL:
 * - VITE_API_BASE_URL when set
 * - production default: same-origin (empty string)
 * - development default: http://127.0.0.1:8000
 */

import { ApiError, messageForApiError } from './errors';

const meta = /** @type {{ env?: { VITE_API_BASE_URL?: string; PROD?: boolean } }} */ (import.meta);

const API_BASE_URL =
  meta.env?.VITE_API_BASE_URL ||
  (meta.env?.PROD ? '' : 'http://127.0.0.1:8000');

export function getApiBaseUrl() {
  return String(API_BASE_URL || '').trim().replace(/\/$/, '');
}

/**
 * @param {string} path
 * @param {Record<string, string | number | undefined> | undefined} params
 */
function buildRequestUrl(path, params) {
  const base = getApiBaseUrl();
  /** @type {URL} */
  let url;
  if (path.startsWith('http')) {
    url = new URL(path);
  } else if (base) {
    url = new URL(`${base}${path.startsWith('/') ? path : `/${path}`}`);
  } else {
    // Same-origin production: resolve against the current page origin.
    const origin =
      typeof window !== 'undefined' && window.location?.origin
        ? window.location.origin
        : 'http://localhost';
    url = new URL(path.startsWith('/') ? path : `/${path}`, origin);
  }

  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        url.searchParams.set(key, String(value));
      }
    });
  }
  return url;
}

/**
 * @param {string} path
 * @param {RequestInit & { params?: Record<string, string | number | undefined> }} [options]
 */
export async function apiRequest(path, options = {}) {
  const { params, headers, ...init } = options;
  const url = buildRequestUrl(path, params);

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
