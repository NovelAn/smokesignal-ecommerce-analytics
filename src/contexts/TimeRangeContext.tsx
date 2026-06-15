import { createContext, useCallback, useMemo, useState, type ReactNode } from 'react';
import { format, startOfQuarter, startOfYear, subDays, subMonths } from 'date-fns';
import type { TimeRange, TimeRangePreset } from '../types/insights';

interface TimeRangeContextValue {
  timeRange: TimeRange;
  setPreset: (preset: Exclude<TimeRangePreset, 'custom'>) => void;
  setCustomRange: (start: string, end: string, compStart?: string, compEnd?: string) => void;
}

export const TimeRangeContext = createContext<TimeRangeContextValue | null>(null);

const DATE_FORMAT = 'yyyy-MM-dd';

function calculateRange(preset: Exclude<TimeRangePreset, 'custom'>, now = new Date()): TimeRange {
  let start: Date;
  switch (preset) {
    case '7D':
      start = subDays(now, 7);
      break;
    case '15D':
      start = subDays(now, 15);
      break;
    case '1Q':
      start = startOfQuarter(now);
      break;
    case '1Y':
      start = startOfYear(now);
      break;
    case '1M':
    default:
      start = subMonths(now, 1);
  }

  return {
    start_date: format(start, DATE_FORMAT),
    end_date: format(now, DATE_FORMAT),
    preset,
  };
}

export function TimeRangeProvider({ children }: { children: ReactNode }) {
  const [timeRange, setTimeRange] = useState<TimeRange>(() => calculateRange('1M'));

  const setPreset = useCallback((preset: Exclude<TimeRangePreset, 'custom'>) => {
    setTimeRange(calculateRange(preset));
  }, []);

  const setCustomRange = useCallback(
    (start: string, end: string, compStart?: string, compEnd?: string) => {
      if (!start || !end || start > end) {
        throw new Error('开始日期不能晚于结束日期');
      }
      if (compStart && compEnd && compStart > compEnd) {
        throw new Error('对比期开始日期不能晚于结束日期');
      }
      setTimeRange({
        start_date: start,
        end_date: end,
        preset: 'custom',
        comparison_start_date: compStart || null,
        comparison_end_date: compEnd || null,
      });
    },
    [],
  );

  const value = useMemo(
    () => ({ timeRange, setPreset, setCustomRange }),
    [setCustomRange, setPreset, timeRange],
  );

  return <TimeRangeContext.Provider value={value}>{children}</TimeRangeContext.Provider>;
}
