/**
 * Dashboard 指标卡片组件 (v2.0 - 运营导向)
 *
 * 4个主题组：
 * 1. 客户健康度（情感分布）
 * 2. 跟进优先级（follow_priority）
 * 3. 销售机会（复购潜力/VIC/SMOKER）
 * 4. 服务质量（负面情绪/投诉反馈）
 */

import React from 'react';
import { Heart, AlertCircle, TrendingUp, MessageCircle, LucideIcon } from 'lucide-react';
import { NotionCard } from '../common/NotionCard';
import { DashboardMetrics } from '../../api/client';
import { MetricCardSkeleton } from '../common/LoadingState';
import { ErrorAlert } from '../common/ErrorAlert';

// ============================================================
// 类型定义
// ============================================================

interface MetricItem {
  label: string;
  value: number;
  percentage?: number;
  color?: string;
}

interface MetricGroupProps {
  title: string;
  icon: LucideIcon;
  iconColor: string;
  metrics: MetricItem[];
  onClick?: () => void;
}

interface MetricCardsProps {
  metrics: DashboardMetrics | null;
  isLoading?: boolean;
  error?: string | null;
  onRetry?: () => void;
}

// ============================================================
// 格式化函数
// ============================================================

function formatNumber(num: number): string {
  if (num >= 10000) return (num / 10000).toFixed(1) + '万';
  if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
  return num.toLocaleString();
}

function formatPercentage(value: number, total: number): string {
  if (total === 0) return '0%';
  return ((value / total) * 100).toFixed(1) + '%';
}

// 辅助函数：确保值为数字（API 返回的是字符串）
function toNumber(val: any): number {
  return Number(val) || 0;
}

// ============================================================
// 指标组卡片组件
// ============================================================

const MetricGroupCard: React.FC<MetricGroupProps> = ({ title, icon: Icon, iconColor, metrics, onClick }) => {
  const total = metrics.reduce((sum, m) => sum + m.value, 0);

  return (
    <NotionCard
      className={`hover:bg-notion-hover transition-all duration-200 cursor-pointer group ${onClick ? '' : 'pointer-events-none'}`}
      onClick={onClick}
    >
      {/* 标题 */}
      <div className="flex items-center gap-2 mb-3 pb-2 border-b border-notion-border">
        <Icon size={14} style={{ color: iconColor }} />
        <span className="text-xs font-medium text-notion-text uppercase tracking-wider">{title}</span>
      </div>

      {/* 指标列表 */}
      <div className="space-y-2">
        {metrics.map((metric, idx) => (
          <div key={idx} className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {metric.color && (
                <span
                  className="w-2 h-2 rounded-full"
                  style={{ backgroundColor: metric.color }}
                />
              )}
              <span className="text-[11px] text-notion-muted">{metric.label}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-notion-text">{formatNumber(metric.value)}</span>
              {metric.percentage !== undefined && (
                <span className="text-[10px] text-notion-muted">({metric.percentage}%)</span>
              )}
            </div>
          </div>
        ))}
      </div>
    </NotionCard>
  );
};

// ============================================================
// 主组件
// ============================================================

export const MetricCards: React.FC<MetricCardsProps> = ({
  metrics,
  isLoading = false,
  error,
  onRetry
}) => {
  // 加载状态
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {[1, 2, 3, 4].map((i) => (
          <MetricCardSkeleton key={i} />
        ))}
      </div>
    );
  }

  // 错误状态
  if (error) {
    return (
      <ErrorAlert
        message="无法加载Dashboard指标"
        onRetry={onRetry}
      />
    );
  }

  // 数据为空时的保护
  if (!metrics) {
    return null;
  }

  const total = toNumber(metrics.total_target_buyers) || 1;

  // 客户健康度数据
  const healthMetrics: MetricItem[] = [
    {
      label: '正面情感',
      value: toNumber(metrics.positive_sentiment_count),
      percentage: parseFloat(formatPercentage(toNumber(metrics.positive_sentiment_count), total)),
      color: '#86EFAC', // 绿色
    },
    {
      label: '中性情感',
      value: toNumber(metrics.neutral_sentiment_count),
      percentage: parseFloat(formatPercentage(toNumber(metrics.neutral_sentiment_count), total)),
      color: '#FCD34D', // 黄色
    },
    {
      label: '负面情感',
      value: toNumber(metrics.negative_sentiment_count),
      percentage: parseFloat(formatPercentage(toNumber(metrics.negative_sentiment_count), total)),
      color: '#FCA5A5', // 红色
    },
  ];

  // 跟进优先级数据
  const priorityMetrics: MetricItem[] = [
    {
      label: '紧急',
      value: toNumber(metrics.urgent_priority_count),
      percentage: parseFloat(formatPercentage(toNumber(metrics.urgent_priority_count), total)),
      color: '#EF4444', // 红色
    },
    {
      label: '高',
      value: toNumber(metrics.high_priority_count),
      percentage: parseFloat(formatPercentage(toNumber(metrics.high_priority_count), total)),
      color: '#F97316', // 橙色
    },
    {
      label: '中/低',
      value: toNumber(metrics.medium_priority_count) + toNumber(metrics.low_priority_count),
      percentage: parseFloat(formatPercentage(
        toNumber(metrics.medium_priority_count) + toNumber(metrics.low_priority_count),
        total
      )),
      color: '#9CA3AF', // 灰色
    },
  ];

  // 销售机会数据
  const salesMetrics: MetricItem[] = [
    {
      label: '复购潜力',
      value: toNumber(metrics.repurchase_potential_count),
      percentage: parseFloat(formatPercentage(toNumber(metrics.repurchase_potential_count), total)),
      color: '#22C55E', // 绿色
    },
    {
      label: 'VIC客户',
      value: toNumber(metrics.total_vics),
      percentage: parseFloat(formatPercentage(toNumber(metrics.total_vics), total)),
      color: '#8B5CF6', // 紫色
    },
    {
      label: 'SMOKER',
      value: toNumber(metrics.total_smokers),
      percentage: parseFloat(formatPercentage(toNumber(metrics.total_smokers), total)),
      color: '#3B82F6', // 蓝色
    },
  ];

  // 服务质量数据（暂时用流失风险作为代理）
  const serviceMetrics: MetricItem[] = [
    {
      label: '负面情绪',
      value: toNumber(metrics.negative_sentiment_count),
      percentage: parseFloat(formatPercentage(toNumber(metrics.negative_sentiment_count), total)),
      color: '#EF4444', // 红色
    },
    {
      label: '高流失风险',
      value: toNumber(metrics.high_churn_count),
      percentage: parseFloat(formatPercentage(toNumber(metrics.high_churn_count), total)),
      color: '#F97316', // 橙色
    },
    {
      label: '中流失风险',
      value: toNumber(metrics.medium_churn_count),
      percentage: parseFloat(formatPercentage(toNumber(metrics.medium_churn_count), total)),
      color: '#FCD34D', // 黄色
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      <MetricGroupCard
        title="客户健康度"
        icon={Heart}
        iconColor="#EC4899"
        metrics={healthMetrics}
      />
      <MetricGroupCard
        title="跟进优先级"
        icon={AlertCircle}
        iconColor="#F97316"
        metrics={priorityMetrics}
      />
      <MetricGroupCard
        title="销售机会"
        icon={TrendingUp}
        iconColor="#22C55E"
        metrics={salesMetrics}
      />
      <MetricGroupCard
        title="服务质量"
        icon={MessageCircle}
        iconColor="#3B82F6"
        metrics={serviceMetrics}
      />
    </div>
  );
};
