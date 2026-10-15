// src/components/ui/StatsCard.tsx
import { TrendingUp, TrendingDown } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

interface StatsCardProps {
  label: string;
  value: string | number;
  change?: number;
  icon: LucideIcon;
  iconBg?: string;     // e.g. "bg-indigo-100"
  iconColor?: string;  // e.g. "text-indigo-600"
  suffix?: string;
}

export default function StatsCard({
  label,
  value,
  change,
  icon: Icon,
  iconBg = 'bg-indigo-100',
  iconColor = 'text-indigo-600',
  suffix,
}: StatsCardProps) {
  const isPositive = (change ?? 0) >= 0;
  const absChange = Math.abs(change ?? 0);

  return (
    <div className="card p-5">
      <div className="flex items-start justify-between mb-4">
        <div className={`w-10 h-10 ${iconBg} rounded-xl flex items-center justify-center`}>
          <Icon size={20} className={iconColor} />
        </div>
        {change !== undefined && <span
          className={`inline-flex items-center gap-1 text-xs font-semibold
            ${isPositive ? 'text-emerald-600' : 'text-red-500'}`}
        >
          {isPositive ? <TrendingUp size={13} /> : <TrendingDown size={13} />}
          {absChange}%
        </span>}
      </div>
      <div>
        <div className="text-2xl font-bold text-slate-900 leading-tight">
          {typeof value === 'number' ? value.toLocaleString() : value}
          {suffix && <span className="text-base font-semibold text-slate-400 ml-1">{suffix}</span>}
        </div>
        <div className="text-sm text-slate-500 mt-0.5">{label}</div>
      </div>
    </div>
  );
}
