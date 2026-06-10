/**
 * History Trends Section (PR4)
 *
 * 历史快照趋势可视化 (5 个 sub-section):
 *   1. Pool Summary - 池子大小趋势线
 *   2. YoY Compare - 同期对比 (VIC YoY)
 *   3. Segment Trend - 13 类 RFM segment 趋势
 *   4. VIP Trend - 5 类 VIP 等级趋势
 *   5. Buyer Timeline - 单买家时间线轨迹
 *
 * 数据源: PR3a + PR3b 5 个 v2 API
 *   GET /api/v2/history/pool-summary
 *   GET /api/v2/history/yoy-compare
 *   GET /api/v2/history/segment-trend
 *   GET /api/v2/history/vip-trend
 *   GET /api/v2/history/buyer-timeline
 */

import React, { useState, useEffect, useMemo } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  Legend, BarChart, Bar, AreaChart, Area
} from 'recharts';
import { History, TrendingUp, TrendingDown, Calendar, User, Search, Loader2 } from 'lucide-react';
import { apiClient } from '../../api/client';
import { LoadingSpinner } from '../common/LoadingState';
import { ErrorAlert } from '../common/ErrorAlert';

// ============ 共享类型 ============

type DateRange = '30d' | '90d' | '180d' | '1y';

const RANGE_DAYS: Record<DateRange, number> = {
  '30d': 30,
  '90d': 90,
  '180d': 180,
  '1y': 365,
};

function todayStr(): string {
  return new Date().toISOString().slice(0, 10);
}

function rangeEnd(range: DateRange): string {
  const d = new Date();
  d.setDate(d.getDate() - 1);  // T-1
  return d.toISOString().slice(0, 10);
}

function rangeStart(range: DateRange): string {
  const days = RANGE_DAYS[range];
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d.toISOString().slice(0, 10);
}

function yoyDates(): { from: string; to: string } {
  // 去年同日 vs 今年同日
  const now = new Date();
  const lastYear = new Date(now);
  lastYear.setFullYear(now.getFullYear() - 1);
  return {
    from: lastYear.toISOString().slice(0, 10),
    to: now.toISOString().slice(0, 10),
  };
}

// ============ DateRangeSelector ============

interface DateRangeSelectorProps {
  value: DateRange;
  onChange: (range: DateRange) => void;
}

function DateRangeSelector({ value, onChange }: DateRangeSelectorProps): React.ReactElement {
  const ranges: Array<{ id: DateRange; label: string }> = [
    { id: '30d', label: '近 30 天' },
    { id: '90d', label: '近 90 天' },
    { id: '180d', label: '近半年' },
    { id: '1y', label: '近 1 年' },
  ];
  return (
    <div className="flex gap-2">
      {ranges.map((r) => (
        <button
          key={r.id}
          onClick={() => onChange(r.id)}
          className={`px-3 py-1.5 text-sm rounded-md transition-colors ${
            value === r.id
              ? 'bg-gray-900 text-white'
              : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50'
          }`}
        >
          {r.label}
        </button>
      ))}
    </div>
  );
}

// ============ 1. PoolSummaryChart ============

function PoolSummaryChart({ dateFrom, dateTo }: { dateFrom: string; dateTo: string }): React.ReactElement {
  const [data, setData] = useState<any[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    apiClient.getHistoryPoolSummary(dateFrom, dateTo)
      .then((res) => { if (!cancelled) setData(res.data); })
      .catch((e: unknown) => { if (!cancelled) setError(e instanceof Error ? e.message : String(e)); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [dateFrom, dateTo]);

  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorAlert message={error} />;
  if (!data || data.length === 0) return <div className="text-gray-500 text-sm">无数据</div>;

  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={data} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis dataKey="snapshot_date" tick={{ fontSize: 11 }} tickFormatter={(v) => v.slice(5)} />
        <YAxis tick={{ fontSize: 11 }} />
        <Tooltip />
        <Legend />
        <Line type="monotone" dataKey="pool_size" name="池子大小" stroke="#6366f1" strokeWidth={2} dot={false} />
        <Line type="monotone" dataKey="vic_count" name="VIC 数" stroke="#10b981" strokeWidth={1.5} dot={false} />
        <Line type="monotone" dataKey="smoker_count" name="Smoker 数" stroke="#f59e0b" strokeWidth={1.5} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}

// ============ 2. YoyCompareCards ============

function YoyCompareCards({ fromDate, toDate }: { fromDate: string; toDate: string }): React.ReactElement {
  const [data, setData] = useState<{ from: any; to: any } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    apiClient.getHistoryYoyCompare(fromDate, toDate)
      .then((res) => {
        if (!cancelled) setData({ from: res.from_data, to: res.to_data });
      })
      .catch((e: unknown) => { if (!cancelled) setError(e instanceof Error ? e.message : String(e)); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [fromDate, toDate]);

  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorAlert message={error} />;
  if (!data || !data.from || !data.to) return <div className="text-gray-500 text-sm">无数据</div>;

  const metrics: Array<{ key: string; label: string; format: (v: number) => string }> = [
    { key: 'pool_size', label: '池子大小', format: (v) => v.toLocaleString() },
    { key: 'vic_count', label: 'VIC 数', format: (v) => v.toLocaleString() },
    { key: 'smoker_count', label: 'Smoker 数', format: (v) => v.toLocaleString() },
    { key: 'total_net_sales', label: '累计净销售', format: (v) => `¥${(v / 10000).toFixed(0)}万` },
    { key: 'rolling_24m_total', label: 'Rolling 24M 净销售', format: (v) => `¥${(v / 10000).toFixed(0)}万` },
  ];

  return (
    <div className="grid grid-cols-2 gap-4">
      {[data.from, data.to].map((d, idx) => (
        <div key={idx} className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="text-xs text-gray-500 mb-3">{idx === 0 ? fromDate : toDate}</div>
          <div className="space-y-2">
            {metrics.map((m) => (
              <div key={m.key} className="flex justify-between items-center">
                <span className="text-sm text-gray-600">{m.label}</span>
                <span className="text-sm font-medium text-gray-900">{m.format(d[m.key] ?? 0)}</span>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

// ============ 3. SegmentTrendChart ============

const SEGMENT_COLORS: Record<string, string> = {
  '重要价值客户': '#6366f1',
  '重要发展客户': '#8b5cf6',
  '重要保持客户': '#ec4899',
  '重要挽留客户': '#f43f5e',
  '优质价值客户': '#10b981',
  '优质发展客户': '#14b8a6',
  '优质保持客户': '#06b6d4',
  '优质挽留客户': '#0ea5e9',
  '潜力客户': '#84cc16',
  '待激活客户': '#eab308',
  '新客户': '#f59e0b',
  '低价值客户': '#f97316',
  '已流失': '#ef4444',
  '无购买记录': '#6b7280',
};

function SegmentTrendChart({
  dateFrom,
  dateTo,
  selectedSegment,
}: {
  dateFrom: string;
  dateTo: string;
  selectedSegment: string | null;
}): React.ReactElement {
  const [data, setData] = useState<any[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    apiClient.getHistorySegmentTrend(dateFrom, dateTo, selectedSegment ?? undefined)
      .then((res) => { if (!cancelled) setData(res.data); })
      .catch((e: unknown) => { if (!cancelled) setError(e instanceof Error ? e.message : String(e)); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [dateFrom, dateTo, selectedSegment]);

  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorAlert message={error} />;
  if (!data || data.length === 0) return <div className="text-gray-500 text-sm">无数据</div>;

  // pivot: snapshot_date -> segment -> count
  const pivoted = useMemo(() => {
    const byDate = new Map<string, Record<string, any>>();
    for (const row of data) {
      if (!byDate.has(row.snapshot_date)) byDate.set(row.snapshot_date, { snapshot_date: row.snapshot_date });
      byDate.get(row.snapshot_date)![row.rfm_segment] = row.customer_count;
    }
    return Array.from(byDate.values()).sort((a, b) => a.snapshot_date.localeCompare(b.snapshot_date));
  }, [data]);

  // 决定渲染哪些 segment
  const segments = useMemo(() => {
    if (selectedSegment) return [selectedSegment];
    return Array.from(new Set(data.map((r) => r.rfm_segment))).sort();
  }, [data, selectedSegment]);

  return (
    <ResponsiveContainer width="100%" height={320}>
      <LineChart data={pivoted} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis dataKey="snapshot_date" tick={{ fontSize: 11 }} tickFormatter={(v) => v.slice(5)} />
        <YAxis tick={{ fontSize: 11 }} />
        <Tooltip />
        <Legend wrapperStyle={{ fontSize: 11 }} />
        {segments.map((seg) => (
          <Line
            key={seg}
            type="monotone"
            dataKey={seg}
            name={seg}
            stroke={SEGMENT_COLORS[seg] ?? '#9ca3af'}
            strokeWidth={selectedSegment ? 2.5 : 1}
            dot={false}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}

// ============ 4. VipTrendChart ============

const VIP_COLORS: Record<string, string> = {
  'V3': '#6366f1',
  'V2': '#8b5cf6',
  'V1': '#a855f7',
  'V0': '#d946ef',
  'Non-VIP': '#6b7280',
};

const VIP_LEVELS = ['V3', 'V2', 'V1', 'V0', 'Non-VIP'];

function VipTrendChart({ dateFrom, dateTo }: { dateFrom: string; dateTo: string }): React.ReactElement {
  const [data, setData] = useState<any[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    apiClient.getHistoryVipTrend(dateFrom, dateTo)
      .then((res) => { if (!cancelled) setData(res.data); })
      .catch((e: unknown) => { if (!cancelled) setError(e instanceof Error ? e.message : String(e)); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [dateFrom, dateTo]);

  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorAlert message={error} />;
  if (!data || data.length === 0) return <div className="text-gray-500 text-sm">无数据</div>;

  // pivot + 按月聚合 (避免 14M 数据点太密)
  const pivoted = useMemo(() => {
    const byMonth = new Map<string, Record<string, any>>();
    for (const row of data) {
      const month = row.snapshot_date.slice(0, 7);  // YYYY-MM
      if (!byMonth.has(month)) {
        const obj: Record<string, any> = { snapshot_date: month };
        for (const lvl of VIP_LEVELS) obj[lvl] = 0;
        byMonth.set(month, obj);
      }
      byMonth.get(month)![row.vip_level] = row.customer_count;
    }
    return Array.from(byMonth.values()).sort((a, b) => a.snapshot_date.localeCompare(b.snapshot_date));
  }, [data]);

  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={pivoted} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis dataKey="snapshot_date" tick={{ fontSize: 11 }} />
        <YAxis tick={{ fontSize: 11 }} />
        <Tooltip />
        <Legend wrapperStyle={{ fontSize: 11 }} />
        {VIP_LEVELS.map((lvl) => (
          <Bar key={lvl} dataKey={lvl} stackId="vip" fill={VIP_COLORS[lvl]} />
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
}

// ============ 5. BuyerTimelineChart ============

function BuyerTimelineChart({
  buyerNick,
  dateFrom,
  dateTo,
}: {
  buyerNick: string;
  dateFrom: string;
  dateTo: string;
}): React.ReactElement {
  const [data, setData] = useState<any[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!buyerNick.trim()) {
      setData(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    apiClient.getHistoryBuyerTimeline(buyerNick, dateFrom, dateTo)
      .then((res) => { if (!cancelled) setData(res.data); })
      .catch((e: unknown) => { if (!cancelled) setError(e instanceof Error ? e.message : String(e)); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [buyerNick, dateFrom, dateTo]);

  if (!buyerNick.trim()) {
    return <div className="text-gray-500 text-sm">输入买家昵称查询时间线</div>;
  }
  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorAlert message={error} />;
  if (!data || data.length === 0) return <div className="text-gray-500 text-sm">该买家无历史数据</div>;

  // 准备 chart data: 用 segment 作为参考线
  const chartData = data.map((r) => ({
    snapshot_date: r.snapshot_date,
    historical_net_sales: Number(r.historical_net_sales),
    rolling_24m_netsales: Number(r.rolling_24m_netsales),
    l6m_netsales: Number(r.l6m_netsales),
    rfm_segment: r.rfm_segment,
    vip_level: r.vip_level,
  }));

  return (
    <div className="space-y-3">
      <div className="text-sm text-gray-600">
        <span className="font-medium">{buyerNick}</span> 跨 {data.length} 个 snapshot
        (最新 segment: <span className="font-medium">{data[data.length - 1]?.rfm_segment}</span>,
        VIP: <span className="font-medium">{data[data.length - 1]?.vip_level}</span>)
      </div>
      <ResponsiveContainer width="100%" height={280}>
        <AreaChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="histGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#6366f1" stopOpacity={0.4} />
              <stop offset="100%" stopColor="#6366f1" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="r24Grad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#10b981" stopOpacity={0.4} />
              <stop offset="100%" stopColor="#10b981" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis dataKey="snapshot_date" tick={{ fontSize: 11 }} tickFormatter={(v) => v.slice(5)} />
          <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `${(v / 10000).toFixed(0)}万`} />
          <Tooltip formatter={(v: number) => `¥${(v / 10000).toFixed(2)}万`} />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          <Area type="monotone" dataKey="historical_net_sales" name="累计净销售" stroke="#6366f1" fill="url(#histGrad)" />
          <Area type="monotone" dataKey="rolling_24m_netsales" name="Rolling 24M" stroke="#10b981" fill="url(#r24Grad)" />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

// ============ 主容器 ============

export const HistoryTrendsSection: React.FC = () => {
  const [dateRange, setDateRange] = useState<DateRange>('90d');
  const [selectedSegment, setSelectedSegment] = useState<string | null>(null);
  const [buyerNick, setBuyerNick] = useState('');

  const dateFrom = rangeStart(dateRange);
  const dateTo = rangeEnd(dateRange);
  const yoy = yoyDates();

  return (
    <section className="bg-white border border-gray-200 rounded-lg p-6 space-y-6">
      {/* 顶部: 标题 + DateRangeSelector */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-2">
          <History className="w-5 h-5 text-indigo-600" />
          <h2 className="text-lg font-semibold text-gray-900">历史快照趋势</h2>
          <span className="text-xs text-gray-500">基于 PR3a + PR3b 5 个 history API</span>
        </div>
        <DateRangeSelector value={dateRange} onChange={setDateRange} />
      </div>

      {/* 1. Pool Summary */}
      <div>
        <h3 className="text-sm font-medium text-gray-700 mb-2 flex items-center gap-1">
          <TrendingUp className="w-4 h-4" /> 池子大小趋势
        </h3>
        <PoolSummaryChart dateFrom={dateFrom} dateTo={dateTo} />
      </div>

      {/* 2. YoY Compare */}
      <div>
        <h3 className="text-sm font-medium text-gray-700 mb-2 flex items-center gap-1">
          <Calendar className="w-4 h-4" /> 同期对比 (去年同日 vs 今年同日)
        </h3>
        <YoyCompareCards fromDate={yoy.from} toDate={yoy.to} />
      </div>

      {/* 3. Segment Trend (含 segment filter) */}
      <div>
        <h3 className="text-sm font-medium text-gray-700 mb-2 flex items-center gap-1">
          <TrendingDown className="w-4 h-4" /> 13 类 RFM Segment 趋势
        </h3>
        <div className="mb-2">
          <select
            value={selectedSegment ?? ''}
            onChange={(e) => setSelectedSegment(e.target.value || null)}
            className="text-sm border border-gray-300 rounded-md px-2 py-1"
          >
            <option value="">全部 13 类</option>
            {Object.keys(SEGMENT_COLORS).map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
          {selectedSegment && (
            <span className="ml-2 text-xs text-indigo-600">当前 filter: {selectedSegment}</span>
          )}
        </div>
        <SegmentTrendChart
          dateFrom={dateFrom}
          dateTo={dateTo}
          selectedSegment={selectedSegment}
        />
      </div>

      {/* 4. VIP Trend (按月聚合 stacked bar) */}
      <div>
        <h3 className="text-sm font-medium text-gray-700 mb-2 flex items-center gap-1">
          <TrendingUp className="w-4 h-4" /> 5 类 VIP 等级趋势 (按月聚合)
        </h3>
        <VipTrendChart dateFrom={dateFrom} dateTo={dateTo} />
      </div>

      {/* 5. Buyer Timeline */}
      <div>
        <h3 className="text-sm font-medium text-gray-700 mb-2 flex items-center gap-1">
          <User className="w-4 h-4" /> 单买家时间线轨迹
        </h3>
        <div className="flex items-center gap-2 mb-3">
          <Search className="w-4 h-4 text-gray-400" />
          <input
            type="text"
            value={buyerNick}
            onChange={(e) => setBuyerNick(e.target.value)}
            placeholder="输入买家昵称 (e.g. 134925792)"
            className="flex-1 text-sm border border-gray-300 rounded-md px-3 py-1.5"
          />
          {buyerNick && (
            <button
              onClick={() => setBuyerNick('')}
              className="text-xs text-gray-500 hover:text-gray-700"
            >
              清除
            </button>
          )}
        </div>
        <BuyerTimelineChart buyerNick={buyerNick} dateFrom={dateFrom} dateTo={dateTo} />
      </div>
    </section>
  );
};
