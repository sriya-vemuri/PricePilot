import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { LogOut } from 'lucide-react';
import { useAuth } from '@/auth/AuthContext';

/** @param {import('@supabase/supabase-js').User | null | undefined} user */
function displayName(user) {
  const meta = user?.user_metadata || {};
  return meta.full_name || meta.name || user?.email || 'Account';
}

/** @param {import('@supabase/supabase-js').User | null | undefined} user */
function avatarUrl(user) {
  const meta = user?.user_metadata || {};
  return meta.avatar_url || meta.picture || '';
}

export default function TopBar() {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();
  const [signingOut, setSigningOut] = useState(false);

  const name = displayName(user);
  const email = user?.email || '';
  const photo = avatarUrl(user);
  const initial = (name || 'P').charAt(0).toUpperCase();

  const handleSignOut = async () => {
    setSigningOut(true);
    try {
      await signOut();
      navigate('/login', { replace: true });
    } catch {
      setSigningOut(false);
    }
  };

  if (!user) {
    return (
      <div className="flex items-center gap-2.5 px-3 py-1.5">
        <div className="h-7 w-7 rounded-lg bg-[hsl(25,40%,22%)] flex items-center justify-center">
          <span className="text-[10px] font-semibold text-[hsl(38,33%,95%)]">P</span>
        </div>
        <span className="text-[13px] font-medium text-[hsl(25,25%,25%)] hidden sm:block">
          PricePilot
        </span>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-3">
      <div className="flex items-center gap-2 min-w-0">
        {photo ? (
          <img
            src={photo}
            alt=""
            className="h-7 w-7 rounded-lg object-cover border border-[hsl(35,20%,84%)] flex-shrink-0"
          />
        ) : (
          <div className="h-7 w-7 rounded-lg bg-[hsl(25,40%,22%)] flex items-center justify-center flex-shrink-0">
            <span className="text-[10px] font-semibold text-[hsl(38,33%,95%)]">{initial}</span>
          </div>
        )}
        <div className="hidden sm:block min-w-0">
          <p className="text-[12px] font-medium text-[hsl(25,25%,20%)] truncate max-w-[180px] leading-tight">
            {name}
          </p>
          {email && email !== name && (
            <p className="text-[10px] text-[hsl(25,15%,55%)] truncate max-w-[180px] leading-tight mt-0.5">
              {email}
            </p>
          )}
        </div>
      </div>
      <button
        type="button"
        onClick={handleSignOut}
        disabled={signingOut}
        className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[12px] font-medium text-[hsl(25,20%,40%)] hover:text-[hsl(25,40%,18%)] hover:bg-[hsl(38,35%,88%)] transition-colors disabled:opacity-60"
      >
        <LogOut className="h-3.5 w-3.5" />
        <span className="hidden sm:inline">{signingOut ? 'Signing out…' : 'Sign out'}</span>
      </button>
    </div>
  );
}
