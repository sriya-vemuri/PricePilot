import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { LayoutDashboard, Plus, History, ChevronLeft, ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';

const navItems = [
  { label: 'Dashboard', path: '/', icon: LayoutDashboard },
  { label: 'New Analysis', path: '/new-analysis', icon: Plus },
  { label: 'History', path: '/history', icon: History },
];

export default function Sidebar() {
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(false);

  return (
    <aside className={cn(
      "fixed left-0 top-0 h-screen flex flex-col z-40 transition-all duration-300 ease-in-out",
      "bg-[hsl(35,28%,92%)] border-r border-[hsl(35,18%,84%)]",
      collapsed ? "w-[68px]" : "w-[230px]"
    )}>
      {/* Logo */}
      <div className={cn(
        "flex items-center gap-3 border-b border-[hsl(35,18%,84%)] transition-all duration-300",
        collapsed ? "px-4 py-5 justify-center" : "px-5 py-5"
      )}>
        <div className="h-8 w-8 rounded-xl bg-[hsl(25,40%,22%)] flex items-center justify-center flex-shrink-0 shadow-warm-sm">
          <span className="text-[hsl(38,33%,95%)] font-serif text-sm font-normal italic">P</span>
        </div>
        {!collapsed && (
          <div className="overflow-hidden">
            <h1 className="font-serif text-[hsl(25,40%,22%)] text-base leading-tight tracking-tight">PricePilot</h1>
            <p className="text-[9px] text-[hsl(25,15%,52%)] font-sans uppercase tracking-[0.15em] mt-0.5">Intelligence</p>
          </div>
        )}
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-0.5">
        {navItems.map((item) => {
          const isActive = location.pathname === item.path;
          return (
            <Link
              key={item.path}
              to={item.path}
              title={collapsed ? item.label : undefined}
              className={cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-xl text-[13px] font-medium transition-all duration-200 group",
                collapsed && "justify-center px-2",
                isActive
                  ? "bg-[hsl(25,40%,22%)] text-[hsl(38,33%,95%)] shadow-warm-sm"
                  : "text-[hsl(25,20%,45%)] hover:text-[hsl(25,40%,22%)] hover:bg-[hsl(38,35%,88%)]"
              )}
            >
              <item.icon className={cn("flex-shrink-0 transition-transform duration-200",
                collapsed ? "h-4.5 w-4.5" : "h-4 w-4",
                !isActive && "group-hover:scale-110"
              )} />
              {!collapsed && <span>{item.label}</span>}
            </Link>
          );
        })}
      </nav>

      {/* Collapse toggle */}
      <div className="px-3 pb-4 border-t border-[hsl(35,18%,84%)] pt-3">
        <button
          onClick={() => setCollapsed(!collapsed)}
          className={cn(
            "w-full flex items-center justify-center p-2 rounded-xl text-[hsl(25,15%,52%)]",
            "hover:text-[hsl(25,40%,22%)] hover:bg-[hsl(38,35%,88%)] transition-all duration-200"
          )}
        >
          {collapsed
            ? <ChevronRight className="h-3.5 w-3.5" />
            : <ChevronLeft className="h-3.5 w-3.5" />
          }
        </button>
      </div>
    </aside>
  );
}