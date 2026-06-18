# Overview 页面改造 - 前端实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实施 Overview 页面前端重构：全局时间筛选器、双 tab 布局（趋势概览 + 行动看板）、5 个新组件（VIC 群体画像、时间对比、客户趋势网格、异常预警、库存需求）。

**Architecture:**
- 使用 React Context 管理全局时间筛选器状态，所有依赖时间的组件通过 `useTimeRange()` hook 消费
- 双 tab 结构：Tab 1（趋势概览）放分析卡片和趋势图表，Tab 2（行动看板）放预警和库存需求
- 并行 fetch 5 个 API（vic-persona、period-comparison、customer-trends、anomaly-alerts、inventory-inquiries）
- Recharts 绘制 4 个趋势图表（堆叠面积、折线、堆叠柱状）
- 保留现有 4-Group 指标卡片、Keyword & Issue Analysis（扩展 10 大类）、Priority List

**Tech Stack:**
- React 19 + TypeScript + Vite 6 + Recharts 3.6 + Tailwind CSS
- React Context API（时间筛选器全局状态）
- fetch API（5 个并行请求）

**依赖：**
- 后端 5 个 API 端点已完成（见 `2026-06-14-overview-redesign-implementation.md`）
- Phase 2 Inventory Inquiry Intent 已上线（库存需求组件需 1-2 周数据积累后才有数据）

---

## 文件结构

### 新建文件

- `src/contexts/TimeRangeContext.tsx` - 全局时间筛选器 Context
- `src/hooks/useTimeRange.ts` - 消费 TimeRangeContext 的 hook
- `src/types/insights.ts` - 5 个新 API 的 TypeScript 类型定义
- `src/api/insights.ts` - 5 个新 API 的 fetch 封装
- `src/components/common/TimeRangeFilter.tsx` - 时间筛选器 UI 组件
- `src/components/dashboard/VicPersonaCard.tsx` - VIC 群体画像卡片
- `src/components/dashboard/PeriodComparisonCard.tsx` - 时间对比摘要卡片
- `src/components/dashboard/CustomerTrendsGrid.tsx` - 4 个趋势图表 2x2 网格
- `src/components/dashboard/CustomerTrendsGrid.module.css` - 趋势图表样式
- `src/components/dashboard/AnomalyAlertsCard.tsx` - 异常客户预警卡片
- `src/components/dashboard/InventoryInquiriesCard.tsx` - 库存需求列表卡片
- `src/components/dashboard/MetricCard.tsx` - 通用指标卡片子组件
- `tests/components/TimeRangeFilter.test.tsx` - 时间筛选器测试
- `tests/api/insights.test.ts` - API 封装测试

### 修改文件

- `src/views/DashboardOverview.tsx` - 完全重构为双 tab 布局
- `src/components/dashboard/KeywordAnalysisPanel.tsx` - 加入第 10 类「库存查询」配置
- `src/App.tsx` - 在 App 根部包裹 TimeRangeProvider
- `src/main.tsx` - 引入 TimeRangeContext（如果需要）
- `package.json` - 添加 date-fns 依赖（时间范围计算）

---

## Task 1: 安装时间处理依赖

**Files:**
- Modify: `package.json`

- [ ] **Step 1: 安装 date-fns**

Run: `npm install date-fns`

Expected: package.json 增加 `"date-fns": "^3.x.x"`

- [ ] **Step 2: 验证安装**

Run: `npm list date-fns`

Expected: 输出 date-fns@x.x.x

---

## Task 2: 定义 TypeScript 类型

**Files:**
- Create: `src/types/insights.ts`

- [ ] **Step 1: 创建类型定义文件**

Create `src/types/insights.ts`:

```typescript
// 5 个新 API 的 TypeScript 类型定义

export interface KeywordItem {
  keyword: string;
  count: number;
  percentage: number;
}

export interface MotivationItem {
  pattern: string;
  count: number;
}

export interface VicPersona {
  total_vic_count: number;
  key_interests: KeywordItem[];
  key_pain_points: KeywordItem[];
  purchase_motivations: MotivationItem[];
}

export interface PeriodMetric {
  current: number;
  previous: number;
  change: number;
  change_pct: number;
}

export interface PeriodComparison {
  current_period: { start_date: string; end_date: string };
  comparison_period: { start_date: string; end_date: string };
  metrics: {
    new_vic: PeriodMetric;
    churn_warning: PeriodMetric;
    vip_upgrades: PeriodMetric;
    sentiment_negative: PeriodMetric;
  };
}

export interface Anomaly {
  buyer_nick: string;
  vip_level: string;
  anomaly_type: string;
  anomaly_reason: string;
  last_purchase_date: string | null;
  last_chat_date: string | null;
  severity: 'high' | 'medium' | 'low';
}

export interface AnomalyAlerts {
  anomalies: Anomaly[];
  total_count: number;
}

export interface VicPoolTrendPoint {
  month: string;
  SMOKER: number;
  VIC: number;
  BOTH: number;
}

export interface ActiveRateTrendPoint {
  month: string;
  total_vic: number;
  active_vic: number;
  active_rate: number;
}

export interface HighRiskTrendPoint {
  month: string;
  high_risk_count: number;
}

export interface SentimentTrendPoint {
  month: string;
  Positive: number;
  Neutral: number;
  Negative: number;
}

export interface CustomerTrends {
  vic_pool_trend: VicPoolTrendPoint[];
  vic_active_rate_trend: ActiveRateTrendPoint[];
  high_risk_trend: HighRiskTrendPoint[];
  sentiment_trend: SentimentTrendPoint[];
}

export interface InventoryInquiry {
  buyer_nick: string;
  vip_level: string;
  dominant_intent: string;
  intent_distribution: Record<string, number>;
  sentiment_label: string;
  last_chat_date: string | null;
  total_chat_messages: number;
}

export interface InventoryInquiries {
  inquiries: InventoryInquiry[];
  total_count: number;
}

export type TimeRangePreset = '7D' | '15D' | '1M' | '1Q' | '1Y' | 'custom';

export interface TimeRange {
  start_date: string; // ISO date
  end_date: string;
  preset: TimeRangePreset;
}
```

- [ ] **Step 2: 验证 TypeScript 编译**

Run: `npx tsc --noEmit --pretty false src/types/insights.ts`

Expected: 无错误

---

## Task 3: 封装 5 个 API

**Files:**
- Create: `src/api/insights.ts`

- [ ] **Step 1: 创建 API 封装文件**

Create `src/api/insights.ts`:

```typescript
import type {
  VicPersona,
  PeriodComparison,
  AnomalyAlerts,
  CustomerTrends,
  InventoryInquiries,
} from '../types/insights';

const API_BASE = '/api/v2';

async function fetchJson<T>(url: string, errorPrefix: string): Promise<T> {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`${errorPrefix}: ${response.status} ${response.statusText}`);
  }
  return response.json();
}

export async function fetchVicPersona(): Promise<VicPersona> {
  return fetchJson<VicPersona>(`${API_BASE}/insights/vic-persona`, 'VIC 群体画像查询失败');
}

export async function fetchPeriodComparison(
  startDate: string,
  endDate: string,
): Promise<PeriodComparison> {
  const url = `${API_BASE}/insights/period-comparison?start_date=${startDate}&end_date=${endDate}`;
  return fetchJson<PeriodComparison>(url, '时间对比查询失败');
}

export async function fetchAnomalyAlerts(): Promise<AnomalyAlerts> {
  return fetchJson<AnomalyAlerts>(`${API_BASE}/insights/anomaly-alerts`, '异常客户查询失败');
}

export async function fetchCustomerTrends(months: number = 6): Promise<CustomerTrends> {
  return fetchJson<CustomerTrends>(
    `${API_BASE}/insights/customer-trends?months=${months}`,
    '趋势数据查询失败',
  );
}

export async function fetchInventoryInquiries(): Promise<InventoryInquiries> {
  return fetchJson<InventoryInquiries>(
    `${API_BASE}/action/inventory-inquiries`,
    '库存需求查询失败',
  );
}

export async function fetchDashboardOverview(
  startDate: string,
  endDate: string,
): Promise<{
  vicPersona: VicPersona;
  periodComparison: PeriodComparison;
  anomalyAlerts: AnomalyAlerts;
  customerTrends: CustomerTrends;
  inventoryInquiries: InventoryInquiries;
}> {
  // 并行获取 5 个 API
  const [vicPersona, periodComparison, anomalyAlerts, customerTrends, inventoryInquiries] =
    await Promise.all([
      fetchVicPersona(),
      fetchPeriodComparison(startDate, endDate),
      fetchAnomalyAlerts(),
      fetchCustomerTrends(6),
      fetchInventoryInquiries(),
    ]);

  return { vicPersona, periodComparison, anomalyAlerts, customerTrends, inventoryInquiries };
}
```

- [ ] **Step 2: 验证 TypeScript 编译**

Run: `npx tsc --noEmit --pretty false src/api/insights.ts`

Expected: 无错误

---

## Task 4: TimeRange Context

**Files:**
- Create: `src/contexts/TimeRangeContext.tsx`
- Create: `src/hooks/useTimeRange.ts`

- [ ] **Step 1: 创建 Context**

Create `src/contexts/TimeRangeContext.tsx`:

```tsx
import { createContext, useState, useMemo, ReactNode } from 'react';
import { subDays, subMonths, startOfQuarter, startOfYear, format } from 'date-fns';
import type { TimeRange, TimeRangePreset } from '../types/insights';

interface TimeRangeContextValue {
  timeRange: TimeRange;
  setPreset: (preset: TimeRangePreset) => void;
  setCustomRange: (start: string, end: string) => void;
}

export const TimeRangeContext = createContext<TimeRangeContextValue | null>(null);

function calculateRange(preset: TimeRangePreset): { start: string; end: string } {
  const end = new Date();
  const today = format(end, 'yyyy-MM-dd');
  let start: Date;

  switch (preset) {
    case '7D':
      start = subDays(end, 7);
      break;
    case '15D':
      start = subDays(end, 15);
      break;
    case '1M':
      start = subMonths(end, 1);
      break;
    case '1Q':
      start = startOfQuarter(end);
      break;
    case '1Y':
      start = startOfYear(end);
      break;
    default:
      start = subMonths(end, 1);
  }

  return { start: format(start, 'yyyy-MM-dd'), end: today };
}

export function TimeRangeProvider({ children }: { children: ReactNode }) {
  const [preset, setPresetState] = useState<TimeRangePreset>('1M');

  const timeRange = useMemo<TimeRange>(() => {
    const { start, end } = calculateRange(preset);
    return { start_date: start, end_date: end, preset };
  }, [preset]);

  const value = useMemo<TimeRangeContextValue>(
    () => ({
      timeRange,
      setPreset: (p) => setPresetState(p),
      setCustomRange: (start, end) =>
        setPresetState('custom'),
    }),
    [timeRange],
  );

  return <TimeRangeContext.Provider value={value}>{children}</TimeRangeContext.Provider>;
}
```

- [ ] **Step 2: 创建 useTimeRange hook**

Create `src/hooks/useTimeRange.ts`:

```typescript
import { useContext } from 'react';
import { TimeRangeContext } from '../contexts/TimeRangeContext';

export function useTimeRange() {
  const ctx = useContext(TimeRangeContext);
  if (!ctx) {
    throw new Error('useTimeRange must be used within TimeRangeProvider');
  }
  return ctx;
}
```

- [ ] **Step 3: 在 App.tsx 包裹 Provider**

读取 `src/App.tsx`，在最外层组件包裹：

```tsx
import { TimeRangeProvider } from './contexts/TimeRangeContext';

function App() {
  return (
    <TimeRangeProvider>
      {/* 现有 JSX */}
    </TimeRangeProvider>
  );
}
```

- [ ] **Step 4: 验证 TypeScript 编译**

Run: `npx tsc --noEmit --pretty false`

Expected: 无错误

---

## Task 5: TimeRangeFilter 组件

**Files:**
- Create: `src/components/common/TimeRangeFilter.tsx`

- [ ] **Step 1: 创建组件**

Create `src/components/common/TimeRangeFilter.tsx`:

```tsx
import { useState } from 'react';
import { useTimeRange } from '../../hooks/useTimeRange';
import type { TimeRangePreset } from '../../types/insights';

const PRESETS: { key: TimeRangePreset; label: string }[] = [
  { key: '7D', label: '7D' },
  { key: '15D', label: '15D' },
  { key: '1M', label: '1M' },
  { key: '1Q', label: '1Q' },
  { key: '1Y', label: '1Y' },
  { key: 'custom', label: '自定义' },
];

export function TimeRangeFilter() {
  const { timeRange, setPreset, setCustomRange } = useTimeRange();
  const [showCustom, setShowCustom] = useState(false);
  const [customStart, setCustomStart] = useState(timeRange.start_date);
  const [customEnd, setCustomEnd] = useState(timeRange.end_date);

  return (
    <div className="flex items-center gap-2 p-4 bg-white border-b">
      <span className="text-sm text-gray-600 mr-2">时间范围:</span>
      {PRESETS.map((p) => (
        <button
          key={p.key}
          onClick={() => {
            setPreset(p.key);
            setShowCustom(p.key === 'custom');
          }}
          className={`px-3 py-1 text-sm rounded ${
            timeRange.preset === p.key
              ? 'bg-blue-500 text-white'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
        >
          {p.label}
        </button>
      ))}

      {showCustom && (
        <div className="flex items-center gap-2 ml-4">
          <input
            type="date"
            value={customStart}
            onChange={(e) => setCustomStart(e.target.value)}
            className="px-2 py-1 text-sm border rounded"
          />
          <span className="text-gray-500">~</span>
          <input
            type="date"
            value={customEnd}
            onChange={(e) => setCustomEnd(e.target.value)}
            className="px-2 py-1 text-sm border rounded"
          />
          <button
            onClick={() => setCustomRange(customStart, customEnd)}
            className="px-3 py-1 text-sm bg-blue-500 text-white rounded"
          >
            应用
          </button>
        </div>
      )}

      <div className="ml-auto text-sm text-gray-500">
        {timeRange.start_date} ~ {timeRange.end_date}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: 验证编译 + 浏览器测试**

Run: `npx tsc --noEmit --pretty false`
Run: `npm run dev`

浏览器打开 http://localhost:3000，验证：
- 顶部出现 5 个预设按钮 + 自定义
- 点击按钮会高亮
- 当前时间段显示在右侧

---

## Task 6: MetricCard 子组件

**Files:**
- Create: `src/components/dashboard/MetricCard.tsx`

- [ ] **Step 1: 创建通用指标卡片**

Create `src/components/dashboard/MetricCard.tsx`:

```tsx
import { ReactNode } from 'react';

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  change?: number; // 变化量
  changePct?: number; // 变化百分比
  icon?: ReactNode;
  children?: ReactNode;
}

export function MetricCard({ title, value, subtitle, change, changePct, icon, children }: MetricCardProps) {
  const showChange = change !== undefined && change !== 0;
  const isPositive = (change ?? 0) > 0;

  return (
    <div className="bg-white rounded-lg shadow-sm p-4 border">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm text-gray-600">{title}</h3>
        {icon && <div className="text-gray-400">{icon}</div>}
      </div>
      <div className="flex items-baseline gap-2">
        <div className="text-2xl font-semibold text-gray-900">{value}</div>
        {showChange && (
          <span className={`text-sm ${isPositive ? 'text-green-600' : 'text-red-600'}`}>
            {isPositive ? '↑' : '↓'} {Math.abs(change)} ({changePct?.toFixed(1)}%)
          </span>
        )}
      </div>
      {subtitle && <div className="text-xs text-gray-500 mt-1">{subtitle}</div>}
      {children && <div className="mt-3">{children}</div>}
    </div>
  );
}
```

---

## Task 7: VicPersonaCard 组件

**Files:**
- Create: `src/components/dashboard/VicPersonaCard.tsx`

- [ ] **Step 1: 创建组件**

Create `src/components/dashboard/VicPersonaCard.tsx`:

```tsx
import { useEffect, useState } from 'react';
import { fetchVicPersona } from '../../api/insights';
import type { VicPersona } from '../../types/insights';

export function VicPersonaCard() {
  const [data, setData] = useState<VicPersona | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchVicPersona()
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="bg-white rounded-lg p-6 shadow-sm">加载中...</div>;
  if (error) return <div className="bg-red-50 text-red-700 p-4 rounded">错误: {error}</div>;
  if (!data) return null;

  return (
    <div className="bg-white rounded-lg shadow-sm p-6 border">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">
        VIC 群体画像 ({data.total_vic_count} 人)
      </h2>

      <div className="space-y-4">
        <Section title="关键兴趣特征" items={data.key_interests} renderKey={(i) => i.keyword} renderMeta={(i) => `${i.count} 人 (${i.percentage}%)`} />
        <Section title="关键痛点特征" items={data.key_pain_points} renderKey={(i) => i.keyword} renderMeta={(i) => `${i.count} 人 (${i.percentage}%)`} />
        <Section title="主流购买动机" items={data.purchase_motivations} renderKey={(i) => i.pattern} renderMeta={(i) => `${i.count} 人`} />
      </div>
    </div>
  );
}

interface SectionProps<T> {
  title: string;
  items: T[];
  renderKey: (item: T) => string;
  renderMeta: (item: T) => string;
}

function Section<T>({ title, items, renderKey, renderMeta }: SectionProps<T>) {
  return (
    <div>
      <h3 className="text-sm font-medium text-gray-700 mb-2">{title}</h3>
      {items.length === 0 ? (
        <div className="text-sm text-gray-400">数据不足</div>
      ) : (
        <div className="flex flex-wrap gap-2">
          {items.map((item, idx) => (
            <span
              key={idx}
              className="inline-flex items-center gap-1 px-3 py-1 bg-blue-50 text-blue-700 rounded-full text-sm"
            >
              {renderKey(item)}
              <span className="text-xs text-blue-500">({renderMeta(item)})</span>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
```

---

## Task 8: PeriodComparisonCard 组件

**Files:**
- Create: `src/components/dashboard/PeriodComparisonCard.tsx`

- [ ] **Step 1: 创建组件**

Create `src/components/dashboard/PeriodComparisonCard.tsx`:

```tsx
import { useEffect, useState } from 'react';
import { fetchPeriodComparison } from '../../api/insights';
import { useTimeRange } from '../../hooks/useTimeRange';
import type { PeriodComparison } from '../../types/insights';
import { MetricCard } from './MetricCard';

const METRIC_LABELS: Record<string, { title: string; subtitle: string }> = {
  new_vic: { title: '新增 VIC', subtitle: '新晋 VIC 客户' },
  churn_warning: { title: '流失预警', subtitle: '高流失风险客户' },
  vip_upgrades: { title: 'VIP 升级', subtitle: 'VIP 等级变化' },
  sentiment_negative: { title: '情感转负', subtitle: 'Positive → Negative' },
};

export function PeriodComparisonCard() {
  const { timeRange } = useTimeRange();
  const [data, setData] = useState<PeriodComparison | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetchPeriodComparison(timeRange.start_date, timeRange.end_date)
      .then(setData)
      .finally(() => setLoading(false));
  }, [timeRange.start_date, timeRange.end_date]);

  if (loading || !data) {
    return <div className="bg-white rounded-lg p-6 shadow-sm">加载中...</div>;
  }

  return (
    <div className="bg-white rounded-lg shadow-sm p-6 border">
      <h2 className="text-lg font-semibold text-gray-900 mb-2">时间对比摘要</h2>
      <p className="text-sm text-gray-500 mb-4">
        {data.current_period.start_date} ~ {data.current_period.end_date}
        {' vs '}
        {data.comparison_period.start_date} ~ {data.comparison_period.end_date}
      </p>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {Object.entries(data.metrics).map(([key, metric]) => {
          const label = METRIC_LABELS[key] || { title: key, subtitle: '' };
          return (
            <MetricCard
              key={key}
              title={label.title}
              value={metric.current}
              subtitle={label.subtitle}
              change={metric.change}
              changePct={metric.change_pct}
            />
          );
        })}
      </div>
    </div>
  );
}
```

---

## Task 9: CustomerTrendsGrid 组件

**Files:**
- Create: `src/components/dashboard/CustomerTrendsGrid.tsx`
- Create: `src/components/dashboard/CustomerTrendsGrid.module.css`

- [ ] **Step 1: 创建样式文件**

Create `src/components/dashboard/CustomerTrendsGrid.module.css`:

```css
.grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.chartCard {
  background: white;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
  padding: 16px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.chartTitle {
  font-size: 14px;
  font-weight: 600;
  color: #111827;
  margin-bottom: 12px;
}

@media (max-width: 768px) {
  .grid {
    grid-template-columns: 1fr;
  }
}
```

- [ ] **Step 2: 创建组件**

Create `src/components/dashboard/CustomerTrendsGrid.tsx`:

```tsx
import { useEffect, useState } from 'react';
import {
  AreaChart,
  Area,
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { fetchCustomerTrends } from '../../api/insights';
import type { CustomerTrends } from '../../types/insights';
import styles from './CustomerTrendsGrid.module.css';

const COLORS = {
  SMOKER: '#8b5cf6',
  VIC: '#3b82f6',
  BOTH: '#10b981',
  POSITIVE: '#10b981',
  NEUTRAL: '#6b7280',
  NEGATIVE: '#ef4444',
  ACTIVE_RATE: '#3b82f6',
  HIGH_RISK: '#ef4444',
};

export function CustomerTrendsGrid() {
  const [data, setData] = useState<CustomerTrends | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchCustomerTrends(6).then(setData).finally(() => setLoading(false));
  }, []);

  if (loading || !data) {
    return <div className={styles.chartCard}>加载中...</div>;
  }

  return (
    <div className={styles.grid}>
      {/* 图表 1: VIC 客户池规模（堆叠面积图） */}
      <div className={styles.chartCard}>
        <h3 className={styles.chartTitle}>VIC 客户池规模趋势</h3>
        <ResponsiveContainer width="100%" height={250}>
          <AreaChart data={data.vic_pool_trend}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="month" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Area type="monotone" dataKey="SMOKER" stackId="1" stroke={COLORS.SMOKER} fill={COLORS.SMOKER} fillOpacity={0.6} />
            <Area type="monotone" dataKey="VIC" stackId="1" stroke={COLORS.VIC} fill={COLORS.VIC} fillOpacity={0.6} />
            <Area type="monotone" dataKey="BOTH" stackId="1" stroke={COLORS.BOTH} fill={COLORS.BOTH} fillOpacity={0.6} />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* 图表 2: VIC 活跃率（折线图） */}
      <div className={styles.chartCard}>
        <h3 className={styles.chartTitle}>VIC 活跃率趋势</h3>
        <ResponsiveContainer width="100%" height={250}>
          <LineChart data={data.vic_active_rate_trend}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="month" />
            <YAxis domain={[0, 100]} unit="%" />
            <Tooltip formatter={(v: number) => `${v.toFixed(1)}%`} />
            <Legend />
            <Line type="monotone" dataKey="active_rate" stroke={COLORS.ACTIVE_RATE} strokeWidth={2} name="活跃率" />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* 图表 3: 高风险客户（折线图） */}
      <div className={styles.chartCard}>
        <h3 className={styles.chartTitle}>高风险客户数量趋势</h3>
        <ResponsiveContainer width="100%" height={250}>
          <LineChart data={data.high_risk_trend}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="month" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Line type="monotone" dataKey="high_risk_count" stroke={COLORS.HIGH_RISK} strokeWidth={2} name="高风险客户" />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* 图表 4: 情感健康度（堆叠柱状图） */}
      <div className={styles.chartCard}>
        <h3 className={styles.chartTitle}>情感健康度趋势</h3>
        {data.sentiment_trend.length === 0 ? (
          <div className="text-sm text-gray-400 text-center py-8">情感趋势数据需要 AI 缓存关联，稍后上线</div>
        ) : (
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={data.sentiment_trend}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="Positive" stackId="1" fill={COLORS.POSITIVE} />
              <Bar dataKey="Neutral" stackId="1" fill={COLORS.NEUTRAL} />
              <Bar dataKey="Negative" stackId="1" fill={COLORS.NEGATIVE} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
```

---

## Task 10: AnomalyAlertsCard 组件

**Files:**
- Create: `src/components/dashboard/AnomalyAlertsCard.tsx`

- [ ] **Step 1: 创建组件**

Create `src/components/dashboard/AnomalyAlertsCard.tsx`:

```tsx
import { useEffect, useState } from 'react';
import { fetchAnomalyAlerts } from '../../api/insights';
import type { AnomalyAlerts, Anomaly } from '../../types/insights';

const ANOMALY_TYPE_LABELS: Record<string, string> = {
  sentiment_negative: '情感转负',
  purchase_interval_long: '购买间隔异常',
  chat_frequency_drop: '聊天频率骤降',
};

const SEVERITY_COLORS: Record<string, string> = {
  high: 'bg-red-100 text-red-700 border-red-300',
  medium: 'bg-yellow-100 text-yellow-700 border-yellow-300',
  low: 'bg-gray-100 text-gray-700 border-gray-300',
};

export function AnomalyAlertsCard() {
  const [data, setData] = useState<AnomalyAlerts | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAnomalyAlerts().then(setData).finally(() => setLoading(false));
  }, []);

  if (loading || !data) {
    return <div className="bg-white rounded-lg p-6 shadow-sm">加载中...</div>;
  }

  return (
    <div className="bg-white rounded-lg shadow-sm p-6 border">
      <h2 className="text-lg font-semibold text-gray-900 mb-2">
        异常客户预警 ({data.total_count} 人)
      </h2>
      {data.anomalies.length === 0 ? (
        <div className="text-sm text-gray-400 py-8 text-center">暂无异常客户</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-xs text-gray-500 border-b">
              <tr>
                <th className="text-left py-2">客户</th>
                <th className="text-left py-2">VIP</th>
                <th className="text-left py-2">异常类型</th>
                <th className="text-left py-2">原因</th>
                <th className="text-left py-2">最后购买</th>
                <th className="text-left py-2">操作</th>
              </tr>
            </thead>
            <tbody>
              {data.anomalies.slice(0, 10).map((a) => (
                <AnomalyRow key={a.buyer_nick + a.anomaly_type} anomaly={a} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function AnomalyRow({ anomaly }: { anomaly: Anomaly }) {
  return (
    <tr className="border-b hover:bg-gray-50">
      <td className="py-2 font-medium">{anomaly.buyer_nick}</td>
      <td className="py-2">{anomaly.vip_level}</td>
      <td className="py-2">
        <span
          className={`inline-block px-2 py-0.5 text-xs rounded border ${
            SEVERITY_COLORS[anomaly.severity] || SEVERITY_COLORS.low
          }`}
        >
          {ANOMALY_TYPE_LABELS[anomaly.anomaly_type] || anomaly.anomaly_type}
        </span>
      </td>
      <td className="py-2 text-gray-600">{anomaly.anomaly_reason}</td>
      <td className="py-2 text-gray-500">{anomaly.last_purchase_date || '—'}</td>
      <td className="py-2">
        <button className="text-blue-600 hover:underline text-sm">查看详情</button>
      </td>
    </tr>
  );
}
```

---

## Task 11: InventoryInquiriesCard 组件

**Files:**
- Create: `src/components/dashboard/InventoryInquiriesCard.tsx`

- [ ] **Step 1: 创建组件**

Create `src/components/dashboard/InventoryInquiriesCard.tsx`:

```tsx
import { useEffect, useState } from 'react';
import { fetchInventoryInquiries } from '../../api/insights';
import type { InventoryInquiries, InventoryInquiry } from '../../types/insights';

const SENTIMENT_COLORS: Record<string, string> = {
  Positive: 'bg-green-100 text-green-700',
  Neutral: 'bg-gray-100 text-gray-700',
  Negative: 'bg-red-100 text-red-700',
};

export function InventoryInquiriesCard() {
  const [data, setData] = useState<InventoryInquiries | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchInventoryInquiries().then(setData).finally(() => setLoading(false));
  }, []);

  if (loading || !data) {
    return <div className="bg-white rounded-lg p-6 shadow-sm">加载中...</div>;
  }

  return (
    <div className="bg-white rounded-lg shadow-sm p-6 border">
      <h2 className="text-lg font-semibold text-gray-900 mb-2">
        库存需求 ({data.total_count} 人)
      </h2>
      {data.inquiries.length === 0 ? (
        <div className="text-sm text-gray-400 py-8 text-center">
          暂无库存需求数据（Phase 2 Inventory Inquiry 上线后开始积累）
        </div>
      ) : (
        <div className="space-y-3 max-h-96 overflow-y-auto">
          {data.inquiries.map((inq) => (
            <InquiryRow key={inq.buyer_nick} inquiry={inq} />
          ))}
        </div>
      )}
    </div>
  );
}

function InquiryRow({ inquiry }: { inquiry: InventoryInquiry }) {
  const inventoryScore = inquiry.intent_distribution['Inventory Inquiry'] ?? 0;

  return (
    <div className="flex items-center justify-between p-3 border rounded hover:bg-gray-50">
      <div className="flex-1">
        <div className="flex items-center gap-2 mb-1">
          <span className="font-medium">{inquiry.buyer_nick}</span>
          <span className="text-xs px-2 py-0.5 bg-purple-100 text-purple-700 rounded">
            {inquiry.vip_level}
          </span>
          <span
            className={`text-xs px-2 py-0.5 rounded ${
              SENTIMENT_COLORS[inquiry.sentiment_label] || SENTIMENT_COLORS.Neutral
            }`}
          >
            {inquiry.sentiment_label}
          </span>
        </div>
        <div className="text-xs text-gray-500">
          库存查询 {Math.round(inventoryScore * 100)}% | 最近聊天: {inquiry.last_chat_date || '—'} | {inquiry.total_chat_messages} 条消息
        </div>
      </div>
      <div className="flex gap-2">
        <button className="text-sm text-blue-600 hover:underline">查看详情</button>
        <button className="text-sm text-gray-500 hover:underline">标记已联系</button>
      </div>
    </div>
  );
}
```

---

## Task 12: 重构 DashboardOverview（双 tab 布局）

**Files:**
- Modify: `src/views/DashboardOverview.tsx`

- [ ] **Step 1: 读取现有 DashboardOverview**

Run: `cat src/views/DashboardOverview.tsx`

查看现有 4-Group 指标卡片、Keyword Analysis、Priority List 的位置和 props。

- [ ] **Step 2: 重构为双 tab 布局**

完整重写 `src/views/DashboardOverview.tsx`:

```tsx
import { useState } from 'react';
import { TimeRangeFilter } from '../components/common/TimeRangeFilter';
import { VicPersonaCard } from '../components/dashboard/VicPersonaCard';
import { PeriodComparisonCard } from '../components/dashboard/PeriodComparisonCard';
import { CustomerTrendsGrid } from '../components/dashboard/CustomerTrendsGrid';
import { AnomalyAlertsCard } from '../components/dashboard/AnomalyAlertsCard';
import { InventoryInquiriesCard } from '../components/dashboard/InventoryInquiriesCard';
// 保留现有组件
import { KeywordAnalysisPanel } from '../components/dashboard/KeywordAnalysisPanel';
import { MetricCardGroup } from '../components/dashboard/MetricCardGroup';
import { PriorityList } from '../components/dashboard/PriorityList';

type TabKey = 'trends' | 'actions';

export function DashboardOverview() {
  const [activeTab, setActiveTab] = useState<TabKey>('trends');

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 顶部时间筛选器 */}
      <TimeRangeFilter />

      <div className="p-6 space-y-6">
        {/* 4-Group 指标卡片（保留现有） */}
        <MetricCardGroup />

        {/* Keyword & Issue Analysis（保留现有） */}
        <KeywordAnalysisPanel />

        {/* 双 Tab 内容区 */}
        <div className="bg-white rounded-lg shadow-sm border">
          {/* Tab 切换 */}
          <div className="flex border-b">
            <TabButton active={activeTab === 'trends'} onClick={() => setActiveTab('trends')}>
              趋势概览
            </TabButton>
            <TabButton active={activeTab === 'actions'} onClick={() => setActiveTab('actions')}>
              行动看板
            </TabButton>
          </div>

          {/* Tab 内容 */}
          <div className="p-6">
            {activeTab === 'trends' && (
              <div className="space-y-6">
                <VicPersonaCard />
                <PeriodComparisonCard />
                <CustomerTrendsGrid />
              </div>
            )}
            {activeTab === 'actions' && (
              <div className="space-y-6">
                <AnomalyAlertsCard />
                <InventoryInquiriesCard />
                <PriorityList />
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={`px-6 py-3 text-sm font-medium border-b-2 ${
        active
          ? 'border-blue-500 text-blue-600'
          : 'border-transparent text-gray-500 hover:text-gray-700'
      }`}
    >
      {children}
    </button>
  );
}
```

- [ ] **Step 3: 验证编译**

Run: `npx tsc --noEmit --pretty false`

Expected: 无错误

- [ ] **Step 4: 浏览器测试**

Run: `npm run dev`

浏览器验证：
- 顶部出现时间筛选器
- 4-Group 卡片、Keyword Analysis 正常显示
- 切换 Tab 1（趋势概览）：看到 VIC 群体画像、时间对比、4 个趋势图表
- 切换 Tab 2（行动看板）：看到异常预警、库存需求、Priority List

---

## Task 13: 扩展 KeywordAnalysisPanel（加入第 10 类）

**Files:**
- Modify: `src/components/dashboard/KeywordAnalysisPanel.tsx`

- [ ] **Step 1: 读取现有配置**

Run: `grep -n "categories\|9 类\|9 大" src/components/dashboard/KeywordAnalysisPanel.tsx`

查找现有 9 类关键词配置。

- [ ] **Step 2: 加入第 10 类「库存查询」**

在 categories 数组末尾追加：

```typescript
{
  key: 'inventory_inquiry',
  name: '库存查询',
  nameEn: 'Inventory Inquiry',
  color: '#06b6d4', // cyan
}
```

- [ ] **Step 3: 验证编译 + 浏览器测试**

Run: `npx tsc --noEmit --pretty false`

浏览器打开 Overview 页面，验证：
- Keyword Analysis 组件显示 10 个 Donut 扇区
- 「库存查询」扇区为青色

---

## Task 14: 端到端前端测试

**Files:**
- Create: `tests/integration/dashboard_e2e.test.tsx`

- [ ] **Step 1: 编写 Playwright 集成测试**

Create `tests/integration/dashboard_e2e.test.tsx`:

```tsx
import { test, expect } from '@playwright/test';

test('Overview page loads and shows all sections', async ({ page }) => {
  await page.goto('http://localhost:3000');

  // 时间筛选器
  await expect(page.getByText('时间范围:')).toBeVisible();
  await expect(page.getByRole('button', { name: '1M' })).toBeVisible();

  // 4-Group 指标卡片
  await expect(page.getByText('Customer Health')).toBeVisible();

  // Keyword Analysis
  await expect(page.getByText(/关键词分析|Keyword/i)).toBeVisible();

  // Tab 1 默认
  await expect(page.getByText('VIC 群体画像')).toBeVisible({ timeout: 10000 });
  await expect(page.getByText('时间对比摘要')).toBeVisible();
  await expect(page.getByText('VIC 客户池规模趋势')).toBeVisible();

  // 切换到 Tab 2
  await page.getByRole('button', { name: '行动看板' }).click();
  await expect(page.getByText('异常客户预警')).toBeVisible({ timeout: 10000 });
  await expect(page.getByText(/库存需求/)).toBeVisible();
});

test('Time range filter changes context', async ({ page }) => {
  await page.goto('http://localhost:3000');
  await page.getByRole('button', { name: '7D' }).click();
  // 验证时间范围显示更新
  await expect(page.locator('text=/\\d{4}-\\d{2}-\\d{2} ~ \\d{4}-\\d{2}-\\d{2}/')).toBeVisible();
});
```

- [ ] **Step 2: 运行 E2E 测试**

Run: `npx playwright test tests/integration/dashboard_e2e.test.tsx`

Expected: PASS

- [ ] **Step 3: 修复失败（如有）**

---

## Task 15: 性能与响应式验证

**Files:**
- Create: `tests/integration/dashboard_perf.test.tsx`

- [ ] **Step 1: 性能测试（5 个 API 并行）**

Create `tests/integration/dashboard_perf.test.tsx`:

```tsx
import { test, expect } from '@playwright/test';

test('Dashboard loads within 3 seconds', async ({ page }) => {
  const start = Date.now();
  await page.goto('http://localhost:3000', { waitUntil: 'networkidle' });
  const elapsed = Date.now() - start;

  // 首屏加载 < 3s
  expect(elapsed).toBeLessThan(3000);
});

test('5 APIs called in parallel', async ({ page }) => {
  const apiCalls: string[] = [];
  page.on('request', (req) => {
    if (req.url().includes('/api/v2/')) {
      apiCalls.push(req.url());
    }
  });

  await page.goto('http://localhost:3000');
  await page.waitForTimeout(2000);

  // 验证至少 5 个 API 调用
  expect(apiCalls.length).toBeGreaterThanOrEqual(5);
});
```

- [ ] **Step 2: 响应式测试**

```tsx
test('Mobile responsive layout', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 667 });
  await page.goto('http://localhost:3000');

  // 时间筛选器应堆叠
  await expect(page.getByRole('button', { name: '1M' })).toBeVisible();
  // 趋势图表 1 列布局
  await expect(page.getByText('VIC 客户池规模趋势')).toBeVisible();
});
```

- [ ] **Step 3: 视觉回归测试**

```tsx
test('Visual regression at 1440px', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto('http://localhost:3000');
  await page.waitForTimeout(2000);

  await expect(page).toHaveScreenshot('dashboard-overview-1440.png', {
    fullPage: true,
  });
});
```

Run: `npx playwright test tests/integration/dashboard_perf.test.tsx`

Expected: 全部 PASS

---

## Phase 4 前端完成

**所有 15 个任务完成后，前端 Overview 改造全部完成。**

**完成检查清单：**
- [ ] 全局时间筛选器可切换预设和自定义
- [ ] Tab 1（趋势概览）显示 VIC 群体画像、时间对比、4 个趋势图表
- [ ] Tab 2（行动看板）显示异常预警、库存需求、Priority List
- [ ] Keyword Analysis 扩展为 10 大类（含库存查询）
- [ ] 5 个 API 并行调用 < 2s
- [ ] 首屏加载 < 3s
- [ ] 移动端响应式（375px 单列布局）
- [ ] 视觉回归测试通过
- [ ] Playwright E2E 测试全部通过

**下一步：** 整体测试 + 提交 PR
