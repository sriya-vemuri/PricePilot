import React from 'react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import { useAuth } from '@/auth/AuthContext';

export default function ProtectedRoute() {
  const { user, loading } = useAuth();
  const location = useLocation();

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

  if (!user) {
    const search = new URLSearchParams(location.search);
    const hash = new URLSearchParams(location.hash.replace(/^#/, ''));
    const oauthError = (
      search.get('error_description') ||
      search.get('error') ||
      hash.get('error_description') ||
      hash.get('error') ||
      ''
    ).replace(/\+/g, ' ');

    return (
      <Navigate
        to="/login"
        replace
        state={{ from: location, oauthError: oauthError || undefined }}
      />
    );
  }

  return <Outlet />;
}
