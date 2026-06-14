import type { ReactNode } from 'react';
import { ArrowDownRight, ArrowUpRight, Minus } from 'lucide-react';

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  change?: number;
  changePct?: number;
  icon?: ReactNode;
}

export function MetricCard({ title, value, subtitle, change, changePct, icon }: MetricCardProps) {
  const direction = Math.sign(change ?? 0);
  const ChangeIcon = direction > 0 ? ArrowUpRight : direction < 0 ? ArrowDownRight : Minus;
  const changeColor = direction > 0 ? 'text-emerald-700' : direction < 0 ? 'text-red-700' : 'text-notion-muted';

  return (
    <article className="rounded-sm border border-notion-border bg-white p-4 shadow-sm">
      <div className="mb-3 flex items-center justify-between gap-3">
        <h3 className="text-xs font-semibold uppercase tracking-[0.12em] text-notion-muted">{title}</h3>
        {icon && <div className="text-notion-muted">{icon}</div>}
      </div>
      <div className="flex items-end justify-between gap-3">
        <strong className="font-serif text-3xl font-medium leading-none text-notion-text">{value}</strong>
        {change !== undefined && (
          <span className={`inline-flex items-center gap-1 text-xs font-medium tabular-nums ${changeColor}`}>
            <ChangeIcon size={13} />
            {Math.abs(change)}
            {changePct !== undefined && ` (${Math.abs(changePct).toFixed(1)}%)`}
          </span>
        )}
      </div>
      {subtitle && <p className="mt-2 text-xs text-notion-muted">{subtitle}</p>}
    </article>
  );
}
