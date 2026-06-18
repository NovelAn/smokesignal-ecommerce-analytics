import { useEffect, useState } from 'react';
import { CalendarDays } from 'lucide-react';
import { useTimeRange } from '../../hooks/useTimeRange';
import type { TimeRangePreset } from '../../types/insights';

const PRESETS: Array<{ key: Exclude<TimeRangePreset, 'custom'>; label: string }> = [
  { key: '7D', label: '7D' },
  { key: '15D', label: '15D' },
  { key: '1M', label: '1M' },
  { key: '1Q', label: '1Q' },
  { key: '1Y', label: '1Y' },
];

export function TimeRangeFilter() {
  const { timeRange, setPreset, setCustomRange } = useTimeRange();
  const [showCustom, setShowCustom] = useState(timeRange.preset === 'custom');
  const [customStart, setCustomStart] = useState(timeRange.start_date);
  const [customEnd, setCustomEnd] = useState(timeRange.end_date);
  const [compStart, setCompStart] = useState(timeRange.comparison_start_date ?? '');
  const [compEnd, setCompEnd] = useState(timeRange.comparison_end_date ?? '');
  const [validationError, setValidationError] = useState<string | null>(null);

  useEffect(() => {
    setCustomStart(timeRange.start_date);
    setCustomEnd(timeRange.end_date);
    setCompStart(timeRange.comparison_start_date ?? '');
    setCompEnd(timeRange.comparison_end_date ?? '');
  }, [timeRange.comparison_end_date, timeRange.comparison_start_date, timeRange.end_date, timeRange.start_date]);

  const applyCustomRange = () => {
    try {
      setCustomRange(customStart, customEnd, compStart || undefined, compEnd || undefined);
      setValidationError(null);
    } catch (error) {
      setValidationError(error instanceof Error ? error.message : '日期范围无效');
    }
  };

  return (
    <section className="rounded-sm border border-notion-border bg-white shadow-sm">
      <div className="flex flex-col gap-3 px-4 py-3 lg:flex-row lg:items-center">
        <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.14em] text-notion-muted">
          <CalendarDays size={14} />
          趋势与沟通分析周期
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          {PRESETS.map((preset) => (
            <button
              key={preset.key}
              type="button"
              onClick={() => {
                setPreset(preset.key);
                setShowCustom(false);
                setValidationError(null);
              }}
              className={`rounded px-3 py-1.5 text-xs font-medium transition-colors ${
                timeRange.preset === preset.key
                  ? 'bg-notion-text text-white'
                  : 'bg-notion-gray_bg text-notion-muted hover:bg-notion-hover hover:text-notion-text'
              }`}
            >
              {preset.label}
            </button>
          ))}
          <button
            type="button"
            onClick={() => setShowCustom((visible) => !visible)}
            className={`rounded px-3 py-1.5 text-xs font-medium transition-colors ${
              timeRange.preset === 'custom' || showCustom
                ? 'bg-orange-50 text-orange-700 ring-1 ring-orange-200'
                : 'bg-notion-gray_bg text-notion-muted hover:bg-notion-hover hover:text-notion-text'
            }`}
          >
            自定义
          </button>
        </div>
        <div className="text-xs tabular-nums text-notion-muted lg:ml-auto">
          {timeRange.start_date} 至 {timeRange.end_date}
        </div>
      </div>

      {showCustom && (
        <div className="flex flex-wrap items-end gap-x-3 gap-y-2 border-t border-notion-border bg-notion-gray_bg/40 px-4 py-3">
          <span className="text-xs font-semibold uppercase tracking-wider text-notion-text">当期</span>
          <label className="text-xs text-notion-muted">
            <span className="mb-1 block">开始</span>
            <input
              aria-label="当期开始日期"
              type="date"
              value={customStart}
              max={customEnd}
              onChange={(event) => setCustomStart(event.target.value)}
              className="rounded border border-notion-border bg-white px-2.5 py-1.5 text-sm text-notion-text"
            />
          </label>
          <label className="text-xs text-notion-muted">
            <span className="mb-1 block">结束</span>
            <input
              aria-label="当期结束日期"
              type="date"
              value={customEnd}
              min={customStart}
              onChange={(event) => setCustomEnd(event.target.value)}
              className="rounded border border-notion-border bg-white px-2.5 py-1.5 text-sm text-notion-text"
            />
          </label>
          <span className="text-xs font-semibold uppercase tracking-wider text-notion-muted">对比期 <span className="font-normal opacity-70">(可选·留空自动算等长前期)</span></span>
          <label className="text-xs text-notion-muted">
            <span className="mb-1 block">开始</span>
            <input
              aria-label="对比期开始日期"
              type="date"
              value={compStart}
              max={compEnd || undefined}
              onChange={(event) => setCompStart(event.target.value)}
              className="rounded border border-notion-border bg-white px-2.5 py-1.5 text-sm text-notion-text"
            />
          </label>
          <label className="text-xs text-notion-muted">
            <span className="mb-1 block">结束</span>
            <input
              aria-label="对比期结束日期"
              type="date"
              value={compEnd}
              min={compStart || undefined}
              onChange={(event) => setCompEnd(event.target.value)}
              className="rounded border border-notion-border bg-white px-2.5 py-1.5 text-sm text-notion-text"
            />
          </label>
          <button
            type="button"
            onClick={applyCustomRange}
            className="rounded bg-orange-600 px-3 py-2 text-xs font-semibold text-white transition-colors hover:bg-orange-700"
          >
            应用日期
          </button>
          {validationError && <span className="text-xs text-red-600">{validationError}</span>}
        </div>
      )}
    </section>
  );
}
