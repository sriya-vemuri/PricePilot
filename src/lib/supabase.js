import { createClient } from '@supabase/supabase-js';

/**
 * Single shared Supabase browser client for Auth only.
 * Application data stays on the FastAPI / Neon stack.
 */

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabasePublishableKey = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY;

function requireEnv(name, value) {
  const trimmed = typeof value === 'string' ? value.trim() : '';
  if (!trimmed) {
    const hint = import.meta.env.DEV
      ? ` Set ${name} in your local .env (or .env.local) and restart Vite.`
      : ` Configure ${name} in the Vercel frontend project environment.`;
    throw new Error(`[Supabase] Missing required environment variable: ${name}.${hint}`);
  }
  return trimmed;
}

const url = requireEnv('VITE_SUPABASE_URL', supabaseUrl);
const publishableKey = requireEnv('VITE_SUPABASE_PUBLISHABLE_KEY', supabasePublishableKey);

export const supabase = createClient(url, publishableKey);
