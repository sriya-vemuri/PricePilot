import React, { useState } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import { useAuth } from '@/auth/AuthContext';

/** @param {{ className?: string }} props */
function GoogleIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" aria-hidden="true">
      <path
        fill="#4285F4"
        d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
      />
      <path
        fill="#34A853"
        d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
      />
      <path
        fill="#FBBC05"
        d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
      />
      <path
        fill="#EA4335"
        d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
      />
    </svg>
  );
}

/**
 * @param {unknown} state
 * @returns {{ from?: import('react-router-dom').Location; oauthError?: string }}
 */
function loginLocationState(state) {
  if (!state || typeof state !== 'object') return {};
  return /** @type {{ from?: import('react-router-dom').Location; oauthError?: string }} */ (state);
}

/** @param {import('react-router-dom').Location} location */
function oauthErrorFromLocation(location) {
  const state = loginLocationState(location.state);
  if (state.oauthError) return state.oauthError;

  const sources = [location.search, location.hash.replace(/^#/, '')];
  if (state.from) {
    sources.push(state.from.search, (state.from.hash || '').replace(/^#/, ''));
  }

  for (const raw of sources) {
    if (!raw) continue;
    const params = new URLSearchParams(raw.startsWith('?') ? raw.slice(1) : raw);
    const description = params.get('error_description') || params.get('error');
    if (description) return description.replace(/\+/g, ' ');
  }
  return '';
}

export default function Login() {
  const { user, loading, signInWithGoogle } = useAuth();
  const location = useLocation();
  const [signingIn, setSigningIn] = useState(false);
  const [errorMessage, setErrorMessage] = useState(() => oauthErrorFromLocation(location));

  const from = loginLocationState(location.state).from;
  const returnTo =
    from && typeof from.pathname === 'string' && from.pathname !== '/login'
      ? `${from.pathname}${from.search || ''}`
      : '/';

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="flex items-center gap-3 text-[hsl(25,25%,35%)]">
          <Loader2 className="h-5 w-5 animate-spin text-[hsl(25,40%,28%)]" />
          <span className="text-[13px] font-medium">Loading…</span>
        </div>
      </div>
    );
  }

  if (user) {
    return <Navigate to={returnTo} replace />;
  }

  const handleGoogle = async () => {
    setErrorMessage('');
    setSigningIn(true);
    try {
      await signInWithGoogle();
    } catch (error) {
      setSigningIn(false);
      setErrorMessage(error instanceof Error ? error.message : 'Google sign-in failed. Please try again.');
    }
  };

  return (
    <div className="min-h-screen bg-background flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-md animate-fade-up">
        <div className="flex flex-col items-center mb-8">
          <div className="h-12 w-12 rounded-2xl bg-[hsl(25,40%,22%)] flex items-center justify-center shadow-warm-sm mb-4">
            <span className="text-[hsl(38,33%,95%)] font-serif text-xl italic">P</span>
          </div>
          <h1 className="font-serif text-[hsl(25,40%,14%)] text-3xl leading-tight">PricePilot</h1>
          <p className="text-[9px] text-[hsl(25,15%,52%)] uppercase tracking-[0.15em] mt-1">Intelligence</p>
        </div>

        <div className="bg-card rounded-2xl shadow-warm border border-[hsl(35,20%,88%)] p-8">
          <p className="text-[11px] font-medium text-[hsl(25,15%,52%)] uppercase tracking-[0.14em] mb-1.5">Sign in</p>
          <h2 className="font-serif text-[hsl(25,40%,18%)] text-xl leading-snug mb-2">
            Pricing intelligence, ready when you are
          </h2>
          <p className="text-[13px] text-[hsl(25,15%,52%)] leading-relaxed mb-7">
            Sign in to generate competitor-backed price recommendations and keep your analyses in one place.
          </p>

          {errorMessage && (
            <div className="rounded-xl border border-[hsl(4,50%,82%)] bg-[hsl(4,55%,96%)] p-3.5 mb-5">
              <p className="text-[12px] text-[hsl(4,40%,38%)] leading-relaxed">{errorMessage}</p>
            </div>
          )}

          <button
            type="button"
            onClick={handleGoogle}
            disabled={signingIn}
            className="w-full h-12 rounded-xl border border-[hsl(35,20%,84%)] bg-white text-[14px] font-semibold text-[hsl(25,25%,18%)] flex items-center justify-center gap-3 hover:bg-[hsl(38,30%,96%)] hover:border-[hsl(35,25%,76%)] shadow-warm-sm transition-all duration-200 disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {signingIn ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Redirecting to Google…
              </>
            ) : (
              <>
                <GoogleIcon className="h-5 w-5" />
                Continue with Google
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
