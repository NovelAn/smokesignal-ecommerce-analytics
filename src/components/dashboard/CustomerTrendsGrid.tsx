import { useEffect, useState } from 'react';
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { Activity, ChartNoAxesCombined } from 'lucide-react';
import { fetchCustomerTrends } from '../../api/insights';
import type { CustomerTrends } from '../../types/insights';
import { ErrorAlert } from '../common/ErrorAlert';
import { LoadingSpinner } from '../common/LoadingState';
import styles from './CustomerTrendsGrid.module.css';

const COLORS = {
  smoker: '#b89c7d',
  vic: '#5b7ea6',
  both: '#587c6b',
  active: '#5b7ea6',
  risk: '#c65d50',
  positive: '#6f967f',
  neutral: '#9ca3af',
  negative: '#c65d50',
};

export function CustomerTrendsGrid() {
  const [data, setData] = useState<CustomerTrends | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    fetchCustomerTrends(6, controller.signal)
      .then(setData)
      .catch((requestError) => {
        if (requestError?.name !== 'AbortError') {
          setError(requestError instanceof Error ? requestError.message : '趋势数据加载失败');
        }
      })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, []);

  if (loading) return <section className={styles.chartCard}><LoadingSpinner /></section>;
  if (error) return <section className={styles.chartCard}><ErrorAlert message={error} /></section>;
  if (!data) return null;

  return (
    <section>
      <div className="mb-4 flex items-end justify-between">
        <div>
          <h2 className="flex items-center gap-2 text-lg font-semibold text-notion-text"><ChartNoAxesCombined size={18} />客户趋势</h2>
          <p className="mt-1 text-xs text-notion-muted">近 6 个月客户池、活跃度与风险变化</p>
        </div>
      </div>
      <div className={styles.grid} data-testid="customer-trends-grid">
        <ChartCard title="VIC 客户池规模趋势">
          <ResponsiveContainer width="100%" height={250}>
            <AreaChart data={data.vic_pool_trend}>
              <CartesianGrid stroke="#eeece8" strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="month" tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 11 }} axisLine={false} tickLine={false} width={34} />
              <Tooltip />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Area dataKey="SMOKER" stackId="pool" stroke={COLORS.smoker} fill={COLORS.smoker} fillOpacity={0.55} />
              <Area dataKey="VIC" stackId="pool" stroke={COLORS.vic} fill={COLORS.vic} fillOpacity={0.55} />
              <Area dataKey="BOTH" stackId="pool" stroke={COLORS.both} fill={COLORS.both} fillOpacity={0.65} />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="VIC 活跃率趋势">
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={data.vic_active_rate_trend}>
              <CartesianGrid stroke="#eeece8" strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="month" tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis domain={[0, 100]} tickFormatter={(value) => `${value}%`} tick={{ fontSize: 11 }} axisLine={false} tickLine={false} width={42} />
              <Tooltip formatter={(value) => [`${Number(value).toFixed(1)}%`, '活跃率']} />
              <Line dataKey="active_rate" name="活跃率" stroke={COLORS.active} strokeWidth={2.5} dot={{ r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="高风险客户数量趋势">
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={data.high_risk_trend}>
              <CartesianGrid stroke="#eeece8" strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="month" tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis allowDecimals={false} tick={{ fontSize: 11 }} axisLine={false} tickLine={false} width={34} />
              <Tooltip />
              <Line dataKey="high_risk_count" name="高风险客户" stroke={COLORS.risk} strokeWidth={2.5} dot={{ r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="情感健康度趋势">
          {data.sentiment_trend.length === 0 ? (
            <div className="flex h-[250px] flex-col items-center justify-center rounded border border-dashed border-notion-border bg-notion-gray_bg/30 text-center">
              <Activity size={22} className="mb-2 text-notion-muted" />
              <p className="text-sm font-medium text-notion-text">情感趋势暂无可用数据</p>
              <p className="mt-1 max-w-xs text-xs text-notion-muted">历史快照暂未包含情感字段，数据接入后图表会自动展示。</p>
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={data.sentiment_trend}>
                <CartesianGrid stroke="#eeece8" strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="month" tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 11 }} axisLine={false} tickLine={false} width={34} />
                <Tooltip />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Bar dataKey="Positive" stackId="sentiment" fill={COLORS.positive} />
                <Bar dataKey="Neutral" stackId="sentiment" fill={COLORS.neutral} />
                <Bar dataKey="Negative" stackId="sentiment" fill={COLORS.negative} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </ChartCard>
      </div>
    </section>
  );
}

function ChartCard({ title, children }: { title: string; children: React.ReactNode }) {
  return <article className={styles.chartCard}><h3 className={styles.chartTitle}>{title}</h3>{children}</article>;
}
