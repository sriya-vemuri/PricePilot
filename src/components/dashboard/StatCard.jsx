import React from 'react';

export default function StatCard({ title, value, subtitle, icon: Icon }) {
  return (
    <div className="bg-card rounded-2xl p-6 shadow-warm border border-[hsl(35,20%,88%)] hover:shadow-warm-md transition-all duration-300 group relative overflow-hidden">
      {/* Subtle corner accent */}
      <div className="absolute top-0 right-0 w-24 h-24 rounded-full bg-[hsl(38,50%,88%)] opacity-30 translate-x-8 -translate-y-8 group-hover:opacity-50 transition-opacity duration-300" />

      <div className="relative">
        {Icon && (
          <div className="h-9 w-9 rounded-xl bg-[hsl(38,45%,90%)] flex items-center justify-center mb-4 border border-[hsl(35,20%,84%)]">
            <Icon className="h-4 w-4 text-[hsl(25,40%,30%)]" />
          </div>
        )}
        <p className="text-[11px] font-medium text-[hsl(25,15%,52%)] uppercase tracking-[0.12em] mb-1">{title}</p>
        <p className="text-3xl font-serif text-[hsl(25,40%,16%)] leading-none mb-2">{value}</p>
        {subtitle && (
          <p className="text-[12px] text-[hsl(25,15%,58%)]">{subtitle}</p>
        )}
      </div>
    </div>
  );
}