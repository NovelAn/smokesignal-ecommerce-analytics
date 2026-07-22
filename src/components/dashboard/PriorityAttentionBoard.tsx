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
  BadgeAlert,
} from 'lucide-react';
import { NotionCard } from '../common/NotionCard';
import { NotionTag } from '../common/NotionTag';
import { TableSkeleton } from '../common/LoadingState';
import { ErrorAlert, EmptyState } from '../common/ErrorAlert';
import { ConfirmDialog } from '../common/ConfirmDialog';
import { StatusButtonGroup } from '../common/StatusButtonGroup';
import {
  apiClient,
  PriorityCustomer,
  PriorityCustomersFilters,
  PriorityCustomersResponse,
  ServiceStatus,
  ChurnWarningRow,
} from '../../api/client';
import { useDataFetchingWithRetry } from '../../hooks/useDataFetching';

const UNDO_WINDOW_MS = 30_000;

const STATUS_LABEL: Record<ServiceStatus, string> = {
  pending: '未处理',
  contacted: '已触达',
  resolved: '已解决',
};

// ========== Churn row helper (流失预警 Tab 行内单元格) ==========

function getChurnRiskColor(risk: string): 'red' | 'orange' | 'green' {
  if (risk === '高') return 'red';
  if (risk === '中') return 'orange';
  return 'green';
}

// RFM segment 等级排名 (M*R*F 越高的 segment 越重要)
const SEGMENT_RANK: Record<string, number> = {
  '重要价值客户': 100, '重要保持客户': 90, '重要发展客户': 85, '重要挽留客户': 70,
  '优质价值客户': 80, '优质保持客户': 75, '优质发展客户': 70, '优质挽留客户': 60,
  '潜力客户': 50, '待激活客户': 40, '新客户': 45,
  '低价值客户': 20, '已流失': 10, '无购买记录': 5,
};

// segment 退化的颜色: 跟 churn_risk 解耦, 按好段位→差段位严重度独立评估
function getSegmentDegradationColor(segOld: string, segNow: string): 'red' | 'orange' | 'yellow' | 'gray' {
  if (segOld === segNow) return 'gray';
  const oldRank = SEGMENT_RANK[segOld] ?? 30;
  const nowRank = SEGMENT_RANK[segNow] ?? 30;
  const drop = oldRank - nowRank;
  if (drop >= 60) return 'red';      // 重要类→已流失/低价值
  if (drop >= 20) return 'orange';    // 重要类→挽留/潜力
  return 'yellow';                    // 优质类→任何差 segment
}

// 入选原因 tag 颜色
function getSelectionReasonColor(reason: string): 'red' | 'orange' | 'purple' | 'gray' {
  if (reason === '情感转负') return 'red';
  if (reason === 'segment退化') return 'red';
  if (reason === 'churn高风险') return 'orange';
  if (reason === '购买力坍塌') return 'purple';
  return 'gray';
}

// 严重度档位的左侧色条 className
function getSeverityTierBar(tier: number): string {
  switch (tier) {
    case 1: return 'bg-red-600';
    case 2: return 'bg-orange-500';
    case 3: return 'bg-yellow-400';
    default: return 'bg-gray-300';
  }
}

// 严重度档位的左侧 border (Round 3 Bug #1 修复: 不用独立 td, 避免与 thead 列数对不上)
function getSeverityTierBorder(tier: number): string {
  switch (tier) {
    case 1: return 'border-l-red-600';
    case 2: return 'border-l-orange-500';
    case 3: return 'border-l-yellow-400';
    default: return 'border-l-gray-300';
  }
}

interface ChurnRowCellsProps {
  row: ChurnWarningRow;
  canUndo: boolean;
  customer: PriorityCustomer;
  onStatusChange: (customer: PriorityCustomer, newStatus: ServiceStatus) => void;
  onUndo: (buyer: PriorityCustomer) => void;
}

function ChurnRowCells({ row, canUndo, customer, onStatusChange, onUndo }: ChurnRowCellsProps) {
  const l6mChange = Number(row.l6m_netsales_change) || 0;
  const l6mPositive = l6mChange > 0;
  const l6mZero = l6mChange === 0;

  const reasons = row.selection_reasons ? row.selection_reasons.split(',').filter(Boolean) : [];
  return (
    <>
      {/* 客户信息 (复用优先级 tab 的样式) - 严重度色条改为 border-l, 避免与 thead 列数对不上 (Bug #1) */}
      <td className={'px-3 py-1 border-l-4 ' + getSeverityTierBorder(row.severity_tier)}>
        <div className="flex flex-col gap-0.5">
          <span className="font-medium text-notion-text truncate max-w-[120px]" title={row.buyer_nick}>
            {row.buyer_nick}
          </span>
          <div className="flex items-center gap-1">
            <NotionTag text={row.channel} color={row.channel === 'DTC' ? 'blue' : 'green'} size="xs" />
            <NotionTag
              text={row.buyer_type}
              color={row.buyer_type === 'SMOKER' ? 'orange' : row.buyer_type === 'BOTH' ? 'red' : row.buyer_type === 'SEASON' ? 'green' : row.buyer_type === 'BULK' ? 'purple' : 'blue'}
              size="xs"
            />
          </div>
        </div>
      </td>

      {/* VIP 等级 */}
      <td className="px-2 py-1">
        <NotionTag
          text={row.vip_level || 'N/A'}
          color={row.vip_level === 'V3' || row.vip_level === 'V2' ? 'red' : row.vip_level === 'V1' ? 'orange' : 'gray'}
          size="xs"
        />
      </td>

      {/* Segment 退化 (30D前 → 现在) */}
      <td className="px-2 py-1">
        <div className="flex items-center gap-1">
          <NotionTag text={row.segment_prev} color="green" size="xs" />
          <span className="text-red-500 text-xs">→</span>
          <NotionTag text={row.segment_now} color={getSegmentDegradationColor(row.segment_prev, row.segment_now)} size="xs" />
        </div>
      </td>

      {/* 入选原因 */}
      <td className="px-2 py-1">
        <div className="flex flex-wrap gap-1">
          {reasons.length === 0 ? (
            <span className="text-notion-muted text-xs">-</span>
          ) : (
            reasons.map((r) => (
              <NotionTag key={r} text={r} color={getSelectionReasonColor(r)} size="xs" />
            ))
          )}
        </div>
      </td>

      {/* Churn 升级 (30D前 → 现在) */}
      <td className="px-2 py-1">
        <div className="flex items-center gap-1">
          <NotionTag text={row.churn_risk_prev} color={getChurnRiskColor(row.churn_risk_prev)} size="xs" />
          <span className="text-red-500 text-xs">→</span>
          <NotionTag text={row.churn_risk_now} color={getChurnRiskColor(row.churn_risk_now)} size="xs" />
        </div>
      </td>

      {/* L6M NetSales 变化 */}
      <td className="px-2 py-1 text-right">
        <span
          className={`font-mono ${
            l6mZero
              ? 'text-notion-muted'
              : l6mPositive
              ? 'text-green-600'
              : 'text-red-600'
          }`}
          title={`L6M NetSales 30天变化: ${l6mChange.toLocaleString()}`}
        >
          {l6mZero ? '-' : `${l6mPositive ? '▲' : '▼'} ¥${Math.abs(l6mChange).toLocaleString()}`}
        </span>
      </td>

      {/* 最后购买日期 */}
      <td className="px-2 py-1">
        <span className="text-notion-muted" title={`最后购买: ${row.last_purchase_date || 'N/A'}`}>
          {row.last_purchase_date ? row.last_purchase_date.split('T')[0] : 'N/A'}
        </span>
      </td>

      {/* 操作 - 复用 StatusButtonGroup（流失客户跟进也要 mark）*/}
      <td className="px-2 py-1" onClick={(e) => e.stopPropagation()}>
        <StatusButtonGroup
          buyer={customer}
          onChange={(newStatus) => onStatusChange(customer, newStatus)}
          canUndo={canUndo}
          onUndo={() => onUndo(customer)}
        />
      </td>
    </>
  );
}

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
  { value: 'SEASON', label: 'Season' },
  { value: 'BULK', label: 'Bulk' },
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
    urgent: 'red',
    high: 'orange',
    medium: 'yellow',
    low: 'gray',
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

function formatRefreshReason(customer: PriorityCustomer): string {
  const reasons: string[] = [];
  if (customer.persona_refresh_required) {
    if (customer.persona_analyzed_last_purchase_date && customer.last_purchase_date > customer.persona_analyzed_last_purchase_date) {
      reasons.push('有新订单');
    }
    if (customer.persona_analyzed_last_chat_date && customer.last_chat_date && customer.last_chat_date > customer.persona_analyzed_last_chat_date) {
      reasons.push('有新聊天');
    }
    if (reasons.length === 0) reasons.push('画像时间早于最新数据');
  }
  return reasons.join(' / ');
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
  onRowAction?: (buyer: PriorityCustomer, actionType: string, currentPage: number) => void;
  /** Back to Overview 时高亮的买家 */
  highlightBuyerNick?: string | null;
  /** 高亮买家所在的页码（Back 时跳回） */
  highlightBuyerPage?: number;
  /** 高亮 5 秒后清除 */
  onClearClickedHighlight?: () => void;
  /** 触发器：Back to Overview 时自增，强制 useEffect 重跑（即使 buyer 相同） */
  highlightTrigger?: number;
  /** App 级 activeTab — 仅在 === 'overview' 时才跑 scroll + timer 逻辑 */
  appActiveTab?: string;
}

export const PriorityAttentionBoard: React.FC<PriorityAttentionBoardProps> = ({
  onRowAction,
  highlightBuyerNick = null,
  highlightBuyerPage = 1,
  onClearClickedHighlight,
  highlightTrigger = 0,
  appActiveTab,
}) => {
  // ========== 状态管理 ==========
  const [activeTab, setActiveTab] = useState<'priority' | 'churn'>('priority');
  // Round 3: 流失预警对比周期可配置 (60/90/180)
  const [churnWindowDays, setChurnWindowDays] = useState<60 | 90 | 180>(90);
  const [currentPage, setCurrentPage] = useState(1);
  // 内部 trigger: 数据加载完后自增, 强制 scroll useEffect 重跑
  const [scrollTrigger, setScrollTrigger] = useState(0);

  // 筛选状态
  const [filters, setFilters] = useState<PriorityCustomersFilters>({
    use_default_filter: true
  });

  // 临时筛选状态
  const [tempFilters, setTempFilters] = useState<PriorityCustomersFilters>(filters);
  const [showFilterPanel, setShowFilterPanel] = useState(false);

  // 批量选择（Round 1 CRM 误触保护）
  const [selectedNicks, setSelectedNicks] = useState<Set<string>>(new Set());

  // 确认弹窗（用于 contacted / resolved 切换的二次确认）
  const [confirmDialog, setConfirmDialog] = useState<{
    title: string;
    message: string;
    onConfirm: () => void;
  } | null>(null);

  // 30 秒撤销（最近一次 mark）
  const [undoState, setUndoState] = useState<{
    buyerNick: string;
    previousStatus: ServiceStatus;
    expiresAt: number;
  } | null>(null);
  const undoTimerRef = useRef<NodeJS.Timeout | null>(null);

  // 卸载清理 undo timer
  useEffect(() => {
    return () => {
      if (undoTimerRef.current) clearTimeout(undoTimerRef.current);
    };
  }, []);

  // ========== Round 1: Back to Overview 高亮定位 ==========
  const rowRefs = useRef<Map<string, HTMLTableRowElement>>(new Map());
  const highlightTimerRef = useRef<NodeJS.Timeout | null>(null);
  // 跟踪 customers 长度, 避免 scroll useEffect 提前用 customers (TDZ)
  const customersLenRef = useRef(0);
  // 整个 PriorityAttentionBoard 的容器 ref — 用作外层 main 滚动的目标点
  // 解决 tr 嵌套在 max-h-[400px] overflow-y-auto 内层时 scrollIntoView 只能滚内层的问题
  const boardRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!highlightBuyerNick) return;
    // Bug #3 修复: 移除 '只 priority tab 触发' 的 gate, churn tab 也要支持 scroll 回原位
    // (用户场景: 在 priority tab 点了客户 A -> ChatAnalysis -> Back to Overview,
    //  如果 activeTab 状态被之前的 churn tab 操作污染, 必须仍能滚到 A)
    // 关键 gate：只有用户当前在 Overview 时才跑 scroll + 启动 timer
    // 否则原始 click 时 effect 也会跑（deps highlightBuyerNick 变了），
    // rowRef 一直挂着，5s timer 会在 ChatAnalysis 页面上 fire 把 highlightBuyerNick 清掉
    if (appActiveTab !== 'overview') return;

    let boardTimer: NodeJS.Timeout | null = null;
    let rowTimer: NodeJS.Timeout | null = null;
    let boardRetry = 0;
    let rowRetry = 0;
    const MAX_RETRY = 40; // 最多重试 2 秒 (40 * 50ms), 兜底慢加载

    // 两步滚动：
    //  1. boardRef.scrollIntoView — 把外层 main 滚到 PriorityAttentionBoard 顶部
    //     (tr 嵌套在 max-h-[400px] 内部 scrollable，单纯 tr.scrollIntoView 只滚内层)
    //  2. 等外层滚动稳定后，tr.scrollIntoView — 把内层表格滚到该行
    function tryBoardScroll() {
      const board = boardRef.current;
      if (board) {
        board.scrollIntoView({ behavior: 'smooth', block: 'start' });
        boardRetry = MAX_RETRY;
        // 给外层 smooth scroll 留时间（通常 200-400ms），再尝试滚内层 tr
        rowTimer = setTimeout(tryRowScroll, 400);
      } else if (boardRetry < MAX_RETRY) {
        boardRetry++;
        boardTimer = setTimeout(tryBoardScroll, 50);
      } else {
        // board 始终未挂上，直接尝试 row scroll
        rowTimer = setTimeout(tryRowScroll, 50);
      }
    }

    function startHighlightTimer() {
      // 关键：5s 计时只在「行已 scrollIntoView 成功」之后启动，
      // 不在 effect 触发时启动。否则用户在 ChatAnalysis 浏览子 tab 超过 5s，
      // timer 会在 ChatAnalysis 页面上 fire 把 highlightBuyerNick 清掉，
      // 回到 overview 时 useEffect 跑到 if (!highlightBuyerNick) return 提前 return。
      if (highlightTimerRef.current) clearTimeout(highlightTimerRef.current);
      highlightTimerRef.current = setTimeout(() => {
        onClearClickedHighlight?.();
        highlightTimerRef.current = null;
      }, 5_000);
    }

    function tryRowScroll() {
      const el = rowRefs.current.get(highlightBuyerNick!);
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        rowRetry = MAX_RETRY;
        startHighlightTimer();
      } else if (rowRetry < MAX_RETRY) {
        rowRetry++;
        rowTimer = setTimeout(tryRowScroll, 50);
      }
    }

    // 1. 跳到目标页（如果不同）
    if (highlightBuyerPage && highlightBuyerPage !== currentPage) {
      setCurrentPage(highlightBuyerPage);
      // 给翻页 + data 加载 + DOM 重新挂载留时间，再开始 board 滚动
      boardTimer = setTimeout(tryBoardScroll, 350);
    } else {
      // 立即尝试 board 滚动
      boardTimer = setTimeout(tryBoardScroll, 50);
    }

    return () => {
      if (boardTimer) clearTimeout(boardTimer);
      if (rowTimer) clearTimeout(rowTimer);
      // 注意: 不 clear highlightTimerRef — 让 timer 自己跑完或下次 useEffect 重入时清
    };
  }, [highlightBuyerNick, highlightBuyerPage, activeTab, onClearClickedHighlight, highlightTrigger, appActiveTab, scrollTrigger]);
  //  ↑ 移除 currentPage（避免 setCurrentPage 触发 effect re-run 导致 cleanup）
  //  ↑ 加 activeTab（priority tab 切回时重跑 highlight）

  // ========== 数据获取（按 activeTab 切换 API）==========
  const fetchCustomers = useCallback(async () => {
    const offset = (currentPage - 1) * PAGE_SIZE;
    if (activeTab === 'churn') {
      // 流失预警 (Round 3): windowDays 控制对比周期 (60/90/180)
      const churnResp = await apiClient.getChurnWarning({
        window: churnWindowDays,
        limit: PAGE_SIZE,
        offset,
      });
      return {
        ...churnResp,
        customers: churnResp.data as unknown as PriorityCustomer[],
      } as PriorityCustomersResponse;
    }
    return apiClient.getPriorityCustomers({
      ...filters,
      limit: PAGE_SIZE,
      offset
    });
  }, [currentPage, filters, activeTab, churnWindowDays]);

  const {
    data: response,
    isLoading,
    error,
    refetch
  } = useDataFetchingWithRetry<PriorityCustomersResponse>(
    fetchCustomers,
    2,
    [currentPage, filters, activeTab, churnWindowDays]
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

  // 保留之前的客户数据用于平滑过渡
  const prevCustomersRef = useRef<PriorityCustomer[]>([]);
  const customers = response?.customers || [];
  const hasData = customers.length > 0;
  // Bug 修复: 数据加载完后自增 scrollTrigger, 触发 scroll useEffect 重跑
  const prevCustomersLenRef = useRef(0);
  useEffect(() => {
    if (customers.length > prevCustomersLenRef.current && highlightBuyerNick) {
      // 触发 scroll effect 重跑: 通过自增 navigationToken-like trigger
      setScrollTrigger((prev) => prev + 1);
    }
    prevCustomersLenRef.current = customers.length;
  }, [customers.length, highlightBuyerNick]);

  // 当有新数据时，更新ref
  useEffect(() => {
    if (customers.length > 0) {
      prevCustomersRef.current = customers;
    }
  }, [customers]);

  // 显示的数据：加载时用之前的数据，否则用当前数据
  const rawDisplayCustomers = isLoading && prevCustomersRef.current.length > 0
    ? prevCustomersRef.current
    : customers;

  // Bug #2 修复: churn tab 客户端 filter (后端 churn-warning API 暂不支持 filter, 客户端过滤避免再发请求)
  const displayCustomers = useMemo(() => {
    if (activeTab !== 'churn' || filters.use_default_filter !== false) {
      return rawDisplayCustomers;
    }
    return rawDisplayCustomers.filter((c) => {
      if (filters.channel?.length && !filters.channel.includes(c.channel)) return false;
      if (filters.buyer_type?.length && !filters.buyer_type.includes(c.buyer_type)) return false;
      return true;
    });
  }, [rawDisplayCustomers, activeTab, filters]);

  const handleExportCSV = useCallback(() => {
    const url = apiClient.getPriorityCustomersCSVUrl(filters);
    window.open(url, '_blank');
  }, [filters]);

  // ========== Round 1 CRM: 客服操作 handlers ==========

  /** 清除单行撤销状态（数据刷新后失效） */
  const clearUndoIfStale = useCallback(() => {
    setUndoState(prev => {
      if (prev && Date.now() >= prev.expiresAt) return null;
      return prev;
    });
  }, []);

  /** 单行状态切换入口：弹 confirm 或直接调 API */
  const handleStatusChange = useCallback(
    (buyer: PriorityCustomer, newStatus: ServiceStatus) => {
      const prev = (buyer.service_status || 'pending') as ServiceStatus;
      if (newStatus === prev) return;

      const doMark = () => performMark(buyer, newStatus, prev);

      // 改回 pending 不弹 confirm（兜底状态，可随时撤销）
      if (newStatus === 'pending') {
        doMark();
        return;
      }
      // 切到 contacted / resolved 弹 confirm
      setConfirmDialog({
        title: `标记「${buyer.buyer_nick}」为「${STATUS_LABEL[newStatus]}」？`,
        message: '标记后该客户将退出当前 tracking list（除非发生 reactivation 事件，如新增负面聊天/退款/RFM 退化）。30 秒内可点击撤销。',
        onConfirm: () => {
          setConfirmDialog(null);
          doMark();
        },
      });
    },
    [],
  );

  /** 实际调 API + 写入 undoState */
  const performMark = useCallback(
    async (buyer: PriorityCustomer, newStatus: ServiceStatus, previousStatus: ServiceStatus) => {
      try {
        const resp = await apiClient.markService({
          buyer_nick: buyer.buyer_nick,
          status: newStatus,
        });
        // 设置 30 秒撤销窗口
        if (undoTimerRef.current) clearTimeout(undoTimerRef.current);
        const expiresAt = Date.now() + UNDO_WINDOW_MS;
        setUndoState({
          buyerNick: buyer.buyer_nick,
          previousStatus: (resp.previous_status || previousStatus) as ServiceStatus,
          expiresAt,
        });
        undoTimerRef.current = setTimeout(() => {
          setUndoState(null);
          undoTimerRef.current = null;
        }, UNDO_WINDOW_MS);
        await refetch();
      } catch (err: unknown) {
        // 网络/服务端错误 — 不弹 modal，避免中断客服流程
        // 简单通过 console 报错（生产应接 logger）
        console.error('[markService] 失败', err);
        await refetch();
      }
    },
    [refetch],
  );

  /** 撤销上一次 mark */
  const handleUndo = useCallback(
    async (buyer: PriorityCustomer) => {
      if (!undoState || undoState.buyerNick !== buyer.buyer_nick) return;
      if (Date.now() >= undoState.expiresAt) {
        setUndoState(null);
        return;
      }
      const previous = undoState.previousStatus;
      if (undoTimerRef.current) clearTimeout(undoTimerRef.current);
      undoTimerRef.current = null;
      setUndoState(null);
      try {
        await apiClient.markService({
          buyer_nick: buyer.buyer_nick,
          status: previous,
        });
        await refetch();
      } catch (err: unknown) {
        console.error('[markService undo] 失败', err);
        await refetch();
      }
    },
    [undoState, refetch],
  );

  /** 批量 mark 入口：弹 confirm 一次 */
  const handleBatchMark = useCallback(
    (status: ServiceStatus) => {
      const nicks = Array.from(selectedNicks);
      if (nicks.length === 0) return;

      const doBatch = async () => {
        try {
          const resp = await apiClient.batchMarkService({
            buyer_nicks: nicks,
            status,
          });
          // 批量后清除选择 + 撤销状态 + 刷新
          setSelectedNicks(new Set());
          setUndoState(null);
          if (undoTimerRef.current) clearTimeout(undoTimerRef.current);
          await refetch();
          // partial 失败提示（Round1 简化：alert）
          if (resp.failed.length > 0) {
            alert(`批量标记完成：${resp.affected_rows} 成功，${resp.failed.length} 失败\n失败客户：${resp.failed.join(', ')}`);
          }
        } catch (err: unknown) {
          console.error('[batchMarkService] 失败', err);
          await refetch();
        }
      };

      if (status === 'pending') {
        // 批量改回 pending 直接执行（兜底）
        doBatch();
        return;
      }
      setConfirmDialog({
        title: `批量将 ${nicks.length} 个客户标记为「${STATUS_LABEL[status]}」？`,
        message: '这些客户将退出当前 tracking list（除非发生 reactivation 事件）。',
        onConfirm: () => {
          setConfirmDialog(null);
          doBatch();
        },
      });
    },
    [selectedNicks, refetch],
  );

  /** 单行 checkbox 切换 */
  const toggleSelect = useCallback((buyerNick: string) => {
    setSelectedNicks(prev => {
      const next = new Set(prev);
      if (next.has(buyerNick)) next.delete(buyerNick);
      else next.add(buyerNick);
      return next;
    });
  }, []);

  /** 表头全选/反选 */
  const toggleSelectAll = useCallback(() => {
    setSelectedNicks(prev => {
      const allSelected = displayCustomers.every(c => prev.has(c.buyer_nick));
      if (allSelected) return new Set();
      return new Set(displayCustomers.map(c => c.buyer_nick));
    });
  }, [displayCustomers]);

  const clearSelection = useCallback(() => {
    setSelectedNicks(new Set());
  }, []);

  // 数据刷新时清理过期的撤销状态
  useEffect(() => {
    clearUndoIfStale();
  }, [response, clearUndoIfStale]);

  // ========== 渲染 ==========
  return (
    <div ref={boardRef}>
    <NotionCard
      className="overflow-hidden"
      icon={AlertTriangle}
      title={activeTab === 'priority' ? '需优先跟进的客户' : '流失预警'}
      subtitle={activeTab === 'priority'
        ? `${response?.total || 0} 位客户 | ${response?.analysis_version === 'v2' ? 'AI V2：情感 + 具体问题优先级' : 'AI V1：紧急/高优先级 或负面情感'}`
        : (() => {
            const floor = churnWindowDays === 60 ? '1万' : churnWindowDays === 90 ? '1.5万' : '2万';
            return `segment/churn 退化、情感转负，或购买力下降 ≥ 50% 且 ${churnWindowDays} 天前 l6m ≥ ${floor}`;
          })()}
      action={
        <div className="flex items-center gap-3">
          {/* 批量工具栏 - Round 1 CRM 误触保护 */}
          {selectedNicks.size > 0 && (
            <div className="flex items-center gap-2 px-2 py-1 bg-blue-50 border border-blue-200 rounded text-xs">
              <span className="text-blue-700 font-medium">已选 {selectedNicks.size} 个</span>
              <button
                onClick={() => handleBatchMark('contacted')}
                className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded hover:bg-blue-200 transition-colors"
              >
                批量标为已触达
              </button>
              <button
                onClick={() => handleBatchMark('resolved')}
                className="px-2 py-0.5 bg-green-100 text-green-700 rounded hover:bg-green-200 transition-colors"
              >
                批量标为已解决
              </button>
              <button
                onClick={() => handleBatchMark('pending')}
                className="px-2 py-0.5 bg-gray-100 text-gray-700 rounded hover:bg-gray-200 transition-colors"
              >
                批量改回未处理
              </button>
              <button
                onClick={clearSelection}
                className="px-2 py-0.5 text-notion-muted hover:text-notion-text transition-colors"
                title="取消所有选择"
              >
                ✕
              </button>
            </div>
          )}
          {/* Tab Bar - Round 1 */}
          <div className="flex bg-gray-100 rounded-md p-0.5">
            <button
              onClick={() => { setActiveTab('priority'); setCurrentPage(1); }}
              className={`px-3 py-1 text-xs rounded transition-colors ${activeTab === 'priority' ? 'bg-white text-gray-900 shadow-sm font-medium' : 'text-gray-600 hover:text-gray-800'}`}
            >需优先跟进</button>
            <button
              onClick={() => { setActiveTab('churn'); setCurrentPage(1); }}
              className={`px-3 py-1 text-xs rounded transition-colors ${activeTab === 'churn' ? 'bg-white text-gray-900 shadow-sm font-medium' : 'text-gray-600 hover:text-gray-800'}`}
            >流失预警</button>
          </div>
          {/* Round 3: 流失预警对比周期分段控件 - 仅 churn tab 显示 */}
          {activeTab === 'churn' && (
            <div className="flex bg-notion-gray_bg p-0.5 rounded-md border border-notion-border">
              {[60, 90, 180].map((d) => (
                <button
                  key={d}
                  onClick={() => { setChurnWindowDays(d as 60 | 90 | 180); setCurrentPage(1); }}
                  className={`px-2.5 py-1 text-xs font-medium rounded-sm transition-all ${
                    churnWindowDays === d
                      ? 'bg-white text-blue-700 shadow-sm border border-blue-100'
                      : 'text-notion-muted hover:text-notion-text'
                  }`}
                >
                  {d}D
                </button>
              ))}
            </div>
          )}
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
            {activeTab === 'priority' ? (
            <thead className="sticky top-0 z-20">
              <tr className="bg-white border-b border-notion-border text-left">
                <th className="px-2 py-1 w-8">
                  <input
                    type="checkbox"
                    checked={displayCustomers.length > 0 && displayCustomers.every(c => selectedNicks.has(c.buyer_nick))}
                    ref={(el) => {
                      if (el) {
                        const allSelected = displayCustomers.length > 0 && displayCustomers.every(c => selectedNicks.has(c.buyer_nick));
                        const someSelected = displayCustomers.some(c => selectedNicks.has(c.buyer_nick));
                        el.indeterminate = someSelected && !allSelected;
                      }
                    }}
                    onChange={toggleSelectAll}
                    className="cursor-pointer"
                    title="全选/反选当前页"
                  />
                </th>
                <th className="px-3 py-1 font-medium text-notion-muted whitespace-nowrap">客户</th>
                <th className="px-2 py-1 font-medium text-notion-muted whitespace-nowrap">优先级</th>
                <th className="px-2 py-1 font-medium text-notion-muted whitespace-nowrap">情感</th>
                <th className="px-2 py-1 font-medium text-notion-muted whitespace-nowrap">意图 / 主要问题</th>
                <th className="px-2 py-1 font-medium text-notion-muted whitespace-nowrap">RFM</th>
                <th className="px-2 py-1 font-medium text-notion-muted whitespace-nowrap">画像</th>
                <th className="px-2 py-1 font-medium text-notion-muted whitespace-nowrap text-right">L6M</th>
                <th className="px-2 py-1 font-medium text-notion-muted whitespace-nowrap text-right">L1Y</th>
                <th className="px-2 py-1 font-medium text-notion-muted whitespace-nowrap text-right">退款</th>
                <th className="px-2 py-1 font-medium text-notion-muted whitespace-nowrap">购买</th>
                <th className="px-2 py-1 font-medium text-notion-muted whitespace-nowrap">兴趣</th>
                <th className="px-2 py-1 font-medium text-notion-muted whitespace-nowrap">痛点</th>
                <th className="px-2 py-1 font-medium text-notion-muted whitespace-nowrap">操作</th>
              </tr>
            </thead>
            ) : (
            <thead className="sticky top-0 z-20">
              <tr className="bg-white border-b border-notion-border text-left">
                <th className="px-2 py-1 w-8">
                  <input
                    type="checkbox"
                    checked={displayCustomers.length > 0 && displayCustomers.every(c => selectedNicks.has(c.buyer_nick))}
                    ref={(el) => {
                      if (el) {
                        const allSelected = displayCustomers.length > 0 && displayCustomers.every(c => selectedNicks.has(c.buyer_nick));
                        const someSelected = displayCustomers.some(c => selectedNicks.has(c.buyer_nick));
                        el.indeterminate = someSelected && !allSelected;
                      }
                    }}
                    onChange={toggleSelectAll}
                    className="cursor-pointer"
                    title="全选/反选当前页"
                  />
                </th>
                <th className="px-3 py-1 font-medium text-notion-muted whitespace-nowrap">客户</th>
                <th className="px-2 py-1 font-medium text-notion-muted whitespace-nowrap">VIP</th>
                <th className="px-2 py-1 font-medium text-notion-muted whitespace-nowrap">Segment 变化</th>
                <th className="px-2 py-1 font-medium text-notion-muted whitespace-nowrap">入选原因</th>
                <th className="px-2 py-1 font-medium text-notion-muted whitespace-nowrap">Churn 升级</th>
                <th className="px-2 py-1 font-medium text-notion-muted whitespace-nowrap text-right">L6M 变化</th>
                <th className="px-2 py-1 font-medium text-notion-muted whitespace-nowrap">最后购买</th>
                <th className="px-2 py-1 font-medium text-notion-muted whitespace-nowrap">操作</th>
              </tr>
            </thead>
            )}
            <tbody className="divide-y divide-notion-border">
              {displayCustomers.map((customer) => {
                const canUndo = undoState?.buyerNick === customer.buyer_nick && Date.now() < undoState.expiresAt;
                const churnRow = activeTab === 'churn' ? (customer as unknown as ChurnWarningRow) : null;
                return (
                <tr
                  key={customer.buyer_nick}
                  ref={(el) => {
                    if (el) rowRefs.current.set(customer.buyer_nick, el);
                    else rowRefs.current.delete(customer.buyer_nick);
                  }}
                  onClick={() => onRowAction?.(customer, 'view_details', currentPage)}
                  className={`hover:bg-notion-hover cursor-pointer transition-colors ${
                    highlightBuyerNick === customer.buyer_nick
                      ? 'bg-yellow-50 ring-2 ring-yellow-400 animate-pulse'
                      : ''
                  }`}
                >
                  {/* checkbox - Round 1 CRM */}
                  <td className="px-2 py-1 w-8" onClick={(e) => e.stopPropagation()}>
                    <input
                      type="checkbox"
                      checked={selectedNicks.has(customer.buyer_nick)}
                      onChange={() => toggleSelect(customer.buyer_nick)}
                      className="cursor-pointer"
                    />
                  </td>
                  {churnRow ? (
                    <ChurnRowCells row={churnRow} canUndo={canUndo} customer={customer} onStatusChange={handleStatusChange} onUndo={handleUndo} />
                  ) : (
                  <>
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
                          color={customer.buyer_type === 'SMOKER' ? 'orange' : customer.buyer_type === 'BOTH' ? 'red' : customer.buyer_type === 'SEASON' ? 'green' : customer.buyer_type === 'BULK' ? 'purple' : 'blue'}
                          size="xs"
                        />
                      </div>
                    </div>
                  </td>

                  {/* 优先级 */}
                  <td className="px-2 py-1">
                    <NotionTag
                      text={customer.attention_priority || customer.follow_priority || 'N/A'}
                      color={getPriorityColor(customer.attention_priority || customer.follow_priority || '')}
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
                    <span className="text-notion-muted" title={customer.primary_issue_detail || customer.dominant_intent || ''}>
                      {truncateText(customer.primary_issue_detail || customer.primary_issue_code || customer.dominant_intent, 12)}
                    </span>
                  </td>

                  {/* RFM分层 */}
                  <td className="px-2 py-1">
                    <span className="text-notion-muted" title={customer.rfm_segment || ''}>
                      {truncateText(customer.rfm_segment, 6)}
                    </span>
                  </td>

                  <td className="px-2 py-1">
                    {customer.persona_refresh_required ? (
                      <span
                        className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] border border-orange-200 bg-orange-50 text-orange-700 whitespace-nowrap"
                        title={formatRefreshReason(customer)}
                      >
                        <BadgeAlert size={10} />
                        待刷新
                      </span>
                    ) : (
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] border border-green-200 bg-green-50 text-green-700 whitespace-nowrap">
                        已更新
                      </span>
                    )}
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
                      className="text-notion-text line-clamp-2 max-w-[140px] block text-[10px] leading-tight"
                      title={parseJsonArray(customer.persona_key_interests).join('; ')}
                    >
                      {parseJsonArray(customer.persona_key_interests).slice(0, 3).join(', ') || '-'}
                    </span>
                  </td>

                  {/* Pain Point */}
                  <td className="px-2 py-1">
                    <span
                      className="text-notion-text line-clamp-2 max-w-[140px] block text-[10px] leading-tight"
                      title={parseJsonArray(customer.persona_pain_points).join('; ')}
                    >
                      {parseJsonArray(customer.persona_pain_points).slice(0, 3).join(', ') || '-'}
                    </span>
                  </td>
                  {/* 操作 - Round 1 CRM: 按钮组 + 30秒撤销 */}
                  <td className="px-2 py-1" onClick={(e) => e.stopPropagation()}>
                    <StatusButtonGroup
                      buyer={customer}
                      onChange={(newStatus) => handleStatusChange(customer, newStatus)}
                      canUndo={canUndo}
                      onUndo={() => handleUndo(customer)}
                    />
                  </td>
                  </>
                  )}
                </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : !isLoading ? (
        <EmptyState
          title="暂无符合条件的客户"
          description="尝试调整筛选条件"
        />
      ) : null}

      {/* 确认弹窗 - Round 1 CRM 误触保护 */}
      {confirmDialog && (
        <ConfirmDialog
          open={!!confirmDialog}
          title={confirmDialog.title}
          message={confirmDialog.message}
          confirmText="确认标记"
          cancelText="取消"
          confirmVariant="danger"
          onConfirm={confirmDialog.onConfirm}
          onCancel={() => setConfirmDialog(null)}
        />
      )}
    </NotionCard>
    </div>
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
  // Bug #4 修复: 当所有筛选字段都为空时 use_default_filter 应回到 true (避免显示 527 全量)
  const computeUseDefaultFilter = (filters: PriorityCustomersFilters): boolean => {
    const filterFields: (keyof PriorityCustomersFilters)[] = [
      'channel', 'buyer_type', 'follow_priority', 'sentiment_label'
    ];
    const hasAny = filterFields.some(f => {
      const v = filters[f];
      return Array.isArray(v) ? v.length > 0 : !!v;
    });
    if (hasAny) return false;
    if (filters.has_chat && filters.has_chat !== 'all') return false;
    return true;
  };

  const handleMultiSelect = (
    field: keyof PriorityCustomersFilters,
    value: string
  ) => {
    setTempFilters(prev => {
      const next: PriorityCustomersFilters = { ...prev };
      if (value === 'ALL') {
        delete next[field];
      } else {
        const currentValues = (prev[field] as string[]) || [];
        const newValues = currentValues.includes(value)
          ? currentValues.filter(v => v !== value)
          : [...currentValues, value];
        (next as Record<string, unknown>)[field] = newValues.length > 0 ? newValues : undefined;
        if (newValues.length === 0) delete next[field];
      }
      next.use_default_filter = computeUseDefaultFilter(next);
      return next;
    });
  };

  const handleHasChatChange = (value: string) => {
    setTempFilters(prev => {
      const next = {
        ...prev,
        has_chat: value === 'ALL' ? undefined : (value as 'true' | 'false'),
      };
      next.use_default_filter = computeUseDefaultFilter(next);
      return next;
    });
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
