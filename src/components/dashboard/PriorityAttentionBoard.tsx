/**
 * 重点关注客户看板组件
 *
 * 显示需要优先处理的客户：
 * - 高流失风险客户
 * - 高价值客户
 * - 中流失风险客户
 */

import React from 'react';
import { AlertTriangle, Download } from 'lucide-react';
import { NotionCard } from '../common/NotionCard';
import { NotionTag } from '../common/NotionTag';
import { TableSkeleton } from '../common/LoadingState';
import { ErrorAlert, EmptyState } from '../common/ErrorAlert';
import { BuyerInfo } from '../../../api/client';

interface BuyerGroup {
  high_churn_risk: BuyerInfo[];
  high_value: BuyerInfo[];
  medium_churn_risk: BuyerInfo[];
}

interface PriorityAttentionBoardProps {
  actionableCustomers: BuyerGroup;
  isLoading?: boolean;
  error?: string | null;
  onRetry?: () => void;
  onRowAction?: (buyer: BuyerInfo, actionType: string) => void;
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
 * VIP 等级颜色映射
 */
function getVIPColor(vipLevel: string): 'red' | 'orange' | 'yellow' | 'green' | 'blue' | 'gray' {
  const colorMap: Record<string, 'red' | 'orange' | 'yellow' | 'green' | 'blue' | 'gray'> = {
    'V3': 'red',
    'V2': 'orange',
    'V1': 'yellow',
    'V0': 'green',
    'Non-VIP': 'gray',
  };
  return colorMap[vipLevel] || 'gray';
}

/**
 * 流失风险颜色映射
 */
function getChurnRiskColor(churnRisk: string): string {
  const colorMap: Record<string, string> = {
    '高': 'text-red-600',
    '中': 'text-yellow-600',
    '低': 'text-green-600',
  };
  return colorMap[churnRisk] || 'text-gray-600';
}

/**
 * 重点关注客户看板
 */
export const PriorityAttentionBoard: React.FC<PriorityAttentionBoardProps> = ({
  actionableCustomers,
  isLoading = false,
  error,
  onRetry,
  onRowAction
}) => {
  // 加载状态
  if (isLoading) {
    return (
      <NotionCard
        title="Priority Attention Board (High Risk / Actionable)"
        icon={AlertTriangle}
        className="overflow-hidden"
      >
        <TableSkeleton rows={5} />
      </NotionCard>
    );
  }

  // 错误状态
  if (error) {
    return (
      <NotionCard
        title="Priority Attention Board (High Risk / Actionable)"
        icon={AlertTriangle}
        className="overflow-hidden"
      >
        <ErrorAlert message="无法加载可操作客户列表" onRetry={onRetry} />
      </NotionCard>
    );
  }

  // 检查是否有数据
  const hasData =
    actionableCustomers.high_churn_risk.length > 0 ||
    actionableCustomers.high_value.length > 0 ||
    actionableCustomers.medium_churn_risk.length > 0;

  return (
    <NotionCard
      title="Priority Attention Board (High Risk / Actionable)"
      icon={AlertTriangle}
      className="overflow-hidden"
      action={
        <button
          className="flex items-center gap-1.5 px-3 py-1.5 bg-notion-gray_bg text-notion-text border border-notion-border rounded text-xs font-medium hover:bg-gray-200 transition-colors"
          onClick={() => {
            // TODO: 实现 CSV 导出功能
            console.log('Download CSV');
          }}
        >
          <Download size={12} /> Download CSV
        </button>
      }
    >
      {hasData ? (
        <div className="flex flex-col h-[500px]">
          {/* 滚动表格 */}
          <div className="flex-1 overflow-y-auto scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-transparent border border-notion-border rounded-sm">
            <table className="w-full text-left text-sm sticky">
              <thead className="sticky top-0 bg-white z-10 shadow-sm">
                <tr className="border-b border-notion-border text-notion-muted text-xs uppercase bg-notion-gray_bg/30">
                  <th className="py-2.5 px-4 font-semibold">User</th>
                  <th className="py-2.5 px-4 font-semibold">VIP Level</th>
                  <th className="py-2.5 px-4 font-semibold">L6M Spend</th>
                  <th className="py-2.5 px-4 font-semibold">Churn Risk</th>
                  <th className="py-2.5 px-4 font-semibold">Last Purchase</th>
                  <th className="py-2.5 px-4 font-semibold text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-notion-border">
                {/* 高流失风险 */}
                {actionableCustomers.high_churn_risk.map((buyer, idx) => (
                  <BuyerRow
                    key={`high-${idx}`}
                    buyer={buyer}
                    formatNumber={formatNumber}
                    getVIPColor={getVIPColor}
                    getChurnRiskColor={getChurnRiskColor}
                    actionLabel="Handle"
                    onAction={() => onRowAction?.(buyer, 'handle')}
                  />
                ))}

                {/* 高价值客户 */}
                {actionableCustomers.high_value.map((buyer, idx) => (
                  <BuyerRow
                    key={`value-${idx}`}
                    buyer={buyer}
                    formatNumber={formatNumber}
                    getVIPColor={getVIPColor}
                    getChurnRiskColor={getChurnRiskColor}
                    actionLabel="Follow Up"
                    onAction={() => onRowAction?.(buyer, 'followup')}
                  />
                ))}

                {/* 中流失风险 */}
                {actionableCustomers.medium_churn_risk.map((buyer, idx) => (
                  <BuyerRow
                    key={`medium-${idx}`}
                    buyer={buyer}
                    formatNumber={formatNumber}
                    getVIPColor={getVIPColor}
                    getChurnRiskColor={getChurnRiskColor}
                    actionLabel="Monitor"
                    onAction={() => onRowAction?.(buyer, 'monitor')}
                  />
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <EmptyState
          title="暂无需要关注的客户"
          description="所有客户状态正常"
        />
      )}
    </NotionCard>
  );
};

/**
 * 客户行组件
 */
const BuyerRow: React.FC<{
  buyer: BuyerInfo;
  formatNumber: (num: number | string) => string;
  getVIPColor: (level: string) => 'red' | 'orange' | 'yellow' | 'green' | 'blue' | 'gray';
  getChurnRiskColor: (risk: string) => string;
  actionLabel: string;
  onAction: () => void;
}> = ({ buyer, formatNumber, getVIPColor, getChurnRiskColor, actionLabel, onAction }) => {
  return (
    <tr className="hover:bg-notion-hover transition-colors">
      <td className="py-3 px-4 font-medium text-notion-text">
        {buyer.buyer_nick || 'Unknown'}
      </td>
      <td className="py-3 px-4">
        <NotionTag text={buyer.vip_level} color={getVIPColor(buyer.vip_level)} />
      </td>
      <td className="py-3 px-4 text-xs font-mono">¥{formatNumber(buyer.l6m_netsales)}</td>
      <td className="py-3 px-4">
        <span className={`text-xs font-bold ${getChurnRiskColor(buyer.churn_risk)}`}>
          {buyer.churn_risk}
        </span>
      </td>
      <td className="py-3 px-4 text-notion-muted text-xs">{buyer.last_purchase_date}</td>
      <td className="py-3 px-4 text-right">
        <button
          className="text-blue-600 hover:text-blue-800 text-xs font-semibold underline"
          onClick={onAction}
        >
          {actionLabel}
        </button>
      </td>
    </tr>
  );
};
