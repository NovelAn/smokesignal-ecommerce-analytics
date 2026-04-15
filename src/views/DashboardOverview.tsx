/**
 * Dashboard Overview 视图组件
 *
 * 显示整体业务指标和分析图表
 *
 * 包含：
 * - 时间范围筛选器
 * - 指标卡片（MetricCards）
 * - 关键词分析面板（KeywordAnalysisPanel）
 * - 重点关注客户看板（PriorityAttentionBoard）
 * - 情感和意图图表（SentimentCharts）
 */

import React, { useState } from 'react';
import { apiClient, DashboardMetrics } from '../api/client';
import { useDataFetchingWithRetry } from '../hooks/useDataFetching';
import { MetricCards } from '../components/dashboard/MetricCards';
import { KeywordAnalysisPanel } from '../components/dashboard/KeywordAnalysisPanel';
import { PriorityAttentionBoard } from '../components/dashboard/PriorityAttentionBoard';
import { SentimentCharts } from '../components/dashboard/SentimentCharts';

type TimeRange = '7d' | '15d' | '30d' | '90d' | '1y';

/**
 * Dashboard Overview 主视图
 */
export const DashboardOverview: React.FC = () => {
  // 全局时间范围筛选器
  const [timeRange, setTimeRange] = useState<TimeRange>('1y');

  // ========== 获取 Dashboard 指标数据 ==========
  const {
    data: metrics,
    isLoading: metricsLoading,
    error: metricsError,
  } = useDataFetchingWithRetry<DashboardMetrics>(
    () => apiClient.getDashboardMetrics(),
    2 // 重试2次
  );

  // ========== 事件处理 ==========

  /**
   * 处理客户行操作
   */
  const handleRowAction = (buyer: any, actionType: string) => {
    console.log('Action:', actionType, 'Buyer:', buyer);
    // TODO: 实现具体的操作逻辑
    // 例如：跳转到客户详情页、打开弹窗等
  };

  // ========== 渲染 ==========

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      {/* 全局时间范围筛选器 */}
      <TimeRangeFilter
        currentRange={timeRange}
        onRangeChange={setTimeRange}
      />

      {/* Row 1: 指标卡片 */}
      <MetricCards
        metrics={metrics!}
        isLoading={metricsLoading}
        error={metricsError}
        onRetry={() => window.location.reload()}
      />

      {/* Row 2: 关键词分析面板 */}
      <KeywordAnalysisPanel timeRange={timeRange} />

      {/* Row 3: 重点关注客户看板 */}
      <PriorityAttentionBoard
        onRowAction={handleRowAction}
      />

      {/* Row 4: 情感和意图图表 */}
      <SentimentCharts timeRange={timeRange} />
    </div>
  );
};

/**
 * 时间范围筛选器组件
 */
interface TimeRangeFilterProps {
  currentRange: TimeRange;
  onRangeChange: (range: TimeRange) => void;
}

const TimeRangeFilter: React.FC<TimeRangeFilterProps> = ({
  currentRange,
  onRangeChange,
}) => {
  const ranges: Array<{ id: TimeRange; label: string }> = [
    { id: '7d', label: '7 Days' },
    { id: '15d', label: '15 Days' },
    { id: '30d', label: '1 Mo' },
    { id: '90d', label: '1 Qtr' },
    { id: '1y', label: '1 Yr' },
  ];

  return (
    <div className="flex justify-end">
      <div className="flex bg-notion-gray_bg p-0.5 rounded-md border border-notion-border shadow-sm">
        {ranges.map((range) => (
          <button
            key={range.id}
            onClick={() => onRangeChange(range.id)}
            className={`px-4 py-2 text-sm font-medium rounded-sm transition-all ${
              currentRange === range.id
                ? 'bg-white text-blue-700 shadow-sm border border-blue-100'
                : 'text-notion-muted hover:text-notion-text'
            }`}
          >
            {range.label}
          </button>
        ))}
      </div>
    </div>
  );
};
