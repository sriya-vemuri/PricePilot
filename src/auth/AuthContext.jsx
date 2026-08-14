import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { supabase } from '@/lib/supabase';

const AuthContext = createContext(null);

function oauthCallbackParams() {
  const search = new URLSearchParams(window.location.search);
  const hash = new URLSearchParams(window.location.hash.replace(/^#/, ''));
  return {
    hasCode: Boolean(search.get('code') || search.get('access_token') || hash.get('access_token')),
    hasError: Boolean(search.get('error') || hash.get('error')),
  };
}

/**
 * Provides Supabase Auth session state to the React tree.
 * Frontend route guards use this context. Backend API is not authenticated yet.
 */
export function AuthProvider({ children }) {
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    /** @type {ReturnType<typeof setTimeout> | undefined} */
    let callbackTimeout;

    const finishLoading = () => {
      if (active) setLoading(false);
    };

    supabase.auth.getSession().then(({ data, error }) => {
      if (!active) return;
      if (error) {
        console.error('[Auth] Failed to get session:', error.message);
        setSession(null);
        finishLoading();
        return;
      }
      setSession(data.session ?? null);
      const { hasCode, hasError } = oauthCallbackParams();
      if (!data.session && hasCode && !hasError) {
        callbackTimeout = setTimeout(finishLoading, 10000);
        return;
      }
      finishLoading();
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((event, nextSession) => {
      setSession(nextSession ?? null);
      const { hasCode, hasError } = oauthCallbackParams();
      if (event === 'INITIAL_SESSION' && !nextSession && hasCode && !hasError) {
        return;
      }
      finishLoading();
    });

    return () => {
      active = false;
      if (callbackTimeout) clearTimeout(callbackTimeout);
      subscription.unsubscribe();
    };
  }, []);

  const signInWithGoogle = useCallback(async () => {
    const { data, error } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: {
        // Uses the current origin so local and production both work without hardcoding.
        redirectTo: window.location.origin,
      },
    });
    if (error) {
      throw error;
    }
    return data;
  }, []);

  const signOut = useCallback(async () => {
    const { error } = await supabase.auth.signOut();
    if (error) {
      throw error;
    }
  }, []);

  const value = useMemo(
    () => ({
      session,
      user: session?.user ?? null,
      loading,
      signInWithGoogle,
      signOut,
    }),
    [session, loading, signInWithGoogle, signOut]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
