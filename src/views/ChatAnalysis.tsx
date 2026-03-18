import React, { useState, useMemo, useEffect } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  ZAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  Legend,
  Layer,
  Rectangle,
  LabelList
} from 'recharts';
import {
  LayoutDashboard,
  MessageSquare,
  Settings,
  Search,
  Users,
  AlertCircle,
  TrendingUp,
  Package,
  Menu,
  X,
  User,
  MapPin,
  DollarSign,
  ShoppingBag,
  Percent,
  Clock,
  Calendar,
  ChevronRight,
  ChevronDown,
  Database,
  Terminal,
  Filter,
  Sparkles,
  Target,
  MessageCircle,
  ThumbsUp,
  ThumbsDown,
  Activity,
  Lightbulb,
  CreditCard,
  Truck,
  CheckCircle,
  XCircle,
  History,
  Download,
  AlertTriangle,
  PieChart as PieIcon,
  BarChart as BarChartIcon,
  Info,
  Award,
  Gauge
} from 'lucide-react';
import {
  KEYWORD_DATA,
  INTENT_DISTRIBUTION,
  HOURLY_ACTIVITY,
  DAILY_STATS,
  MOCK_SESSIONS,
} from '../constants';
import { BuyerSession, CustomerProfile, ChatMessage, OrderRecord, IntentType } from '../types';
import { apiClient, DashboardMetrics, BuyerProfile as APIBuyerProfile } from '../api/client';
import { useDataFetchingWithRetry } from '../hooks/useDataFetching';
import { LoadingSpinner, CardSkeleton, TableSkeleton, MetricCardSkeleton } from '../components/common/LoadingState';
import { ErrorAlert, EmptyState } from '../components/common/ErrorAlert';

// --- Notion Style Components ---

const NotionCard: React.FC<{ children: React.ReactNode; className?: string; title?: string; icon?: any; action?: React.ReactNode; subtitle?: React.ReactNode }> = ({ children, className = '', title, icon: Icon, action, subtitle }) => (
  <div className={`bg-notion-bg border border-notion-border rounded-sm shadow-card p-4 ${className}`}>
    {title && (
      <div className="flex items-center justify-between mb-4 border-b border-notion-border pb-2">
        <div className="flex items-center gap-2">
            {Icon && <Icon size={16} className="text-notion-text opacity-80" />}
            <h3 className="text-notion-text font-semibold text-sm tracking-wide uppercase">{title}</h3>
            {subtitle && <span className="text-xs text-notion-muted">{subtitle}</span>}
        </div>
        {action}
      </div>
    )}
    {children}
  </div>
);

const NotionTag: React.FC<{ text: string; color?: 'gray' | 'brown' | 'orange' | 'yellow' | 'green' | 'blue' | 'purple' | 'pink' | 'red' }> = ({ text, color = 'gray' }) => {
  const colors = {
    gray: 'bg-notion-gray_bg text-gray-700',
    brown: 'bg-notion-brown_bg text-yellow-900',
    orange: 'bg-notion-orange_bg text-orange-900',
    yellow: 'bg-notion-yellow_bg text-yellow-800',
    green: 'bg-notion-green_bg text-green-900',
    blue: 'bg-notion-blue_bg text-blue-900',
    purple: 'bg-notion-purple_bg text-purple-900',
    pink: 'bg-notion-pink_bg text-pink-900',
    red: 'bg-notion-red_bg text-red-900',
  };
  return <span className={`px-1.5 py-0.5 rounded text-xs font-medium mr-1 ${colors[color]}`}>{text}</span>;
};


// --- Chat Analysis with CRM Features ---

// Helper function to format date to YYYY-MM-DD
const formatShortDate = (dateStr: string | undefined | null): string => {
  if (!dateStr) return 'N/A';
  try {
    const date = new Date(dateStr);
    if (isNaN(date.getTime())) return 'N/A';
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  } catch {
    return 'N/A';
  }
};

// Date range filter options
type DateRangeFilter = 'LAST_6_MONTH' | 'LAST_1_YEAR' | 'LAST_2_YEAR' | 'ALL';

// Helper function to calculate last_purchase_after date
const calculateLastPurchaseAfter = (range: DateRangeFilter): string | undefined => {
  const now = new Date();
  switch (range) {
    case 'LAST_6_MONTH':
      return new Date(now.setMonth(now.getMonth() - 6)).toISOString().split('T')[0];
    case 'LAST_1_YEAR':
      return new Date(now.setMonth(now.getMonth() - 12)).toISOString().split('T')[0];
    case 'LAST_2_YEAR':
      return new Date(now.setMonth(now.getMonth() - 24)).toISOString().split('T')[0];
    case 'ALL':
    default:
      return undefined;
  }
};

const ChatAnalysis: React.FC = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedSession, setSelectedSession] = useState<BuyerSession | null>(null);
  const [activeSubTab, setActiveSubTab] = useState<'profile' | 'orders' | 'chat'>('profile');
  const [enableAI, setEnableAI] = useState(false); // AI分析开关（控制是否强制刷新分析）
  const [hasActivatedAI, setHasActivatedAI] = useState(false);
  const [isRefreshingAI, setIsRefreshingAI] = useState(false); // 是否正在刷新AI分析

  // Filter states - pending (user selected but not applied)
  const [pendingChannelFilter, setPendingChannelFilter] = useState<('DTC' | 'PFS')[]>([]);
  const [pendingBuyerTypeFilter, setPendingBuyerTypeFilter] = useState<('SMOKER' | 'VIC' | 'BOTH')[]>([]);
  const [pendingDateRangeFilter, setPendingDateRangeFilter] = useState<DateRangeFilter>('LAST_6_MONTH');
  const [showFilters, setShowFilters] = useState(false);

  // Applied filter states (actually used for API calls)
  const [appliedChannelFilter, setAppliedChannelFilter] = useState<('DTC' | 'PFS')[]>([]);
  const [appliedBuyerTypeFilter, setAppliedBuyerTypeFilter] = useState<('SMOKER' | 'VIC' | 'BOTH')[]>([]);
  const [appliedDateRangeFilter, setAppliedDateRangeFilter] = useState<DateRangeFilter>('LAST_6_MONTH');

  // Calculate pending filter count for badge (filters selected but not yet applied)
  const pendingFilterCount = useMemo(() => {
    let count = 0;
    if (pendingChannelFilter.length > 0) count++;
    if (pendingBuyerTypeFilter.length > 0) count++;
    if (pendingDateRangeFilter !== 'LAST_6_MONTH') count++;
    return count;
  }, [pendingChannelFilter, pendingBuyerTypeFilter, pendingDateRangeFilter]);

  // Calculate active filter count for badge (actually applied filters)
  const activeFilterCount = useMemo(() => {
    let count = 0;
    if (appliedChannelFilter.length > 0) count++;
    if (appliedBuyerTypeFilter.length > 0) count++;
    if (appliedDateRangeFilter !== 'LAST_6_MONTH') count++; // Only count non-default date range
    return count;
  }, [appliedChannelFilter, appliedBuyerTypeFilter, appliedDateRangeFilter]);

  // Check if pending filters differ from applied filters
  const hasPendingChanges = useMemo(() => {
    const pendingChannelStr = JSON.stringify(pendingChannelFilter.sort());
    const appliedChannelStr = JSON.stringify(appliedChannelFilter.sort());
    const pendingBuyerStr = JSON.stringify(pendingBuyerTypeFilter.sort());
    const appliedBuyerStr = JSON.stringify(appliedBuyerTypeFilter.sort());
    return pendingChannelStr !== appliedChannelStr
      || pendingBuyerStr !== appliedBuyerStr
      || pendingDateRangeFilter !== appliedDateRangeFilter;
  }, [pendingChannelFilter, appliedChannelFilter, pendingBuyerTypeFilter, appliedBuyerTypeFilter, pendingDateRangeFilter, appliedDateRangeFilter]);

  // Apply pending filters
  const handleApplyFilters = () => {
    setAppliedChannelFilter([...pendingChannelFilter]);
    setAppliedBuyerTypeFilter([...pendingBuyerTypeFilter]);
    setAppliedDateRangeFilter(pendingDateRangeFilter);
  };

  // Clear all filters (both pending and applied)
  const handleClearFilters = () => {
    setPendingChannelFilter([]);
    setPendingBuyerTypeFilter([]);
    setPendingDateRangeFilter('LAST_6_MONTH');
    setAppliedChannelFilter([]);
    setAppliedBuyerTypeFilter([]);
    setAppliedDateRangeFilter('LAST_6_MONTH');
  };

  // Track open states for chat dates. Default empty.
  const [openDates, setOpenDates] = useState<Record<string, boolean>>({});

  // 获取买家列表数据（真实API）- 使用已应用的筛选参数
  const { data: buyersData, isLoading: buyersLoading, error: buyersError } = useDataFetchingWithRetry(
    () => apiClient.getBuyers({
      limit: 100,
      sort_by: 'last_purchase',
      channel: appliedChannelFilter.length > 0 ? appliedChannelFilter : undefined,
      buyer_type: appliedBuyerTypeFilter.length > 0 ? appliedBuyerTypeFilter : undefined,
      last_purchase_after: calculateLastPurchaseAfter(appliedDateRangeFilter),
    }),
    2,
    [appliedChannelFilter, appliedBuyerTypeFilter, appliedDateRangeFilter] // 当已应用的筛选条件变化时重新获取
  );

  const { data: buyersCountData, isLoading: buyersCountLoading } = useDataFetchingWithRetry(
    () => apiClient.getBuyersCount({
      channel: appliedChannelFilter.length > 0 ? appliedChannelFilter : undefined,
      buyer_type: appliedBuyerTypeFilter.length > 0 ? appliedBuyerTypeFilter : undefined,
      last_purchase_after: calculateLastPurchaseAfter(appliedDateRangeFilter),
    }),
    1,
    [appliedChannelFilter, appliedBuyerTypeFilter, appliedDateRangeFilter]
  );

  // 转换API数据为Session格式
  const buyerSessions = useMemo(() => {
    if (!buyersData?.buyers) return [];
    return buyersData.buyers.map((buyer: any) => {
      // 构造一个基本的session对象
      const userNick = buyer.buyer_nick || buyer.user_nick || 'Unknown';
      const session: BuyerSession = {
        user_nick: userNick,
        profile: {
          user_nick: userNick,
          avatar_color: `bg-${['blue', 'green', 'orange', 'purple'][Math.floor(Math.random() * 4)]}-200 text-${['blue', 'green', 'orange', 'purple'][Math.floor(Math.random() * 4)]}-800`,
          city: buyer.city || 'Unknown',
          is_new_customer: buyer.buyer_type === 'SMOKER', // 简化判断
          historical_ltv: Number(buyer.historical_gmv || buyer.historical_net_sales || 0),
          historical_gmv: Number(buyer.historical_gmv || 0),
          historical_refund: Number(buyer.historical_refund || 0),
          historical_net_sales: Number(buyer.historical_net_sales || 0),
          refund_rate: Number(buyer.refund_rate || 0),
          total_orders: Number(buyer.total_orders || 0),
          discount_spend_amount: 0,
          discount_ratio: Number(buyer.discount_ratio || 0),
          l6m_netsales: Number(buyer.l6m_netsales || 0),
          l6m_orders: Number(buyer.l6m_orders || 0),
          l1y_netsales: Number(buyer.l1y_netsales || 0),
          l1y_orders: Number(buyer.l1y_orders || 0),
          l6m_refund_rate: Number(buyer.l6m_refund_rate || 0),
          recent_chat_frequency: 0,
          avg_reply_interval_days: 0,
          last_interaction_date: buyer.last_purchase_date,
          last_chat_date: buyer.last_chat_date || undefined,
          tags: [
            buyer.vip_level,
            buyer.buyer_type,
            buyer.rfm_segment,
            buyer.follow_priority,
            buyer.sentiment_label
          ].filter(Boolean),
          intent_scores: INTENT_DISTRIBUTION,
          order_history: [],
          analysis: {
            summary: '',
            key_interests: [],
            pain_points: [],
            recommended_action: ''
          }
        },
        messages: [], // 空消息列表
        sentimentScore: 0.5,
        dominantIntent: IntentType.PRE_SALE
      };
      return session;
    });
  }, [buyersData]);

  // Filter based on user_nick only as requested for precise lookup
  const filteredSessions = useMemo(() => {
    if (!searchTerm) return buyerSessions;
    return buyerSessions.filter(s =>
      s.user_nick.toLowerCase().includes(searchTerm.toLowerCase())
    );
  }, [searchTerm, buyerSessions]);

  // 当买家列表变化时（比如应用新筛选条件），检查当前选中是否仍在列表中
  // 如果不在，自动选择第一个
  useEffect(() => {
    if (filteredSessions.length > 0) {
      const isSelectedInList = selectedSession &&
        filteredSessions.some(s => s.user_nick === selectedSession.user_nick);
      if (!isSelectedInList) {
        setSelectedSession(filteredSessions[0]);
      }
    } else {
      setSelectedSession(null);
    }
  }, [filteredSessions]);

  // 当前选中的会话（如果没有选中，默认选择第一个）
  const currentSession = selectedSession || (filteredSessions.length > 0 ? filteredSessions[0] : null);

  // 当选中的用户改变时，按需获取其详细信息（AI默认关闭，仅激活后获取）
  const { data: buyerProfile, isLoading: profileLoading, error: profileError, refetch: refetchProfile } = useDataFetchingWithRetry(
    async () => {
      if (!currentSession?.user_nick) return null;
      const profile = await apiClient.getBuyerProfile(currentSession.user_nick, hasActivatedAI);

      // 同时获取订单历史和聊天记录
      try {
        const [ordersRaw, chatsRaw] = await Promise.all([
          apiClient.getBuyerOrders(currentSession.user_nick, 50),
          apiClient.getBuyerChats(currentSession.user_nick, 100)
        ]);

        // 转换订单数据：将后端格式转换为前端期望的OrderRecord格式
        // 后端每个产品一行，前端保持独立，不合并
        const orders = ordersRaw.map((item: any) => {
          const gmv = Number(item['成交总金额']) || 0;
          const refundAmount = Number(item['退款金额']) || 0;
          const quantity = Number(item['件数']) || 1;

          // 计算退款件数（按退款金额占GMV的比例）
          const refundedQty = gmv > 0 && refundAmount > 0
            ? Math.round(quantity * (refundAmount / gmv))
            : 0;

          const netQty = Math.max(0, quantity - refundedQty);

          return {
            order_id: item['订单号'],
            sub_order_id: item['子订单号'],
            date: item['最后付款时间'].split('T')[0],
            gmv: gmv,
            netsales: Number(item.netsales || 0),
            refund_amount: refundAmount,
            refund_type: item['退款类型'] || null,
            fp_md: item['FP_MD'] || 'FP',
            image_url: item['图片地址'] || '',
            items: [item['商品名称'] || 'Unknown'],
            quantity: quantity,
            gross_qty: quantity,
            net_qty: netQty,
            refunded_qty: refundedQty
          };
        });

        // 将订单历史和聊天记录添加到profile中
        return {
          ...profile,
          order_history: orders,
          chat_history: chatsRaw
        } as APIBuyerProfile & { order_history: OrderRecord[], chat_history: ChatMessage[] };
      } catch (error) {
        console.error('Failed to fetch orders/chats:', error);
        // 即使orders/chats失败，也返回基本profile
        return {
          ...profile,
          order_history: [],
          chat_history: []
        } as APIBuyerProfile & { order_history: OrderRecord[], chat_history: ChatMessage[] };
      }
    },
    2,
    [currentSession?.user_nick, hasActivatedAI]
  );

  const handleSelectUser = (session: BuyerSession) => {
    setSelectedSession(session);
    setActiveSubTab('profile'); // Reset to profile on user change
    // Reset AI switch to off when switching users (but keep any cached results)
    setEnableAI(false);
    setHasActivatedAI(false);
    // Open all dates by default when selecting a new user for better visibility
    const dates: Record<string, boolean> = {};
    session.messages.forEach(m => {
       const d = m.msg_time.split(' ')[0];
       dates[d] = true;
    });
    setOpenDates(dates);
  };

  // 处理AI开关切换
  const handleAIToggle = async () => {
    const newEnableAI = !enableAI;
    setEnableAI(newEnableAI);

    // 当从OFF切换到ON时，触发强制刷新AI分析
    if (newEnableAI && currentSession?.user_nick) {
      setHasActivatedAI(true);
      setIsRefreshingAI(true);
      try {
        await apiClient.forceRefreshAnalysis(currentSession.user_nick, 'persona');
        // 刷新成功后重新获取profile
        refetchProfile();
      } catch (error) {
        console.error('Failed to refresh AI analysis:', error);
      } finally {
        setIsRefreshingAI(false);
      }
    }
    // 当从ON切换到OFF时，不做任何操作，保持显示已有结果
  };

  // 合并基本信息和AI分析结果
  const enrichedProfile = useMemo(() => {
    if (!currentSession || !buyerProfile) return currentSession?.profile;

    return {
      ...currentSession.profile,
      // 如果有AI分析结果，使用它；否则使用默认值
      analysis: buyerProfile.ai_analysis || currentSession.profile.analysis,
      // 使用真实数据更新字段
      historical_ltv: Number((buyerProfile as any).historical_gmv ?? currentSession.profile.historical_ltv),
      historical_gmv: Number((buyerProfile as any).historical_gmv ?? currentSession.profile.historical_gmv),
      historical_refund: Number((buyerProfile as any).historical_refund ?? 0),
      historical_net_sales: Number((buyerProfile as any).historical_net_sales ?? currentSession.profile.historical_net_sales),
      refund_rate: Number((buyerProfile as any).refund_rate ?? 0),
      total_orders: buyerProfile.total_orders ?? currentSession.profile.total_orders,
      // L6M 指标 - 直接从buyerProfile获取
      l6m_gmv: Number((buyerProfile as any).l6m_gmv ?? 0),
      l6m_netsales: Number(buyerProfile.l6m_netsales ?? 0),
      l6m_orders: Number(buyerProfile.l6m_orders ?? 0),
      l6m_refund_rate: Number((buyerProfile as any).l6m_refund_rate ?? 0),
      // L1Y 指标 - 直接从buyerProfile获取
      l1y_gmv: Number((buyerProfile as any).l1y_gmv ?? 0),
      l1y_netsales: Number(buyerProfile.l1y_netsales ?? 0),
      l1y_orders: Number(buyerProfile.l1y_orders ?? 0),
      l1y_refund_rate: Number((buyerProfile as any).l1y_refund_rate ?? 0),
      // Rolling 24M 指标
      rolling_24m_gmv: Number((buyerProfile as any).rolling_24m_gmv ?? 0),
      rolling_24m_netsales: Number((buyerProfile as any).rolling_24m_netsales ?? 0),
      rolling_24m_orders: Number((buyerProfile as any).rolling_24m_orders ?? 0),
      rolling_24m_refund_rate: Number((buyerProfile as any).rolling_24m_refund_rate ?? 0),
      vip_level: buyerProfile.vip_level ?? 'Unknown',
      city: buyerProfile.city ?? currentSession.profile.city,
      // 聊天指标
      first_chat_date: buyerProfile.first_chat_date,
      last_chat_date: buyerProfile.last_chat_date,
      l30d_chat_frequency_days: buyerProfile.l30d_chat_frequency_days,
      l3m_chat_frequency_days: buyerProfile.l3m_chat_frequency_days,
      avg_chat_interval_days: buyerProfile.avg_chat_interval_days,
      // 其他字段
      top_category: buyerProfile.top_category,
      second_category: buyerProfile.second_category,
      third_category: buyerProfile.third_category,
      discount_ratio: buyerProfile.discount_ratio,
      tags: [
        buyerProfile.vip_level ?? (currentSession.profile as any).vip_level,
        (buyerProfile as any).buyer_type ?? (currentSession.profile as any).buyer_type,
        (buyerProfile as any).rfm_segment ?? (currentSession.profile as any).rfm_segment,
        (buyerProfile as any).follow_priority ?? (currentSession.profile as any).follow_priority,
        (buyerProfile as any).sentiment_label ?? (currentSession.profile as any).sentiment_label
      ].filter(Boolean),
      // 包含订单历史和聊天记录
      order_history: (buyerProfile as any).order_history || currentSession.profile.order_history || [],
      chat_history: (buyerProfile as any).chat_history || currentSession.profile.chat_history || [],
    };
  }, [currentSession, buyerProfile]);

  const hasChatRecord = ((enrichedProfile as any)?.chat_history?.length || 0) > 0
    || !!buyerProfile?.last_chat_date
    || !!currentSession?.profile?.last_chat_date;

  // Transform intent_distribution JSON to radar chart format
  const intentDistributionData = useMemo(() => {
    const allIntentKeys = [
      'Pre-sale Inquiry',
      'Post-sale Support',
      'Logistics',
      'Usage Guide',
      'Complaint'
    ];
    const rawDistribution = (buyerProfile as any)?.intent_distribution;
    if (!rawDistribution || typeof rawDistribution !== 'object') {
      return allIntentKeys.map((key) => ({ subject: key, A: 0, fullMark: 100 }));
    }

    // Calculate total for percentage conversion
    const values = Object.values(rawDistribution) as number[];
    const total = values.reduce((sum, val) => sum + val, 0);

    if (total === 0) {
      return allIntentKeys.map((key) => ({ subject: key, A: 0, fullMark: 100 }));
    }

    // Map intent names to IntentType enum values
    const intentMapping: Record<string, IntentType> = {
      'Pre-sale Inquiry': IntentType.PRE_SALE,
      'Post-sale Support': IntentType.POST_SALE,
      'Logistics': IntentType.LOGISTICS,
      'Usage Guide': IntentType.USAGE_GUIDE,
      'Complaint': IntentType.COMPLAINT,
    };

    // Convert to radar chart format with percentage (scale to 100)
    const fullMark = 100;
    return Object.entries(rawDistribution).map(([key, value]) => {
      const numValue = value as number;
      const percentage = total > 0 ? Math.round((numValue / total) * 100) : 0;
      return {
        subject: intentMapping[key] || key,
        A: percentage,
        fullMark,
      };
    });
  }, [buyerProfile]);

  // Get dominant intent from API
  const dominantIntent = (buyerProfile as any)?.ai_dominant_intent || 'Unknown';

  // Calculations for Metrics
  const historicalAov = enrichedProfile?.total_orders > 0
    ? (enrichedProfile.historical_ltv || 0) / enrichedProfile.total_orders
    : 0;

  const l6mAov = enrichedProfile?.l6m_orders > 0
    ? (enrichedProfile.l6m_gmv || 0) / enrichedProfile.l6m_orders
    : 0;

  const l1yAov = enrichedProfile?.l1y_orders > 0
    ? (enrichedProfile.l1y_gmv || 0) / enrichedProfile.l1y_orders
    : 0;

  const r24mAov = (enrichedProfile as any)?.rolling_24m_orders > 0
    ? ((enrichedProfile as any).rolling_24m_gmv || 0) / (enrichedProfile as any).rolling_24m_orders
    : 0;

  const r24mRefundRate = (() => {
    const gmv = Number((enrichedProfile as any)?.rolling_24m_gmv || 0);
    const netSales = Number((enrichedProfile as any)?.rolling_24m_netsales || 0);
    if (gmv <= 0) return 0;
    const rawRate = 1 - (netSales / gmv);
    return Math.max(0, Math.min(rawRate, 1));
  })();

  // Group orders by date and merge items for same date
  const groupedOrders = useMemo(() => {
    const orders = enrichedProfile?.order_history || [];
    if (!orders || orders.length === 0) return [];

    const grouped: Record<string, {
      date: string;
      total_gmv: number;
      items: string[];
      fp_md: string;
      order_ids: string[];
    }> = {};

    orders.forEach((order: OrderRecord) => {
      const date = order.date;
      if (!grouped[date]) {
        grouped[date] = {
          date,
          total_gmv: 0,
          items: [],
          fp_md: order.fp_md || 'FP',
          order_ids: []
        };
      }
      grouped[date].total_gmv += Number(order.gmv) || 0;
      grouped[date].items.push(...order.items);
      grouped[date].order_ids.push(order.order_id);
    });

    // Convert to array and sort by date descending (most recent first)
    return Object.values(grouped).sort((a, b) => b.date.localeCompare(a.date));
  }, [enrichedProfile?.order_history]);

  // Group messages by date and sort by date ascending (oldest first)
  const groupedMessages = useMemo<Record<string, ChatMessage[]>>(() => {
     const chatHistory = enrichedProfile?.chat_history || currentSession?.messages || [];
     if (!chatHistory || chatHistory.length === 0) return {};

     const groups: Record<string, ChatMessage[]> = {};
     chatHistory.forEach((msg: ChatMessage) => {
         // Handle both ISO 8601 format (2026-01-19T22:54:32) and space-separated format (2026-01-19 22:54:32)
         let date: string;
         if (msg.msg_time.includes('T')) {
             date = msg.msg_time.split('T')[0];  // ISO 8601 format
         } else {
             date = msg.msg_time.split(' ')[0];  // Space-separated format
         }

         if (!groups[date]) groups[date] = [];
         groups[date].push(msg);
     });

     // Sort messages within each date by time
     Object.keys(groups).forEach(date => {
         groups[date].sort((a, b) => a.msg_time.localeCompare(b.msg_time));
     });

     return groups;
  }, [enrichedProfile, currentSession]);

  // Get sorted dates for display (oldest first)
  const sortedDates = useMemo(() => {
     return Object.keys(groupedMessages).sort((a, b) => a.localeCompare(b));
  }, [groupedMessages]);

  // Auto-expand all dates when chat history changes
  React.useEffect(() => {
    if (sortedDates.length > 0 && Object.keys(openDates).length === 0) {
      const newOpenDates: Record<string, boolean> = {};
      sortedDates.forEach(date => {
        newOpenDates[date] = true;
      });
      setOpenDates(newOpenDates);
    }
  }, [sortedDates]);

  const toggleDate = (date: string) => {
     setOpenDates(prev => ({ ...prev, [date]: !prev[date] }));
  };
  
  if (buyersLoading) {
    return (
      <div className="p-8">
        <LoadingSpinner size={24} text="加载买家数据中..." />
      </div>
    );
  }

  if (buyersError) {
    return (
      <div className="p-8">
        <ErrorAlert message={buyersError} />
      </div>
    );
  }

  if (!currentSession) {
    return (
      <div className="p-8">
        <EmptyState
          title="暂无可显示的买家"
          description="请检查后端服务与买家数据接口是否正常"
        />
      </div>
    );
  }

  if (!currentSession.profile) {
    return <div className="p-8 text-center text-notion-muted">加载中...</div>;
  }

  return (
    <div className="h-[calc(100vh-120px)] flex gap-6">
        {/* Left Sidebar: Search & User List */}
        <div className="w-64 flex-none border border-notion-border bg-notion-sidebar rounded-sm flex flex-col shadow-sm">
             <div className="p-3 border-b border-notion-border bg-white rounded-t-sm">
                <div className="flex gap-2">
                  <div className="relative flex-1">
                    <Search className="absolute left-2.5 top-2.5 text-notion-muted" size={14} />
                    <input
                        type="text"
                        placeholder="Search user..."
                        className="w-full bg-notion-gray_bg border-0 text-notion-text pl-9 pr-3 py-1.5 rounded text-sm focus:ring-1 focus:ring-blue-400 placeholder-notion-muted/70 transition-all"
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                    />
                  </div>
                  {/* Filter Button */}
                  <button
                    onClick={() => setShowFilters(!showFilters)}
                    className={`relative px-2 py-1.5 rounded transition-colors ${
                      showFilters || activeFilterCount > 0 || hasPendingChanges
                        ? 'bg-blue-100 text-blue-700 border border-blue-300'
                        : 'bg-notion-gray_bg text-notion-muted border border-notion-border hover:border-gray-400'
                    }`}
                    title="筛选"
                  >
                    <Filter size={14} />
                    {(activeFilterCount > 0 || hasPendingChanges) && (
                      <span className={`absolute -top-1 -right-1 w-4 h-4 text-white text-[10px] font-bold rounded-full flex items-center justify-center ${
                        hasPendingChanges ? 'bg-amber-500' : 'bg-blue-600'
                      }`}>
                        {activeFilterCount}
                      </span>
                    )}
                  </button>
                </div>

                {/* Filter Section - Collapsible */}
                {showFilters && (
                  <div className="mt-3 space-y-2 pt-3 border-t border-notion-border">
                    {/* Channel Filter */}
                    <div>
                      <label className="text-[10px] font-semibold text-notion-muted uppercase tracking-wider block mb-1">渠道</label>
                      <select
                        value={pendingChannelFilter.length > 0 ? pendingChannelFilter[0] : ''}
                        onChange={(e) => {
                          const value = e.target.value as 'DTC' | 'PFS' | '';
                          if (value === '') {
                            setPendingChannelFilter([]);
                          } else {
                            setPendingChannelFilter([value]);
                          }
                        }}
                        className="w-full bg-notion-gray_bg border border-notion-border text-notion-text text-xs rounded px-2 py-1.5 focus:ring-1 focus:ring-blue-400 cursor-pointer"
                      >
                        <option value="">全部</option>
                        <option value="DTC">DTC</option>
                        <option value="PFS">PFS</option>
                      </select>
                    </div>

                    {/* Buyer Type Filter */}
                    <div>
                      <label className="text-[10px] font-semibold text-notion-muted uppercase tracking-wider block mb-1">客户类型</label>
                      <select
                        value={pendingBuyerTypeFilter.length > 0 ? pendingBuyerTypeFilter[0] : ''}
                        onChange={(e) => {
                          const value = e.target.value as 'SMOKER' | 'VIC' | 'BOTH' | '';
                          if (value === '') {
                            setPendingBuyerTypeFilter([]);
                          } else {
                            setPendingBuyerTypeFilter([value]);
                          }
                        }}
                        className="w-full bg-notion-gray_bg border border-notion-border text-notion-text text-xs rounded px-2 py-1.5 focus:ring-1 focus:ring-blue-400 cursor-pointer"
                      >
                        <option value="">全部</option>
                        <option value="SMOKER">SMOKER (烟斗/打火机)</option>
                        <option value="VIC">VIC (高价值)</option>
                        <option value="BOTH">BOTH (双重身份)</option>
                      </select>
                    </div>

                    {/* Date Range Filter */}
                    <div>
                      <label className="text-[10px] font-semibold text-notion-muted uppercase tracking-wider block mb-1">购买时间</label>
                      <select
                        value={pendingDateRangeFilter}
                        onChange={(e) => setPendingDateRangeFilter(e.target.value as DateRangeFilter)}
                        className="w-full bg-notion-gray_bg border border-notion-border text-notion-text text-xs rounded px-2 py-1.5 focus:ring-1 focus:ring-blue-400 cursor-pointer"
                      >
                        <option value="LAST_6_MONTH">近6个月</option>
                        <option value="LAST_1_YEAR">近1年</option>
                        <option value="LAST_2_YEAR">近2年</option>
                        <option value="ALL">全部时间</option>
                      </select>
                    </div>

                    {/* Query Button */}
                    <button
                      onClick={handleApplyFilters}
                      disabled={!hasPendingChanges}
                      className={`w-full mt-3 px-3 py-1.5 text-xs font-medium rounded transition-colors ${
                        hasPendingChanges
                          ? 'bg-blue-600 text-white hover:bg-blue-700 cursor-pointer'
                          : 'bg-gray-200 text-gray-500 cursor-not-allowed'
                      }`}
                    >
                      查询
                    </button>

                    {/* Clear Filters Button */}
                    {(activeFilterCount > 0 || pendingFilterCount > 0) && (
                      <button
                        onClick={handleClearFilters}
                        className="w-full px-2 py-1 text-xs text-notion-muted hover:text-red-600 hover:bg-red-50 rounded transition-colors border border-dashed border-notion-border hover:border-red-300"
                      >
                        清除筛选
                      </button>
                    )}

                    {/* Pending Changes Indicator */}
                    {hasPendingChanges && (
                      <div className="text-[10px] text-amber-600 flex items-center gap-1 mt-1">
                        <span className="w-1.5 h-1.5 bg-amber-500 rounded-full animate-pulse"></span>
                        有未应用的筛选条件
                      </div>
                    )}
                  </div>
                )}
             </div>
             <div className="flex-1 overflow-y-auto">
                <div className="px-3 py-2 border-b border-notion-border bg-notion-gray_bg/50 text-[11px] text-notion-muted flex items-center justify-between">
                  <span>当前显示 {filteredSessions.length} 人</span>
                  <span>{buyersCountLoading ? '总数计算中...' : `筛选总数 ${buyersCountData?.total ?? 0} 人`}</span>
                </div>
                 {buyersLoading ? (
                   <div className="p-4">
                     <LoadingSpinner size={20} text="加载买家列表..." />
                   </div>
                 ) : buyersError ? (
                   <div className="p-4">
                     <ErrorAlert message={buyersError} />
                   </div>
                 ) : filteredSessions.length === 0 ? (
                   <div className="p-4">
                     <EmptyState
                       title="未找到买家"
                       description="尝试其他搜索关键词"
                     />
                   </div>
                 ) : (
                   filteredSessions.map((session, idx) => (
                    <div
                        key={idx}
                        onClick={() => handleSelectUser(session)}
                        className={`p-3 border-b border-notion-border cursor-pointer hover:bg-notion-hover transition-colors group ${currentSession.user_nick === session.user_nick ? 'bg-white border-l-4 border-l-orange-500' : 'border-l-4 border-l-transparent'}`}
                    >
                        <div className="flex items-center justify-between">
                            <span className="font-medium text-sm text-notion-text truncate">{session.user_nick}</span>
                            <span className="text-[10px] text-notion-muted group-hover:text-notion-text whitespace-nowrap ml-2">{formatShortDate((session.profile as any).last_chat_date || session.profile.last_interaction_date)}</span>
                        </div>
                    </div>
                   ))
                 )}
             </div>
        </div>

        {/* Right Main Content Area */}
        <div className="flex-1 flex flex-col gap-4 min-w-0 h-full overflow-hidden">
             
             {/* Sticky Header Card */}
             <div className="bg-notion-bg border border-notion-border rounded-sm shadow-sm flex-none">
                 {/* Top Row: Identity */}
                 <div className="p-4 border-b border-notion-border flex items-center justify-between">
                     <div className="flex items-center gap-4">
                         <div className={`w-12 h-12 rounded-full flex items-center justify-center text-lg font-bold shadow-sm ${currentSession.profile.avatar_color}`}>
                            {currentSession.profile.user_nick?.slice(0, 2) || '??'}
                         </div>
                         <div>
                             <h2 className="text-xl font-bold text-notion-text flex items-center gap-3">
                                {currentSession.profile.user_nick || 'Unknown'}
                                {currentSession.profile.is_new_customer ? (
                                    <span className="text-xs bg-green-100 text-green-700 border border-green-200 px-2 py-0.5 rounded font-medium shadow-sm">New</span>
                                ) : (
                                    <span className="text-xs bg-blue-100 text-blue-700 border border-blue-200 px-2 py-0.5 rounded font-medium shadow-sm">Existing</span>
                                )}
                                {hasChatRecord ? (
                                    <span className="text-xs bg-purple-100 text-purple-700 border border-purple-200 px-2 py-0.5 rounded font-medium shadow-sm">Chatted</span>
                                ) : (
                                    <span className="text-xs bg-gray-100 text-gray-700 border border-gray-200 px-2 py-0.5 rounded font-medium shadow-sm">No Chat</span>
                                )}
                             </h2>
                             <div className="flex items-center gap-3 text-xs text-notion-muted mt-0.5">
                                <span className="flex items-center gap-1"><MapPin size={12} /> {currentSession.profile.city || 'Unknown'}</span>
                             </div>
                             {/* Lifetime Metrics */}
                             <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-2 text-xs">
                                <span className="text-notion-muted">LTV: <span className="font-semibold text-notion-text">¥{(enrichedProfile?.historical_ltv || 0).toLocaleString()}</span></span>
                                <span className="w-1 h-1 bg-gray-300 rounded-full"></span>
                                <span className="text-notion-muted">Orders: <span className="font-semibold text-notion-text">{(enrichedProfile?.total_orders || 0).toLocaleString()}</span></span>
                                <span className="w-1 h-1 bg-gray-300 rounded-full"></span>
                                <span className="text-notion-muted">AOV: <span className="font-semibold text-notion-text">¥{historicalAov.toLocaleString(undefined, {minimumFractionDigits: 0, maximumFractionDigits: 0})}</span></span>
                                <span className="w-1 h-1 bg-gray-300 rounded-full"></span>
                                <span className="text-notion-muted">NetSales: <span className="font-semibold text-notion-text">¥{((enrichedProfile as any)?.historical_net_sales || 0).toLocaleString()}</span></span>
                                <span className="w-1 h-1 bg-gray-300 rounded-full"></span>
                                <span className="text-notion-muted">RRC: <span className="font-semibold text-notion-text">{(((enrichedProfile as any)?.historical_refund || 0) / Math.max((enrichedProfile?.historical_ltv || 1), 1) * 100).toFixed(1)}%</span></span>
                                <span className="w-1 h-1 bg-gray-300 rounded-full"></span>
                                <span className="text-notion-muted">Discount: <span className="font-semibold text-notion-text">{(Number((enrichedProfile as any)?.discount_ratio || 0) * 100).toFixed(0)}%</span></span>
                                <span className="w-1 h-1 bg-gray-300 rounded-full"></span>
                                <span className="text-notion-muted">Top 3: <span className="font-semibold text-notion-text">{[
                                  (enrichedProfile as any)?.top_category,
                                  (enrichedProfile as any)?.second_category,
                                  (enrichedProfile as any)?.third_category
                                ].filter(Boolean).join(' / ') || 'N/A'}</span></span>
                             </div>
                         </div>
                     </div>
                     <div className="flex items-center gap-3">
                         {/* AI分析开关 */}
                         <div className="flex items-center gap-2 px-3 py-1.5 bg-purple-50 border border-purple-200 rounded-md">
                            <Sparkles size={14} className={`text-purple-600 ${isRefreshingAI ? 'animate-pulse' : ''}`} />
                            <label className="flex items-center gap-2 cursor-pointer">
                              <span className="text-xs font-medium text-purple-900">AI分析</span>
                              <button
                                onClick={handleAIToggle}
                                disabled={isRefreshingAI}
                                className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
                                  enableAI ? 'bg-purple-600' : 'bg-purple-200'
                                } ${isRefreshingAI ? 'opacity-50 cursor-wait' : ''}`}
                              >
                                <span
                                  className={`inline-block h-3 w-3 transform rounded-full bg-white transition-transform ${
                                    enableAI ? 'translate-x-5' : 'translate-x-1'
                                  }`}
                                />
                              </button>
                            </label>
                         </div>
                         <div className="flex gap-2">
                             {(enrichedProfile?.tags || currentSession.profile.tags || []).map(t => <NotionTag key={t} text={t} color="orange" />)}
                         </div>
                     </div>
                 </div>

                 {/* Bottom Row: Sub-Navigation (Reordered) */}
                 <div className="flex items-center bg-notion-sidebar px-4">
                     {[
                         { id: 'profile', label: '360° Profile & Insights', icon: User },
                         { id: 'orders', label: 'Purchase History', icon: ShoppingBag },
                         { id: 'chat', label: 'Communication', icon: MessageCircle }
                     ].map((tab) => (
                         <button
                            key={tab.id}
                            onClick={() => setActiveSubTab(tab.id as any)}
                            className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                                activeSubTab === tab.id 
                                ? 'border-orange-500 text-orange-700 bg-white' 
                                : 'border-transparent text-notion-muted hover:text-notion-text hover:bg-gray-100'
                            }`}
                         >
                             <tab.icon size={16} />
                             {tab.label}
                         </button>
                     ))}
                 </div>
             </div>

             {/* Dynamic Content Area (Scrollable) */}
             <div className="flex-1 overflow-y-auto pr-2 scrollbar-thin scrollbar-thumb-gray-200">
                 
                 {/* VIEW 1: 360° PROFILE & INSIGHTS */}
                 {activeSubTab === 'profile' && (
                     <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
                         {/* AI Summary Section */}
                         <NotionCard
                           icon={Sparkles}
                           title="AI Persona Analysis"
                           subtitle={enableAI && !enrichedProfile?.analysis?.error ? "(AI分析已基于买家历史数据和聊天记录生成)" : undefined}
                         >
                            {profileLoading ? (
                              <div className="py-8">
                                <LoadingSpinner size={24} text={enableAI ? "AI正在分析买家画像..." : "加载买家信息..."} />
                              </div>
                            ) : profileError ? (
                              <ErrorAlert message={profileError} onRetry={() => refetchProfile()} />
                            ) : (
                              <div className="flex flex-col gap-4">
                                {/* AI Summary */}
                                <div className="bg-purple-50 p-4 rounded border border-purple-100 text-sm text-notion-text leading-relaxed italic">
                                     "{enrichedProfile?.analysis?.summary || '暂无AI分析'}"
                                </div>

                                 {!enableAI && !enrichedProfile?.analysis?.summary && (
                                   <div className="flex items-center gap-2 text-xs text-gray-600 bg-gray-50 px-3 py-2 rounded border border-gray-200">
                                     <Info size={12} />
                                     <span>启用右上角的"AI分析"开关以获取智能买家画像</span>
                                   </div>
                                 )}

                                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                    <div>
                                        <span className="text-xs font-bold text-notion-muted uppercase tracking-wider block mb-2">Key Interests</span>
                                        <div className="flex flex-wrap gap-2">
                                            {(enrichedProfile?.analysis?.key_interests || []).length > 0 ? (
                                              enrichedProfile?.analysis?.key_interests.map((tag, i) => (
                                                <span key={i} className="px-2.5 py-1 bg-blue-50 text-blue-700 border border-blue-100 rounded text-xs font-medium">
                                                  {tag}
                                                </span>
                                              ))
                                            ) : (
                                              <span className="text-xs text-gray-500 italic">暂无兴趣点数据</span>
                                            )}
                                        </div>
                                    </div>
                                    <div>
                                        <span className="text-xs font-bold text-notion-muted uppercase tracking-wider block mb-2">Pain Points</span>
                                        <div className="flex flex-wrap gap-2">
                                            {(enrichedProfile?.analysis?.pain_points || []).length > 0 ? (
                                              enrichedProfile?.analysis?.pain_points.map((tag, i) => (
                                                <span key={i} className="px-2.5 py-1 bg-red-50 text-red-700 border border-red-100 rounded text-xs font-medium">
                                                  {tag}
                                                </span>
                                              ))
                                            ) : (
                                              <span className="text-xs text-gray-500 italic">暂无痛点数据</span>
                                            )}
                                        </div>
                                    </div>
                                </div>
                                <div className="mt-2">
                                     <div className="flex flex-col gap-1">
                                         <span className="text-xs font-bold text-notion-muted uppercase tracking-wider block mb-1">Recommended Action</span>
                                         <span className="text-xs text-notion-text leading-relaxed bg-yellow-50 border border-yellow-100 rounded px-3 py-2">
                                             {enrichedProfile?.analysis?.recommended_action || '建议根据买家情况制定跟进策略'}
                                         </span>
                                     </div>
                                </div>
                            </div>
                            )}
                         </NotionCard>

                        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
                            {/* Individual Intent Radar */}
                             <NotionCard icon={Target} title="Intent Distribution">
                                 <div className="h-64">
                                    <ResponsiveContainer width="100%" height="100%">
                                        <RadarChart cx="50%" cy="50%" outerRadius="70%" data={intentDistributionData}>
                                        <PolarGrid stroke="#E9E9E7" />
                                        <PolarAngleAxis dataKey="subject" tick={{ fill: '#37352F', fontSize: 10 }} />
                                        <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
                                        <Radar name="Intents" dataKey="A" stroke="#F59E0B" fill="#F59E0B" fillOpacity={0.4} />
                                        <Tooltip contentStyle={{ backgroundColor: '#fff', borderColor: '#E9E9E7' }} />
                                        </RadarChart>
                                    </ResponsiveContainer>
                                 </div>
                                 <p className="text-xs text-notion-muted text-center mt-2">
                                     Dominant Intent: <span className="font-semibold text-notion-text">{dominantIntent}</span>
                                 </p>
                             </NotionCard>

                            {/* RFM Score Module */}
                            <NotionCard icon={Gauge} title="RFM Score">
                                <div className="space-y-4">
                                    {/* RFM Segment Badge */}
                                    {(() => {
                                        const rfmSegment = (buyerProfile as any)?.rfm_segment || (enrichedProfile as any)?.rfm_segment;
                                        const segmentColors: Record<string, { bg: string; text: string; border: string }> = {
                                            'Champions': { bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200' },
                                            'Loyal Customers': { bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-200' },
                                            'Potential Loyalists': { bg: 'bg-cyan-50', text: 'text-cyan-700', border: 'border-cyan-200' },
                                            'Recent Customers': { bg: 'bg-teal-50', text: 'text-teal-700', border: 'border-teal-200' },
                                            'Promising': { bg: 'bg-indigo-50', text: 'text-indigo-700', border: 'border-indigo-200' },
                                            'Customers Needing Attention': { bg: 'bg-yellow-50', text: 'text-yellow-700', border: 'border-yellow-200' },
                                            'About to Sleep': { bg: 'bg-orange-50', text: 'text-orange-700', border: 'border-orange-200' },
                                            'At Risk': { bg: 'bg-red-50', text: 'text-red-700', border: 'border-red-200' },
                                            'Cannot Lose Them': { bg: 'bg-rose-50', text: 'text-rose-700', border: 'border-rose-200' },
                                            'Hibernating': { bg: 'bg-gray-50', text: 'text-gray-700', border: 'border-gray-200' },
                                            'Lost': { bg: 'bg-slate-50', text: 'text-slate-700', border: 'border-slate-200' },
                                        };
                                        const segmentStyle = segmentColors[rfmSegment] || { bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200' };
                                        return rfmSegment ? (
                                            <div className={`text-center py-2 px-4 rounded-lg ${segmentStyle.bg} ${segmentStyle.border} border`}>
                                                <div className="flex items-center justify-center gap-2">
                                                    <Award size={18} className={segmentStyle.text} />
                                                    <span className={`font-semibold ${segmentStyle.text}`}>{rfmSegment}</span>
                                                </div>
                                            </div>
                                        ) : (
                                            <div className="text-center py-2 px-4 rounded-lg bg-gray-50 border border-gray-200">
                                                <span className="text-gray-400 text-sm">No RFM Segment Data</span>
                                            </div>
                                        );
                                    })()}

                                    {/* RFM Score Bars */}
                                    <div className="space-y-3">
                                        {/* Recency Score */}
                                        {(() => {
                                            const recencyScore = (buyerProfile as any)?.rfm_recency_score || (enrichedProfile as any)?.rfm_recency_score || 0;
                                            const percentage = (recencyScore / 5) * 100;
                                            return (
                                                <div>
                                                    <div className="flex items-center justify-between mb-1">
                                                        <div className="flex items-center gap-2">
                                                            <Clock size={14} className="text-amber-600" />
                                                            <span className="text-xs font-medium text-notion-text">Recency (R)</span>
                                                        </div>
                                                        <span className="text-xs font-mono font-bold text-amber-600">{recencyScore}/5</span>
                                                    </div>
                                                    <div className="h-2 bg-amber-100 rounded-full overflow-hidden">
                                                        <div
                                                            className="h-full bg-gradient-to-r from-amber-400 to-amber-500 rounded-full transition-all duration-300"
                                                            style={{ width: `${percentage}%` }}
                                                        />
                                                    </div>
                                                    <p className="text-[10px] text-notion-muted mt-0.5">Days since last purchase</p>
                                                </div>
                                            );
                                        })()}

                                        {/* Frequency Score */}
                                        {(() => {
                                            const frequencyScore = (buyerProfile as any)?.rfm_frequency_score || (enrichedProfile as any)?.rfm_frequency_score || 0;
                                            const percentage = (frequencyScore / 5) * 100;
                                            return (
                                                <div>
                                                    <div className="flex items-center justify-between mb-1">
                                                        <div className="flex items-center gap-2">
                                                            <Activity size={14} className="text-orange-600" />
                                                            <span className="text-xs font-medium text-notion-text">Frequency (F)</span>
                                                        </div>
                                                        <span className="text-xs font-mono font-bold text-orange-600">{frequencyScore}/5</span>
                                                    </div>
                                                    <div className="h-2 bg-orange-100 rounded-full overflow-hidden">
                                                        <div
                                                            className="h-full bg-gradient-to-r from-orange-400 to-orange-500 rounded-full transition-all duration-300"
                                                            style={{ width: `${percentage}%` }}
                                                        />
                                                    </div>
                                                    <p className="text-[10px] text-notion-muted mt-0.5">Purchase frequency level</p>
                                                </div>
                                            );
                                        })()}

                                        {/* Monetary Score */}
                                        {(() => {
                                            const monetaryScore = (buyerProfile as any)?.rfm_monetary_score || (enrichedProfile as any)?.rfm_monetary_score || 0;
                                            const percentage = (monetaryScore / 5) * 100;
                                            return (
                                                <div>
                                                    <div className="flex items-center justify-between mb-1">
                                                        <div className="flex items-center gap-2">
                                                            <DollarSign size={14} className="text-yellow-600" />
                                                            <span className="text-xs font-medium text-notion-text">Monetary (M)</span>
                                                        </div>
                                                        <span className="text-xs font-mono font-bold text-yellow-600">{monetaryScore}/5</span>
                                                    </div>
                                                    <div className="h-2 bg-yellow-100 rounded-full overflow-hidden">
                                                        <div
                                                            className="h-full bg-gradient-to-r from-yellow-400 to-yellow-500 rounded-full transition-all duration-300"
                                                            style={{ width: `${percentage}%` }}
                                                        />
                                                    </div>
                                                    <p className="text-[10px] text-notion-muted mt-0.5">Total spending level</p>
                                                </div>
                                            );
                                        })()}
                                    </div>

                                    {/* RFM Score Summary */}
                                    <div className="pt-2 border-t border-notion-border">
                                        <div className="flex items-center justify-between">
                                            <span className="text-xs text-notion-muted">Combined RFM Score</span>
                                            <span className="text-sm font-mono font-bold text-notion-text">
                                                {(() => {
                                                    const r = (buyerProfile as any)?.rfm_recency_score || (enrichedProfile as any)?.rfm_recency_score || 0;
                                                    const f = (buyerProfile as any)?.rfm_frequency_score || (enrichedProfile as any)?.rfm_frequency_score || 0;
                                                    const m = (buyerProfile as any)?.rfm_monetary_score || (enrichedProfile as any)?.rfm_monetary_score || 0;
                                                    return `${r + f + m}/15`;
                                                })()}
                                            </span>
                                        </div>
                                    </div>
                                </div>
                            </NotionCard>
                         </div>
                     </div>
                 )}

                 {/* VIEW 2: PURCHASE HISTORY (MOVED UP) */}
                 {activeSubTab === 'orders' && (
                     <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
                        <NotionCard icon={TrendingUp} title="Recent Financial Performance">
                            <div className="space-y-6">
                                <div>
                                    <h4 className="text-xs font-bold text-notion-muted uppercase mb-3 border-b border-notion-border pb-1">Rolling 24 Month Activity</h4>
                                    <div className="grid grid-cols-5 gap-2">
                                        <div className="bg-gradient-to-br from-violet-50 to-violet-100 p-3 rounded border border-violet-200">
                                            <div className="text-[10px] text-violet-700 uppercase font-semibold">R24M GMV</div>
                                            <div className="text-base font-mono font-bold text-violet-900">¥{((enrichedProfile as any)?.rolling_24m_gmv || 0).toLocaleString(undefined, {minimumFractionDigits: 0, maximumFractionDigits: 0})}</div>
                                        </div>
                                        <div className="bg-gradient-to-br from-violet-50 to-violet-100 p-3 rounded border border-violet-200">
                                            <div className="text-[10px] text-violet-700 uppercase font-semibold">R24M NetSales</div>
                                            <div className="text-base font-mono font-bold text-violet-900">¥{((enrichedProfile as any)?.rolling_24m_netsales || 0).toLocaleString(undefined, {minimumFractionDigits: 0, maximumFractionDigits: 0})}</div>
                                        </div>
                                        <div className="bg-gradient-to-br from-violet-50 to-violet-100 p-3 rounded border border-violet-200">
                                            <div className="text-[10px] text-violet-700 uppercase font-semibold">R24M Orders</div>
                                            <div className="text-base font-mono font-bold text-violet-900">{((enrichedProfile as any)?.rolling_24m_orders || 0).toLocaleString(undefined, {minimumFractionDigits: 0, maximumFractionDigits: 0})}</div>
                                        </div>
                                        <div className="bg-gradient-to-br from-violet-50 to-violet-100 p-3 rounded border border-violet-200">
                                            <div className="text-[10px] text-violet-700 uppercase font-semibold">R24M AOV</div>
                                            <div className="text-base font-mono font-bold text-violet-900">¥{r24mAov.toLocaleString(undefined, {minimumFractionDigits: 0, maximumFractionDigits: 0})}</div>
                                        </div>
                                        <div className="bg-gradient-to-br from-violet-50 to-violet-100 p-3 rounded border border-violet-200">
                                            <div className="text-[10px] text-violet-700 uppercase font-semibold">R24M Refund</div>
                                            <div className="text-base font-mono font-bold text-violet-900">{(r24mRefundRate * 100).toFixed(1)}%</div>
                                        </div>
                                    </div>
                                </div>
                                <div>
                                    <h4 className="text-xs font-bold text-notion-muted uppercase mb-3 border-b border-notion-border pb-1">Last 1 Year Activity</h4>
                                    <div className="grid grid-cols-5 gap-2">
                                        <div className="bg-gradient-to-br from-emerald-50 to-emerald-100 p-3 rounded border border-emerald-200">
                                            <div className="text-[10px] text-emerald-700 uppercase font-semibold">L1Y GMV</div>
                                            <div className="text-base font-mono font-bold text-emerald-900">¥{(enrichedProfile?.l1y_gmv || 0).toLocaleString(undefined, {minimumFractionDigits: 0, maximumFractionDigits: 0})}</div>
                                        </div>
                                        <div className="bg-gradient-to-br from-emerald-50 to-emerald-100 p-3 rounded border border-emerald-200">
                                            <div className="text-[10px] text-emerald-700 uppercase font-semibold">L1Y NetSales</div>
                                            <div className="text-base font-mono font-bold text-emerald-900">¥{(enrichedProfile?.l1y_netsales || 0).toLocaleString(undefined, {minimumFractionDigits: 0, maximumFractionDigits: 0})}</div>
                                        </div>
                                        <div className="bg-gradient-to-br from-emerald-50 to-emerald-100 p-3 rounded border border-emerald-200">
                                            <div className="text-[10px] text-emerald-700 uppercase font-semibold">L1Y Orders</div>
                                            <div className="text-base font-mono font-bold text-emerald-900">{(enrichedProfile?.l1y_orders || 0).toLocaleString(undefined, {minimumFractionDigits: 0, maximumFractionDigits: 0})}</div>
                                        </div>
                                        <div className="bg-gradient-to-br from-emerald-50 to-emerald-100 p-3 rounded border border-emerald-200">
                                            <div className="text-[10px] text-emerald-700 uppercase font-semibold">L1Y AOV</div>
                                            <div className="text-base font-mono font-bold text-emerald-900">¥{l1yAov.toLocaleString(undefined, {minimumFractionDigits: 0, maximumFractionDigits: 0})}</div>
                                        </div>
                                        <div className="bg-gradient-to-br from-emerald-50 to-emerald-100 p-3 rounded border border-emerald-200">
                                            <div className="text-[10px] text-emerald-700 uppercase font-semibold">L1Y Refund</div>
                                            <div className="text-base font-mono font-bold text-emerald-900">{((enrichedProfile?.l1y_refund_rate || 0) * 100).toFixed(1)}%</div>
                                        </div>
                                    </div>
                                </div>
                                <div>
                                    <h4 className="text-xs font-bold text-notion-muted uppercase mb-3 border-b border-notion-border pb-1">Last 6 Months Activity</h4>
                                    <div className="grid grid-cols-5 gap-2">
                                        <div className="bg-gradient-to-br from-sky-50 to-sky-100 p-3 rounded border border-sky-200">
                                            <div className="text-[10px] text-sky-700 uppercase font-semibold">L6M GMV</div>
                                            <div className="text-base font-mono font-bold text-sky-900">¥{(enrichedProfile?.l6m_gmv || 0).toLocaleString(undefined, {minimumFractionDigits: 0, maximumFractionDigits: 0})}</div>
                                        </div>
                                        <div className="bg-gradient-to-br from-sky-50 to-sky-100 p-3 rounded border border-sky-200">
                                            <div className="text-[10px] text-sky-700 uppercase font-semibold">L6M NetSales</div>
                                            <div className="text-base font-mono font-bold text-sky-900">¥{(enrichedProfile?.l6m_netsales || 0).toLocaleString(undefined, {minimumFractionDigits: 0, maximumFractionDigits: 0})}</div>
                                        </div>
                                        <div className="bg-gradient-to-br from-sky-50 to-sky-100 p-3 rounded border border-sky-200">
                                            <div className="text-[10px] text-sky-700 uppercase font-semibold">L6M Orders</div>
                                            <div className="text-base font-mono font-bold text-sky-900">{(enrichedProfile?.l6m_orders || 0).toLocaleString(undefined, {minimumFractionDigits: 0, maximumFractionDigits: 0})}</div>
                                        </div>
                                        <div className="bg-gradient-to-br from-sky-50 to-sky-100 p-3 rounded border border-sky-200">
                                            <div className="text-[10px] text-sky-700 uppercase font-semibold">L6M AOV</div>
                                            <div className="text-base font-mono font-bold text-sky-900">¥{l6mAov.toLocaleString(undefined, {minimumFractionDigits: 0, maximumFractionDigits: 0})}</div>
                                        </div>
                                        <div className="bg-gradient-to-br from-sky-50 to-sky-100 p-3 rounded border border-sky-200">
                                            <div className="text-[10px] text-sky-700 uppercase font-semibold">L6M Refund</div>
                                            <div className="text-base font-mono font-bold text-sky-900">{((enrichedProfile?.l6m_refund_rate || 0) * 100).toFixed(1)}%</div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </NotionCard>
                         {groupedOrders.length > 0 ? (
                             <>
                                {/* Latest Order Highlight - Merged by Date */}
                                <div className="bg-gradient-to-r from-green-50 to-emerald-50 border border-green-100 p-5 rounded-sm shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
                                     <div className="flex items-start gap-4">
                                         <div className="p-3 bg-white rounded-full text-green-600 shadow-sm border border-green-100">
                                             <Truck size={24} />
                                         </div>
                                         <div>
                                             <h3 className="text-sm font-bold text-green-900 uppercase tracking-wide mb-1">Latest Purchase</h3>
                                             <div className="text-2xl font-serif text-green-900">
                                                 ¥{groupedOrders[0]?.total_gmv.toLocaleString() || '0'}
                                             </div>
                                             <div className="text-xs text-green-800 mt-1 flex items-center gap-2">
                                                 <Calendar size={12} /> {groupedOrders[0]?.date || 'N/A'}
                                                 <span className="w-1 h-1 bg-green-400 rounded-full"></span>
                                                 <span>{groupedOrders[0]?.fp_md || 'FP'}</span>
                                             </div>
                                         </div>
                                     </div>
                                     <div className="flex-1 bg-white/60 p-3 rounded border border-green-100/50">
                                         <span className="text-[10px] text-green-800 font-bold uppercase block mb-1">Items in this order:</span>
                                         <ul className="list-disc list-inside text-sm text-green-900">
                                             {groupedOrders[0]?.items.map((item: string, idx: number) => (
                                                 <li key={idx}>{item}</li>
                                             ))}
                                         </ul>
                                     </div>
                                </div>

                                {/* Full History Table */}
                                <NotionCard icon={History} title="Full Order History">
                                     <div className="overflow-x-auto">
                                         <table className="w-full text-left text-sm">
                                             <thead>
                                                 <tr className="border-b border-notion-border text-notion-muted text-xs uppercase bg-notion-gray_bg/30">
                                                     <th className="py-2 px-3 font-semibold">Date</th>
                                                     <th className="py-2 px-3 font-semibold">Order ID</th>
                                                     <th className="py-2 px-3 font-semibold">Item</th>
                                                     <th className="py-2 px-3 font-semibold">GMV</th>
                                                     <th className="py-2 px-3 font-semibold">Gross Qty</th>
                                                     <th className="py-2 px-3 font-semibold">NetSales</th>
                                                     <th className="py-2 px-3 font-semibold">Net Qty</th>
                                                     <th className="py-2 px-3 font-semibold">Refund</th>
                                                     <th className="py-2 px-3 font-semibold">Type</th>
                                                 </tr>
                                             </thead>
                                             <tbody className="divide-y divide-notion-border">
                                                 {(enrichedProfile?.order_history || []).map((order: OrderRecord) => (
                                                     <tr key={order.order_id} className="hover:bg-notion-hover transition-colors">
                                                         <td className="py-3 px-3 font-mono text-xs whitespace-nowrap">{order.date}</td>
                                                         <td className="py-3 px-3 font-mono text-xs text-notion-muted whitespace-nowrap">{order.order_id}</td>
                                                         <td className="py-3 px-3">
                                                             <div className="flex items-center gap-2">
                                                                 {order.image_url && (
                                                                     <img
                                                                         src={order.image_url}
                                                                         alt={order.items[0]}
                                                                         className="w-12 h-12 object-cover rounded border border-notion-border"
                                                                         onError={(e) => {
                                                                             const target = e.target as HTMLImageElement;
                                                                             target.style.display = 'none';
                                                                         }}
                                                                     />
                                                                 )}
                                                                 <div className="flex flex-col gap-0.5">
                                                                     {order.items.slice(0, 2).map((item: string, i: number) => (
                                                                         <span key={i} className="text-xs line-clamp-1">{item}</span>
                                                                     ))}
                                                                 </div>
                                                             </div>
                                                         </td>
                                                         <td className="py-3 px-3 font-semibold text-xs">¥{(Number(order.gmv) || 0).toLocaleString()}</td>
                                                         <td className="py-3 px-3 font-semibold text-xs text-center">{order.gross_qty || order.quantity || 0}</td>
                                                         <td className="py-3 px-3 font-semibold text-xs">¥{(Number(order.netsales) || 0).toLocaleString()}</td>
                                                         <td className="py-3 px-3 font-semibold text-xs text-center">
                                                             <span className={Number(order.net_qty || 0) < (order.gross_qty || order.quantity || 0) ? 'text-orange-600' : ''}>
                                                                 {order.net_qty || 0}
                                                             </span>
                                                         </td>
                                                         <td className="py-3 px-3 text-xs">
                                                             {(Number(order.refund_amount) || 0) > 0 ? (
                                                                 <span className="text-red-600 font-semibold">¥{(Number(order.refund_amount) || 0).toLocaleString()}</span>
                                                             ) : (
                                                                 <span className="text-notion-muted">-</span>
                                                             )}
                                                         </td>
                                                         <td className="py-3 px-3">
                                                             <span className={`text-[10px] px-2 py-0.5 rounded-full border ${
                                                                 order.fp_md === 'FP'
                                                                     ? 'bg-green-50 text-green-700 border-green-100'
                                                                     : 'bg-orange-50 text-orange-700 border-orange-100'
                                                             }`}>
                                                                 {order.fp_md}
                                                             </span>
                                                         </td>
                                                     </tr>
                                                 ))}
                                             </tbody>
                                         </table>
                                     </div>
                                </NotionCard>
                             </>
                         ) : (
                             <div className="flex flex-col items-center justify-center h-64 text-notion-muted bg-notion-gray_bg/30 rounded border border-notion-border border-dashed">
                                 <ShoppingBag size={32} className="mb-2 opacity-50" />
                                 <p>No purchase history found for this user.</p>
                             </div>
                         )}
                     </div>
                 )}

                 {/* VIEW 3: COMMUNICATION (MOVED DOWN) */}
                 {activeSubTab === 'chat' && (
                     <div className="space-y-4 animate-in fade-in slide-in-from-bottom-2 duration-300 h-full flex flex-col">
                         {/* Communication Metrics Strip */}
                         <div className="grid grid-cols-4 gap-3 bg-white border border-notion-border p-3 rounded-sm shadow-sm flex-none">
                             <div className="flex flex-col items-center justify-center border-r border-notion-border">
                                 <div className="text-[10px] text-notion-muted uppercase font-bold tracking-wider mb-1">Recent Freq (30d)</div>
                                 <div className="text-base font-mono text-notion-text">{enrichedProfile?.l30d_chat_frequency_days || 0} days</div>
                             </div>
                             <div className="flex flex-col items-center justify-center border-r border-notion-border">
                                 <div className="text-[10px] text-notion-muted uppercase font-bold tracking-wider mb-1">Recent Freq (3m)</div>
                                 <div className="text-base font-mono text-notion-text">{enrichedProfile?.l3m_chat_frequency_days || 0} days</div>
                             </div>
                             <div className="flex flex-col items-center justify-center border-r border-notion-border">
                                 <div className="text-[10px] text-notion-muted uppercase font-bold tracking-wider mb-1">Avg Interval</div>
                                 <div className="text-base font-mono text-notion-text">{Number(enrichedProfile?.avg_chat_interval_days || 0).toFixed(1)} days</div>
                             </div>
                             <div className="flex flex-col items-center justify-center">
                                 <div className="text-[10px] text-notion-muted uppercase font-bold tracking-wider mb-1">Last Contact</div>
                                 <div className="text-xs font-mono text-notion-text text-center px-1">
                                     {enrichedProfile?.last_chat_date ?
                                         new Date(enrichedProfile.last_chat_date).toLocaleDateString('zh-CN', {
                                             year: 'numeric',
                                             month: '2-digit',
                                             day: '2-digit'
                                         }) : 'N/A'}
                                 </div>
                             </div>
                         </div>

                         {/* Chat Log */}
                         <div className="flex-1 bg-notion-sidebar border border-notion-border rounded-sm flex flex-col overflow-hidden shadow-inner relative">
                            <div className="flex-1 overflow-y-auto p-4 scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-transparent space-y-6 bg-white">
                                {sortedDates.map((date) => {
                                    const msgs = groupedMessages[date];
                                    return (
                                    <div key={date} className="relative">
                                        {/* Date Header / Collapsible Trigger */}
                                        <div className="sticky top-0 z-10 flex justify-center mb-4">
                                            <button 
                                                onClick={() => toggleDate(date)}
                                                className="bg-gray-100 hover:bg-gray-200 text-gray-600 text-[11px] font-medium px-3 py-1 rounded-full border border-gray-200 shadow-sm flex items-center gap-1 transition-colors backdrop-blur-sm bg-opacity-90"
                                            >
                                                <Calendar size={10} />
                                                {date}
                                                {openDates[date] === false ? <ChevronRight size={10}/> : <ChevronDown size={10}/>}
                                            </button>
                                        </div>

                                        {/* Messages Area */}
                                        {openDates[date] !== false && (
                                            <div className="space-y-3 px-2">
                                                {msgs.map((msg) => {
                                                    const isBuyer = msg.sender_nick === currentSession.user_nick;
                                                    return (
                                                        <div key={msg.id} className={`flex ${isBuyer ? 'justify-start' : 'justify-end'}`}>
                                                            {/* Chat Bubble: Limited Width */}
                                                            <div className={`max-w-[80%] min-w-[20%] p-3 rounded-lg text-sm shadow-sm border group hover:shadow-md transition-shadow ${
                                                                isBuyer
                                                                ? 'bg-white border-notion-border text-notion-text rounded-tl-none'
                                                                : 'bg-blue-50 border-blue-100 text-blue-900 rounded-tr-none'
                                                            }`}>
                                                                <div className="flex justify-between items-center gap-4 mb-1 border-b border-black/5 pb-1">
                                                                    <span className={`text-[10px] font-bold truncate max-w-[100px] ${isBuyer ? 'text-notion-muted' : 'text-blue-700'}`}>
                                                                        {isBuyer ? msg.sender_nick : 'Support'}
                                                                    </span>
                                                                    <span className="text-[10px] opacity-40 font-mono">{msg.msg_time.split(' ')[1]}</span>
                                                                </div>
                                                                {msg.msg_type === 'image' ? (
                                                                    <div className="mt-1">
                                                                        <img
                                                                            src={msg.content}
                                                                            alt="Chat image"
                                                                            className="max-w-[300px] rounded border border-notion-border"
                                                                        />
                                                                    </div>
                                                                ) : (
                                                                    <p className="leading-relaxed whitespace-pre-wrap mt-1">{msg.content}</p>
                                                                )}
                                                            </div>
                                                        </div>
                                                    )
                                                })}
                                            </div>
                                        )}
                                    </div>
                                    );
                                })}
                            </div>
                        </div>
                     </div>
                 )}
             </div>
        </div>
    </div>
  );
};

export default ChatAnalysis;
