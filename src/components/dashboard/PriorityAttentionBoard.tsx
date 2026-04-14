/**
 * Priority Attention Board 组件
 *
 * 显示需要优先关注的客户:
 * - 支持多选筛选 (channel, buyer_type, follow_priority, has_chat)
 * - 分页显示 (分页器在标题栏)
 * - 扁平化表格设计
 * - CSV导出功能
 */

import React, { useState, useMemo, useCallback, useRef, useEffect } from 'react';
import {
  AlertTriangle,
  Download,
  ChevronLeft,
  ChevronRight,
  Filter,
  RefreshCw,
  Loader2,
} from 'lucide-react';
import { NotionCard } from '../common/NotionCard';
import { NotionTag } from '../common/NotionTag';
import { TableSkeleton } from '../common/LoadingState';
import { ErrorAlert, EmptyState } from '../common/ErrorAlert';
import { apiClient, PriorityCustomer, PriorityCustomersFilters, PriorityCustomersResponse } from '../../api/client';
import { useDataFetchingWithRetry } from '../../hooks/useDataFetching';

// ========== 常量定义 ==========

const PAGE_SIZE = 15;

const CHANNEL_OPTIONS = [
  { value: 'ALL', label: '全部' },
  { value: 'DTC', label: 'DTC' },
  { value: 'PFS', label: 'PFS' },
];

const BUYER_TYPE_OPTIONS = [
  { value: 'ALL', label: '全部' },
  { value: 'SMOKER', label: 'Smoker' },
  { value: 'VIC', label: 'VIC' },
  { value: 'BOTH', label: 'Both' },
];

const FOLLOW_PRIORITY_OPTIONS = [
  { value: 'ALL', label: '全部' },
  { value: '紧急', label: '紧急' },
  { value: '高', label: '高' },
  { value: '中', label: '中' },
  { value: '低', label: '低' },
];

const HAS_CHAT_OPTIONS = [
  { value: 'ALL', label: '全部' },
  { value: 'true', label: '有聊天' },
  { value: 'false', label: '无聊天' },
];

// ========== 工具函数 ==========

function formatNumber(num: number | string): string {
  const n = Number(num);
  if (isNaN(n)) return 'N/A';
  if (n >= 10000) return (n / 10000).toFixed(1) + '万';
  if (n >= 1000) return (n / 1000).toFixed(1) + 'K';
  return n.toLocaleString();
}

function formatCurrency(num: number | string): string {
  const n = Number(num);
  if (isNaN(n)) return 'N/A';
  return '¥' + formatNumber(n);
}

function formatPercent(num: number | string): string {
  const n = Number(num);
  if (isNaN(n)) return 'N/A';
  return (n * 100).toFixed(1) + '%';
}

function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return 'N/A';
  try {
    const date = new Date(dateStr);
    if (isNaN(date.getTime())) return 'N/A';
    return date.toISOString().split('T')[0];
  } catch {
    return 'N/A';
  }
}

function getPriorityColor(priority: string): 'red' | 'orange' | 'yellow' | 'green' | 'blue' | 'gray' {
  const colorMap: Record<string, 'red' | 'orange' | 'yellow' | 'green' | 'blue' | 'gray'> = {
    '紧急': 'red',
    '高': 'orange',
    '中': 'yellow',
    '低': 'gray',
  };
  return colorMap[priority] || 'gray';
}

function getSentimentColor(label: string): 'red' | 'orange' | 'yellow' | 'green' | 'blue' | 'gray' {
  const colorMap: Record<string, 'red' | 'orange' | 'yellow' | 'green' | 'blue' | 'gray'> = {
    'Positive': 'green',
    'Neutral': 'gray',
    'Negative': 'red',
  };
  return colorMap[label] || 'gray';
}

function truncateText(text: string | null | undefined, maxLen: number = 20): string {
  if (!text) return '-';
  if (text.length <= maxLen) return text;
  return text.slice(0, maxLen) + '...';
}

/**
 * 解析JSON字符串数组（API可能返回字符串或数组）
 */
function parseJsonArray(value: string | string[] | null | undefined): string[] {
  if (!value) return [];
  if (Array.isArray(value)) return value;
  try {
    const parsed = JSON.parse(value);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

// ========== 组件定义 ==========

interface PriorityAttentionBoardProps {
  onRowAction?: (buyer: PriorityCustomer, actionType: string) => void;
}

export const PriorityAttentionBoard: React.FC<PriorityAttentionBoardProps> = ({
  onRowAction
}) => {
  // ========== 状态管理 ==========
  const [currentPage, setCurrentPage] = useState(1);

  // 筛选状态
  const [filters, setFilters] = useState<PriorityCustomersFilters>({
    use_default_filter: true
  });

  // 临时筛选状态
  const [tempFilters, setTempFilters] = useState<PriorityCustomersFilters>(filters);
  const [showFilterPanel, setShowFilterPanel] = useState(false);

  // ========== 数据获取 ==========
  const fetchPriorityCustomers = useCallback(async () => {
    const offset = (currentPage - 1) * PAGE_SIZE;
    return apiClient.getPriorityCustomers({
      ...filters,
      limit: PAGE_SIZE,
      offset
    });
  }, [currentPage, filters]);

  const {
    data: response,
    isLoading,
    error,
    refetch
  } = useDataFetchingWithRetry<PriorityCustomersResponse>(
    fetchPriorityCustomers,
    2,
    [currentPage, filters] // Re-fetch when page or filters change
  );

  // ========== 计算属性 ==========
  const totalPages = useMemo(() => {
    if (!response?.total) return 1;
    return Math.ceil(response.total / PAGE_SIZE);
  }, [response?.total]);

  const activeFiltersCount = useMemo(() => {
    let count = 0;
    if (filters.channel && filters.channel.length > 0) count++;
    if (filters.buyer_type && filters.buyer_type.length > 0) count++;
    if (filters.follow_priority && filters.follow_priority.length > 0) count++;
    if (filters.has_chat) count++;
    return count;
  }, [filters]);

  // ========== 事件处理 ==========
  const handleApplyFilters = useCallback(() => {
    setFilters(tempFilters);
    setCurrentPage(1);
    setShowFilterPanel(false);
  }, [tempFilters]);

  const handleResetFilters = useCallback(() => {
    const resetFilters: PriorityCustomersFilters = {
      use_default_filter: true
    };
    setTempFilters(resetFilters);
    setFilters(resetFilters);
    setCurrentPage(1);
    setShowFilterPanel(false);
  }, []);

  const handlePageChange = useCallback((newPage: number) => {
    setCurrentPage(newPage);
  }, []);

  const handleExportCSV = useCallback(() => {
    const url = apiClient.getPriorityCustomersCSVUrl(filters);
    window.open(url, '_blank');
  }, [filters]);

  // ========== 渲染 ==========
  // 保留之前的客户数据用于平滑过渡
  const prevCustomersRef = useRef<PriorityCustomer[]>([]);
  const customers = response?.customers || [];
  const hasData = customers.length > 0;

  // 当有新数据时，更新ref
  useEffect(() => {
    if (customers.length > 0) {
      prevCustomersRef.current = customers;
    }
  }, [customers]);

  // 显示的数据：加载时用之前的数据，否则用当前数据
  const displayCustomers = isLoading && prevCustomersRef.current.length > 0
    ? prevCustomersRef.current
    : customers;

  return (
    <NotionCard
      className="overflow-hidden"
      icon={AlertTriangle}
      title="需优先跟进的客户"
      subtitle={`${response?.total || 0} 位客户 | 默认: 紧急/高优先级 或 负面情感`}
      action={
        <div className="flex items-center gap-3">
          {/* 分页器 */}
          {totalPages > 1 && (
            <div className="flex items-center gap-1">
              <button
                onClick={() => handlePageChange(Math.max(1, currentPage - 1))}
                disabled={currentPage === 1}
                className="p-1 border border-notion-border rounded hover:bg-notion-hover disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                title="上一页"
              >
                <ChevronLeft size={14} />
              </button>
              <span className="text-xs text-notion-muted px-2">
                {currentPage} / {totalPages}
              </span>
              <button
                onClick={() => handlePageChange(Math.min(totalPages, currentPage + 1))}
                disabled={currentPage === totalPages}
                className="p-1 border border-notion-border rounded hover:bg-notion-hover disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                title="下一页"
              >
                <ChevronRight size={14} />
              </button>
            </div>
          )}
          {/* 筛选按钮 */}
          <button
            onClick={() => setShowFilterPanel(!showFilterPanel)}
            className={`flex items-center gap-1 px-2 py-1 border rounded text-xs font-medium transition-colors ${
              showFilterPanel || activeFiltersCount > 0
                ? 'bg-blue-50 text-blue-700 border-blue-200'
                : 'bg-notion-gray_bg text-notion-text border-notion-border hover:bg-gray-200'
            }`}
          >
            <Filter size={12} />
            筛选 {activeFiltersCount > 0 && `(${activeFiltersCount})`}
          </button>
          {/* 导出按钮 */}
          <button
            onClick={handleExportCSV}
            className="flex items-center gap-1 px-2 py-1 bg-notion-gray_bg text-notion-text border border-notion-border rounded text-xs font-medium hover:bg-gray-200 transition-colors"
          >
            <Download size={12} />
            导出
          </button>
        </div>
      }
    >
      {/* 筛选面板 */}
      {showFilterPanel && (
        <FilterPanel
          tempFilters={tempFilters}
          setTempFilters={setTempFilters}
          onApply={handleApplyFilters}
          onReset={handleResetFilters}
          onClose={() => setShowFilterPanel(false)}
        />
      )}

      {/* 表格 */}
      {displayCustomers.length > 0 ? (
        <div className="relative overflow-x-auto max-h-[400px] overflow-y-auto">
          {/* 加载覆盖层 */}
          {isLoading && (
            <div className="absolute inset-0 bg-white/60 backdrop-blur-[1px] z-10 flex items-center justify-center transition-opacity duration-300">
              <Loader2 className="w-5 h-5 animate-spin text-blue-600" />
            </div>
          )}
          <table className={`w-full text-xs transition-opacity duration-200 ${isLoading ? 'opacity-60' : 'opacity-100'}`}>
            <thead className="sticky top-0 z-20">
              <tr className="bg-white border-b border-notion-border text-left">
                <th className="px-3 py-1 font-medium text-notion-muted whitespace-nowrap">客户</th>
                <th className="px-2 py-1 font-medium text-notion-muted whitespace-nowrap">优先级</th>
                <th className="px-2 py-1 font-medium text-notion-muted whitespace-nowrap">情感</th>
                <th className="px-2 py-1 font-medium text-notion-muted whitespace-nowrap">意图</th>
                <th className="px-2 py-1 font-medium text-notion-muted whitespace-nowrap">RFM</th>
                <th className="px-2 py-1 font-medium text-notion-muted whitespace-nowrap text-right">L6M</th>
                <th className="px-2 py-1 font-medium text-notion-muted whitespace-nowrap text-right">L1Y</th>
                <th className="px-2 py-1 font-medium text-notion-muted whitespace-nowrap text-right">退款</th>
                <th className="px-2 py-1 font-medium text-notion-muted whitespace-nowrap">购买</th>
                <th className="px-2 py-1 font-medium text-notion-muted whitespace-nowrap">兴趣</th>
                <th className="px-2 py-1 font-medium text-notion-muted whitespace-nowrap">痛点</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-notion-border">
              {displayCustomers.map((customer) => (
                <tr
                  key={customer.buyer_nick}
                  onClick={() => onRowAction?.(customer, 'view_details')}
                  className="hover:bg-notion-hover cursor-pointer transition-colors"
                >
                  {/* 客户信息 */}
                  <td className="px-3 py-1">
                    <div className="flex flex-col gap-0.5">
                      <span className="font-medium text-notion-text truncate max-w-[120px]" title={customer.buyer_nick}>
                        {customer.buyer_nick}
                      </span>
                      <div className="flex items-center gap-1">
                        <NotionTag
                          text={customer.channel}
                          color={customer.channel === 'DTC' ? 'blue' : 'green'}
                          size="xs"
                        />
                        <NotionTag
                          text={customer.buyer_type}
                          color={customer.buyer_type === 'SMOKER' ? 'orange' : customer.buyer_type === 'BOTH' ? 'red' : 'blue'}
                          size="xs"
                        />
                      </div>
                    </div>
                  </td>

                  {/* 优先级 */}
                  <td className="px-2 py-1">
                    <NotionTag
                      text={customer.follow_priority || 'N/A'}
                      color={getPriorityColor(customer.follow_priority || '')}
                      size="xs"
                    />
                  </td>

                  {/* 情感 */}
                  <td className="px-2 py-1">
                    <NotionTag
                      text={customer.sentiment_label || 'N/A'}
                      color={getSentimentColor(customer.sentiment_label || '')}
                      size="xs"
                    />
                  </td>

                  {/* 意图 */}
                  <td className="px-2 py-1">
                    <span className="text-notion-muted" title={customer.dominant_intent || ''}>
                      {truncateText(customer.dominant_intent, 8)}
                    </span>
                  </td>

                  {/* RFM分层 */}
                  <td className="px-2 py-1">
                    <span className="text-notion-muted" title={customer.rfm_segment || ''}>
                      {truncateText(customer.rfm_segment, 6)}
                    </span>
                  </td>

                  {/* L6M NetSales */}
                  <td className="px-2 py-1 text-right">
                    <span className="font-mono text-notion-text" title={`L6M NetSales: ¥${customer.l6m_netsales?.toLocaleString() || 0}`}>
                      {formatCurrency(customer.l6m_netsales)}
                    </span>
                  </td>

                  {/* L1Y NetSales */}
                  <td className="px-2 py-1 text-right">
                    <span className="font-mono text-notion-text" title={`L1Y NetSales: ¥${customer.l1y_netsales?.toLocaleString() || 0}`}>
                      {formatCurrency(customer.l1y_netsales)}
                    </span>
                  </td>

                  {/* 退款率 */}
                  <td className="px-2 py-1 text-right">
                    <span
                      className={`font-mono ${(customer.l1y_refund_rate || 0) > 0.1 ? 'text-red-600' : 'text-notion-muted'}`}
                      title={`退款率: ${((customer.l1y_refund_rate || 0) * 100).toFixed(1)}%`}
                    >
                      {formatPercent(customer.l1y_refund_rate)}
                    </span>
                  </td>

                  {/* 最后购买日期 */}
                  <td className="px-2 py-1">
                    <span className="text-notion-muted" title={`最后购买: ${customer.last_purchase_date || 'N/A'}`}>
                      {formatDate(customer.last_purchase_date)}
                    </span>
                  </td>

                  {/* Key Interest */}
                  <td className="px-2 py-1">
                    <span
                      className="text-notion-text line-clamp-1 max-w-[80px] block"
                      title={parseJsonArray(customer.persona_key_interests).join('; ')}
                    >
                      {parseJsonArray(customer.persona_key_interests)[0] || '-'}
                    </span>
                  </td>

                  {/* Pain Point */}
                  <td className="px-2 py-1">
                    <span
                      className="text-notion-text line-clamp-1 max-w-[80px] block"
                      title={parseJsonArray(customer.persona_pain_points).join('; ')}
                    >
                      {parseJsonArray(customer.persona_pain_points)[0] || '-'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : !isLoading ? (
        <EmptyState
          title="暂无符合条件的客户"
          description="尝试调整筛选条件"
        />
      ) : null}
    </NotionCard>
  );
};

// ========== 子组件: 筛选面板 ==========
interface FilterPanelProps {
  tempFilters: PriorityCustomersFilters;
  setTempFilters: React.Dispatch<React.SetStateAction<PriorityCustomersFilters>>;
  onApply: () => void;
  onReset: () => void;
  onClose: () => void;
}

const FilterPanel: React.FC<FilterPanelProps> = ({
  tempFilters,
  setTempFilters,
  onApply,
  onReset,
  onClose
}) => {
  const handleMultiSelect = (
    field: keyof PriorityCustomersFilters,
    value: string
  ) => {
    setTempFilters(prev => {
      // If "ALL" is selected, clear this filter
      if (value === 'ALL') {
        const newFilters = { ...prev };
        delete newFilters[field];
        return {
          ...newFilters,
          use_default_filter: false
        };
      }

      const currentValues = (prev[field] as string[]) || [];
      const newValues = currentValues.includes(value)
        ? currentValues.filter(v => v !== value)
        : [...currentValues, value];

      return {
        ...prev,
        [field]: newValues.length > 0 ? newValues : undefined,
        use_default_filter: false
      };
    });
  };

  const handleHasChatChange = (value: string) => {
    setTempFilters(prev => ({
      ...prev,
      has_chat: value === 'ALL' ? undefined : (value as 'true' | 'false'),
      use_default_filter: false
    }));
  };

  // Check if "ALL" should be selected for a field
  const isAllSelected = (field: keyof PriorityCustomersFilters) => {
    const values = tempFilters[field];
    return !values || (Array.isArray(values) && values.length === 0);
  };

  return (
    <div className="p-4 bg-notion-gray_bg/50 border-b border-notion-border animate-in slide-in-from-top-2">
      <div className="grid grid-cols-4 gap-4 mb-4">
        {/* 渠道筛选 */}
        <div>
          <label className="block text-xs font-medium text-notion-muted mb-2">渠道</label>
          <div className="flex flex-wrap gap-1">
            {CHANNEL_OPTIONS.map(opt => (
              <button
                key={opt.value}
                onClick={() => handleMultiSelect('channel', opt.value)}
                className={`px-2.5 py-1 text-xs rounded border transition-colors ${
                  (opt.value === 'ALL' && isAllSelected('channel')) ||
                  (opt.value !== 'ALL' && tempFilters.channel?.includes(opt.value as any))
                    ? 'bg-blue-100 text-blue-700 border-blue-300'
                    : 'bg-white text-notion-muted border-notion-border hover:border-gray-300'
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        {/* 买家类型筛选 */}
        <div>
          <label className="block text-xs font-medium text-notion-muted mb-2">买家类型</label>
          <div className="flex flex-wrap gap-1">
            {BUYER_TYPE_OPTIONS.map(opt => (
              <button
                key={opt.value}
                onClick={() => handleMultiSelect('buyer_type', opt.value)}
                className={`px-2.5 py-1 text-xs rounded border transition-colors ${
                  (opt.value === 'ALL' && isAllSelected('buyer_type')) ||
                  (opt.value !== 'ALL' && tempFilters.buyer_type?.includes(opt.value as any))
                    ? 'bg-blue-100 text-blue-700 border-blue-300'
                    : 'bg-white text-notion-muted border-notion-border hover:border-gray-300'
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        {/* 跟进优先级筛选 */}
        <div>
          <label className="block text-xs font-medium text-notion-muted mb-2">跟进优先级</label>
          <div className="flex flex-wrap gap-1">
            {FOLLOW_PRIORITY_OPTIONS.map(opt => (
              <button
                key={opt.value}
                onClick={() => handleMultiSelect('follow_priority', opt.value)}
                className={`px-2.5 py-1 text-xs rounded border transition-colors ${
                  (opt.value === 'ALL' && isAllSelected('follow_priority')) ||
                  (opt.value !== 'ALL' && tempFilters.follow_priority?.includes(opt.value as any))
                    ? 'bg-blue-100 text-blue-700 border-blue-300'
                    : 'bg-white text-notion-muted border-notion-border hover:border-gray-300'
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        {/* 聊天状态筛选 */}
        <div>
          <label className="block text-xs font-medium text-notion-muted mb-2">聊天状态</label>
          <div className="flex flex-wrap gap-1">
            {HAS_CHAT_OPTIONS.map(opt => (
              <button
                key={opt.value}
                onClick={() => handleHasChatChange(opt.value)}
                className={`px-2.5 py-1 text-xs rounded border transition-colors ${
                  (opt.value === 'ALL' && tempFilters.has_chat === undefined) ||
                  (opt.value !== 'ALL' && tempFilters.has_chat === opt.value)
                    ? 'bg-blue-100 text-blue-700 border-blue-300'
                    : 'bg-white text-notion-muted border-notion-border hover:border-gray-300'
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* 操作按钮 */}
      <div className="flex items-center justify-between pt-3 border-t border-notion-border">
        <button
          onClick={onReset}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-notion-muted hover:text-notion-text transition-colors"
        >
          <RefreshCw size={12} />
          重置
        </button>
        <div className="flex items-center gap-2">
          <button
            onClick={onClose}
            className="px-3 py-1.5 text-xs text-notion-muted hover:text-notion-text transition-colors"
          >
            取消
          </button>
          <button
            onClick={onApply}
            className="px-4 py-1.5 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
          >
            应用筛选
          </button>
        </div>
      </div>
    </div>
  );
};
