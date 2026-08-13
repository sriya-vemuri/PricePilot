import React from 'react';

const categories = [
  { value: 'electronics', label: 'Electronics' },
  { value: 'software', label: 'Software' },
  { value: 'clothing', label: 'Clothing' },
  { value: 'food_beverage', label: 'Food & Beverage' },
  { value: 'health_beauty', label: 'Health & Beauty' },
  { value: 'home_garden', label: 'Home & Garden' },
  { value: 'automotive', label: 'Automotive' },
  { value: 'services', label: 'Services' },
  { value: 'other', label: 'Other' },
];

const strategies = [
  {
    value: 'aggressive',
    label: 'Aggressive',
    desc: 'Undercut competitors to gain market share quickly',
    icon: '↘',
  },
  {
    value: 'balanced',
    label: 'Balanced',
    desc: 'Match market pricing while protecting margins',
    icon: '⟷',
  },
  {
    value: 'premium',
    label: 'Premium',
    desc: 'Price above market to signal superior quality',
    icon: '↗',
  },
];

const fieldClass = "w-full px-4 py-3 rounded-xl border border-[hsl(35,20%,84%)] bg-[hsl(38,35%,97%)] text-[14px] text-[hsl(25,25%,18%)] placeholder:text-[hsl(25,15%,62%)] focus:outline-none focus:border-[hsl(25,40%,40%)] focus:ring-2 focus:ring-[hsl(25,40%,40%)]/10 transition-all duration-200";

export default function ProductForm({ form, setForm }) {
  const update = (field, value) => setForm((prev) => ({ ...prev, [field]: value }));

  return (
    <div className="space-y-7">
      {/* Name + Category */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        <div className="space-y-2">
          <label className="text-[11px] font-medium text-[hsl(25,20%,45%)] uppercase tracking-[0.1em]">Product Name</label>
          <input
            className={fieldClass}
            placeholder="e.g., Premium Wireless Headphones"
            value={form.name}
            onChange={(e) => update('name', e.target.value)}
          />
        </div>
        <div className="space-y-2">
          <label className="text-[11px] font-medium text-[hsl(25,20%,45%)] uppercase tracking-[0.1em]">Category</label>
          <select
            className={fieldClass}
            value={form.category}
            onChange={(e) => update('category', e.target.value)}
          >
            <option value="">Select category</option>
            {categories.map((c) => (
              <option key={c.value} value={c.value}>{c.label}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Cost + Margin */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        <div className="space-y-2">
          <label className="text-[11px] font-medium text-[hsl(25,20%,45%)] uppercase tracking-[0.1em]">Base Cost</label>
          <div className="relative">
            <span className="absolute left-4 top-1/2 -translate-y-1/2 text-[14px] text-[hsl(25,20%,52%)]">$</span>
            <input
              className={`${fieldClass} pl-8`}
              type="number"
              step="0.01"
              min="0"
              placeholder="0.00"
              value={form.cost}
              onChange={(e) => update('cost', parseFloat(e.target.value) || '')}
            />
          </div>
        </div>
        <div className="space-y-2">
          <label className="text-[11px] font-medium text-[hsl(25,20%,45%)] uppercase tracking-[0.1em]">Target Margin</label>
          <div className="relative">
            <input
              className={`${fieldClass} pr-8`}
              type="number"
              min="0"
              max="200"
              placeholder="30"
              value={form.target_margin}
              onChange={(e) => update('target_margin', parseFloat(e.target.value) || '')}
            />
            <span className="absolute right-4 top-1/2 -translate-y-1/2 text-[14px] text-[hsl(25,20%,52%)]">%</span>
          </div>
        </div>
      </div>

      {/* Target Market */}
      <div className="space-y-2">
        <label className="text-[11px] font-medium text-[hsl(25,20%,45%)] uppercase tracking-[0.1em]">Target Market</label>
        <textarea
          className={`${fieldClass} h-24 resize-none leading-relaxed`}
          placeholder="Describe your ideal customer segment and market context..."
          value={form.target_market}
          onChange={(e) => update('target_market', e.target.value)}
        />
      </div>

      {/* Strategy Selector */}
      <div className="space-y-3">
        <label className="text-[11px] font-medium text-[hsl(25,20%,45%)] uppercase tracking-[0.1em]">Pricing Strategy</label>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {strategies.map((s) => {
            const isSelected = form.strategy === s.value;
            return (
              <button
                key={s.value}
                type="button"
                onClick={() => update('strategy', s.value)}
                className={`p-5 rounded-2xl border-2 text-left transition-all duration-200 group ${
                  isSelected
                    ? 'border-[hsl(25,40%,28%)] bg-[hsl(25,40%,28%)] shadow-warm-sm'
                    : 'border-[hsl(35,20%,86%)] bg-[hsl(38,35%,97%)] hover:border-[hsl(35,25%,76%)] hover:bg-[hsl(38,30%,94%)]'
                }`}
              >
                <span className={`text-xl mb-2 block ${isSelected ? 'opacity-100' : 'opacity-40 group-hover:opacity-60'}`}>
                  {s.icon}
                </span>
                <p className={`text-[13px] font-semibold mb-1 ${isSelected ? 'text-[hsl(38,33%,94%)]' : 'text-[hsl(25,35%,22%)]'}`}>
                  {s.label}
                </p>
                <p className={`text-[11px] leading-relaxed ${isSelected ? 'text-[hsl(38,25%,78%)]' : 'text-[hsl(25,15%,52%)]'}`}>
                  {s.desc}
                </p>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}