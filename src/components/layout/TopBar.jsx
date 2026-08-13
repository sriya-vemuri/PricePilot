import React from 'react';

export default function TopBar() {
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
