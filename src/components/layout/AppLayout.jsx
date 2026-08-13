import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import TopBar from './TopBar';
import { Menu } from 'lucide-react';

export default function AppLayout() {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="min-h-screen bg-background">
      {mobileOpen && (
        <div
          className="fixed inset-0 bg-[hsl(25,25%,14%)]/30 backdrop-blur-[2px] z-30 lg:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      <div className={`fixed z-40 lg:block ${mobileOpen ? 'block' : 'hidden'}`}>
        <Sidebar onClose={() => setMobileOpen(false)} />
      </div>

      <div className="lg:ml-[230px] flex flex-col min-h-screen transition-all duration-300">
        {/* Top bar */}
        <header className="h-14 border-b border-[hsl(35,18%,86%)] bg-[hsl(36,40%,97%)]/80 backdrop-blur-sm flex items-center justify-between px-4 lg:px-7 sticky top-0 z-20">
          <button
            className="lg:hidden p-2 rounded-xl hover:bg-[hsl(38,35%,88%)] transition-colors"
            onClick={() => setMobileOpen(true)}
          >
            <Menu className="h-4.5 w-4.5 text-[hsl(25,25%,35%)]" />
          </button>

          {/* Breadcrumb-style page indicator can be added here */}
          <div className="hidden lg:block">
            <div className="h-1.5 w-1.5 rounded-full bg-[hsl(38,50%,68%)]" />
          </div>

          <TopBar />
        </header>

        <main className="flex-1 px-4 py-6 lg:px-10 lg:py-10">
          <Outlet />
        </main>
      </div>
    </div>
  );
}