import { useEffect, useState } from 'react';
import { GitCompareArrows } from 'lucide-react';
import { fetchPeriodComparison } from '../../api/insights';
import { useTimeRange } from '../../hooks/useTimeRange';
import type { PeriodComparison } from '../../types/insights';
import { ErrorAlert } from '../common/ErrorAlert';
import { LoadingSpinner } from '../common/LoadingState';
import { MetricCard } from './MetricCard';

const METRIC_LABELS = {
  new_vic: { title: '新增 VIC', subtitle: '本周期新晋 VIC 客户' },
  churn_warning: { title: '流失预警', subtitle: '新增高风险客户' },
  vip_upgrades: { title: 'VIP 升级', subtitle: '发生等级跃迁的客户' },
  sentiment_negative: { title: '情感转负', subtitle: '情感状态转为负向' },
} as const;

export function PeriodComparisonCard() {
  const { timeRange } = useTimeRange();
  const [data, setData] = useState<PeriodComparison | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    fetchPeriodComparison(
      timeRange.start_date,
      timeRange.end_date,
      timeRange.comparison_start_date,
      timeRange.comparison_end_date,
      controller.signal,
    )
      .then(setData)
      .catch((requestError) => {
        if (requestError?.name !== 'AbortError') {
          setError(requestError instanceof Error ? requestError.message : '时间对比加载失败');
        }
      })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, [timeRange.end_date, timeRange.start_date]);

  return (
    <section className="rounded-sm border border-notion-border bg-notion-gray_bg/30 p-5 shadow-sm">
      <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="flex items-center gap-2 text-lg font-semibold text-notion-text"><GitCompareArrows size={18} />时间对比摘要</h2>
          <p className="mt-1 text-xs text-notion-muted">同等时长的前一周期作为比较基线</p>
        </div>
        {data && (
          <div className="text-right text-xs tabular-nums text-notion-muted">
            <div>{data.current_period.start_date} 至 {data.current_period.end_date}</div>
            <div className="mt-0.5 opacity-70">对比 {data.comparison_period.start_date} 至 {data.comparison_period.end_date}</div>
          </div>
        )}
      </div>
      {loading && <LoadingSpinner />}
      {error && <ErrorAlert message={error} />}
      {!loading && !error && data && (
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {(Object.keys(METRIC_LABELS) as Array<keyof typeof METRIC_LABELS>).map((key) => (
            <MetricCard
              key={key}
              title={METRIC_LABELS[key].title}
              subtitle={METRIC_LABELS[key].subtitle}
              value={data.metrics[key].current}
              change={data.metrics[key].change}
              changePct={data.metrics[key].change_pct}
            />
          ))}
        </div>
      )}
    </section>
  );
}
