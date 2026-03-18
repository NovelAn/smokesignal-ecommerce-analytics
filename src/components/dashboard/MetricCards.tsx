/**
 * Dashboard 指标卡片组件
 *
 * 显示核心业务指标：
 * - 目标买家总数
 * - 历史总净销售额
 * - 总订单数
 * - 平均退款率
 */

import React from 'react';
import { Users, DollarSign, ShoppingBag, Percent, LucideIcon } from 'lucide-react';
import { NotionCard } from '../common/NotionCard';
import { DashboardMetrics } from '../../../api/client';
import { MetricCardSkeleton } from '../common/LoadingState';
import { ErrorAlert } from '../common/ErrorAlert';

interface MetricCard {
  label: string;
  value: string;
  change: string;
  icon: LucideIcon;
}

interface MetricCardsProps {
  metrics: DashboardMetrics;
  isLoading?: boolean;
  error?: string | null;
  onRetry?: () => void;
}

/**
 * 格式化数字
 */
function formatNumber(num: number | string): string {
  const n = Number(num);
  if (n >= 10000) return (n / 10000).toFixed(1) + '万';
  if (n >= 1000) return (n / 1000).toFixed(1) + 'K';
  return n.toLocaleString();
}

/**
 * 格式化金额
 */
function formatCurrency(num: number | string): string {
  const n = Number(num);
  if (n >= 10000) return '¥' + (n / 10000).toFixed(1) + '万';
  return '¥' + formatNumber(n);
}

/**
 * 指标卡片组件
 */
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
        <MetricCardSkeleton />
        <MetricCardSkeleton />
        <MetricCardSkeleton />
        <MetricCardSkeleton />
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

  // 计算指标卡片数据
  const cards: MetricCard[] = [
    {
      label: '目标买家总数',
      value: formatNumber(metrics.total_target_buyers),
      change: `VIC: ${formatNumber(metrics.total_vics)} | Smoker: ${formatNumber(metrics.total_smokers)}`,
      icon: Users,
    },
    {
      label: '历史总净销售额',
      value: formatCurrency(metrics.total_netsales),
      change: `近6月: ${formatCurrency(metrics.total_l6m_netsales)}`,
      icon: DollarSign,
    },
    {
      label: '总订单数',
      value: formatNumber(metrics.total_orders),
      change: `人均: ${Number(metrics.avg_orders_per_buyer).toFixed(1)}单`,
      icon: ShoppingBag,
    },
    {
      label: '平均退款率',
      value: (Number(metrics.avg_refund_rate) * 100).toFixed(1) + '%',
      change: `高流失风险: ${formatNumber(metrics.high_churn_count)}人`,
      icon: Percent,
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {cards.map((card, idx) => (
        <MetricCard key={idx} card={card} />
      ))}
    </div>
  );
};

/**
 * 单个指标卡片
 */
const MetricCard: React.FC<{ card: MetricCard }> = ({ card }) => {
  const Icon = card.icon;

  return (
    <NotionCard className="hover:bg-notion-hover transition-colors cursor-pointer">
      <div className="flex items-center justify-between mb-2">
        <span className="text-notion-muted text-sm flex items-center gap-2">
          <Icon size={14} /> {card.label}
        </span>
      </div>
      <div className="flex items-end gap-2">
        <h4 className="text-3xl font-serif text-notion-text">{card.value}</h4>
      </div>
      <div className="text-xs text-notion-muted mt-1">{card.change}</div>
    </NotionCard>
  );
};
