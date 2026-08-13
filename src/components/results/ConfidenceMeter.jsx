import React, { useEffect, useState } from 'react';

export default function ConfidenceMeter({ score, explanation }) {
  const [animated, setAnimated] = useState(0);

  useEffect(() => {
    const timer = setTimeout(() => setAnimated(score), 100);
    return () => clearTimeout(timer);
  }, [score]);

  const getLabel = () => {
    if (score >= 65) return { text: 'High', color: 'text-[hsl(140,40%,38%)]' };
    if (score >= 42) return { text: 'Medium', color: 'text-[hsl(38,55%,42%)]' };
    return { text: 'Low', color: 'text-[hsl(4,55%,48%)]' };
  };

  const label = getLabel();

  const radius = 54;
  const circumference = Math.PI * radius;
  const offset = circumference - (animated / 100) * circumference;

  return (
    <div className="bg-card rounded-2xl shadow-warm border border-[hsl(35,20%,88%)] p-8 flex flex-col items-center">
      <p className="text-[11px] font-medium text-[hsl(25,15%,52%)] uppercase tracking-[0.12em] mb-6 self-start w-full">Confidence</p>

      {/* Arc gauge */}
      <div className="relative w-36 h-20 mb-5">
        <svg width="144" height="80" viewBox="0 0 144 80">
          <path d="M 12 76 A 60 60 0 0 1 132 76" fill="none" stroke="hsl(35, 20%, 86%)" strokeWidth="10" strokeLinecap="round" />
          <path
            d="M 12 76 A 60 60 0 0 1 132 76"
            fill="none"
            stroke="hsl(25, 40%, 28%)"
            strokeWidth="10"
            strokeLinecap="round"
            strokeDasharray={`${circumference}`}
            strokeDashoffset={`${offset}`}
            style={{ transition: 'stroke-dashoffset 1.2s ease-out' }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-end pb-1">
          <span className="font-serif text-[hsl(25,40%,14%)] text-3xl leading-none">{score}</span>
        </div>
      </div>

      <p className={`text-[13px] font-semibold ${label.color} mb-3`}>{label.text} Confidence</p>

      {/* One-line explanation */}
      <p className="text-[11px] text-[hsl(25,15%,52%)] text-center leading-relaxed">
        {explanation
          ? explanation.split('.')[0] + '.'
          : 'Based on market data quality and signal strength'}
      </p>

      {/* Bar */}
      <div className="w-full mt-5 space-y-2">
        <div className="flex justify-between text-[10px] text-[hsl(25,15%,55%)]">
          <span>0</span>
          <span>50</span>
          <span>100</span>
        </div>
        <div className="h-1.5 bg-[hsl(35,20%,86%)] rounded-full overflow-hidden">
          <div
            className="h-full bg-[hsl(25,40%,28%)] rounded-full transition-all duration-1000 ease-out"
            style={{ width: `${animated}%` }}
          />
        </div>
      </div>
    </div>
  );
}