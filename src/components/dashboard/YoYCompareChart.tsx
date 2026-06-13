/**
 * YoY 对比图 (CRM Round 1)
 *
 * 替换 HistoryTrendsSection.
 * 双色双线: 今年(蓝) + 去年同期/自定义对比期(灰).
 * 支持自定义日期区间 + YoY/MoM/自定义 对比模式.
 */

import React, { useState, useEffect, useMemo } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { Calendar, TrendingUp, TrendingDown } from 'lucide-react';
import { apiClient } from '../../api/client';
import { LoadingSpinner } from '../common/LoadingState';
import { ErrorAlert } from '../common/ErrorAlert';

type CompareMode = 'yoy' | 'mom' | 'custom';

interface SummaryCard {
  label: string;
  current: number;
  previous: number;
  changePct: number;
  format: (v: number) => string;
}

function YoYCompareChart(): React.ReactElement {
  const today = new Date().toISOString().slice(0, 10);
  const yearAgo = new Date(Date.now() - 365 * 86400000).toISOString().slice(0, 10);

  const [mode, setMode] = useState<CompareMode>('yoy');
  const [fromDate, setFromDate] = useState(yearAgo);
  const [toDate, setToDate] = useState(today);
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    apiClient.getHistoryYoyCompare(fromDate, toDate)
      .then((res) => { if (!cancelled) setData(res); })
      .catch((e: unknown) => { if (!cancelled) setError(e instanceof Error ? e.message : String(e)); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [fromDate, toDate]);

  const summaries = useMemo<SummaryCard[]>(() => {
    if (!data?.from_data || !data?.to_data) return [];
    const f = data.from_data;
    const t = data.to_data;
    const pct = (v1: number, v2: number) => v2 === 0 ? 0 : ((v1 - v2) / v2 * 100);
    return [
      { label: '池子大小', current: t.pool_size, previous: f.pool_size, changePct: pct(t.pool_size, f.pool_size), format: (v) => v.toLocaleString() },
      { label: 'VIC 数', current: t.vic_count, previous: f.vic_count, changePct: pct(t.vic_count, f.vic_count), format: (v) => v.toLocaleString() },
      { label: '累计净销售', current: t.total_net_sales, previous: f.total_net_sales, changePct: pct(t.total_net_sales, f.total_net_sales), format: (v) => `¥${(v / 10000).toFixed(0)}万` },
      { label: 'Rolling 24M', current: t.rolling_24m_total, previous: f.rolling_24m_total, changePct: pct(t.rolling_24m_total, f.rolling_24m_total), format: (v) => `¥${(v / 10000).toFixed(0)}万` },
    ];
  }, [data]);

  const handleModeChange = (m: CompareMode) => {
    setMode(m);
    const now = new Date();
    if (m === 'yoy') {
      setFromDate(new Date(now.getFullYear() - 1, now.getMonth(), now.getDate()).toISOString().slice(0, 10));
      setToDate(now.toISOString().slice(0, 10));
    } else if (m === 'mom') {
      setFromDate(new Date(now.getFullYear(), now.getMonth() - 1, now.getDate()).toISOString().slice(0, 10));
      setToDate(now.toISOString().slice(0, 10));
    }
    // custom: keep current dates
  };

  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorAlert message={error} />;

  return (
    <section className="bg-white border border-gray-200 rounded-lg p-6 space-y-4">
      {/* 标题 + 日期选择 */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-2">
          <Calendar className="w-5 h-5 text-indigo-600" />
          <h2 className="text-lg font-semibold text-gray-900">同期对比分析</h2>
        </div>
        <div className="flex items-center gap-2">
          {/* 对比模式 */}
          <select value={mode} onChange={(e) => handleModeChange(e.target.value as CompareMode)}
            className="text-sm border border-gray-300 rounded-md px-2 py-1">
            <option value="yoy">去年同期</option>
            <option value="mom">上月同期</option>
            <option value="custom">自定义</option>
          </select>
          {/* 日期选择器 */}
          <input type="date" value={fromDate} onChange={(e) => { setMode('custom'); setFromDate(e.target.value); }}
            className="text-sm border border-gray-300 rounded-md px-2 py-1" />
          <span className="text-gray-400">~</span>
          <input type="date" value={toDate} onChange={(e) => { setMode('custom'); setToDate(e.target.value); }}
            className="text-sm border border-gray-300 rounded-md px-2 py-1" />
        </div>
      </div>

      {/* 4 个总结卡 */}
      {summaries.length > 0 && (
        <div className="grid grid-cols-4 gap-3">
          {summaries.map((s) => (
            <div key={s.label} className="bg-gray-50 rounded-lg p-3 text-center">
              <div className="text-xs text-gray-500">{s.label}</div>
              <div className="text-lg font-semibold text-gray-900 mt-0.5">{s.format(s.current)}</div>
              <div className={`flex items-center justify-center gap-1 text-xs mt-0.5 ${s.changePct >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {s.changePct >= 0 ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                {s.changePct >= 0 ? '+' : ''}{s.changePct.toFixed(1)}%
                <span className="text-gray-400 ml-1">vs {fromDate}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 图表区 (简单双线, 用 yoy-compare 数据) */}
      {data?.from_data && data?.to_data && (
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={[
            { name: fromDate, pool: data.from_data.pool_size, vic: data.from_data.vic_count, smoker: data.from_data.smoker_count, net: data.from_data.total_net_sales / 10000 },
            { name: toDate, pool: data.to_data.pool_size, vic: data.to_data.vic_count, smoker: data.to_data.smoker_count, net: data.to_data.total_net_sales / 10000 },
          ]} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis dataKey="name" tick={{ fontSize: 12 }} />
            <YAxis yAxisId="left" tick={{ fontSize: 11 }} />
            <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11 }} tickFormatter={(v) => `${v}万`} />
            <Tooltip />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            <Line yAxisId="left" type="monotone" dataKey="pool" name="池子大小" stroke="#6366f1" strokeWidth={2} />
            <Line yAxisId="left" type="monotone" dataKey="vic" name="VIC 数" stroke="#10b981" strokeWidth={2} />
            <Line yAxisId="right" type="monotone" dataKey="net" name="净销售(万)" stroke="#f59e0b" strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      )}
    </section>
  );
}

export { YoYCompareChart };
