import React, { useState, useMemo } from 'react';
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
  Zap,
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
  Info
} from 'lucide-react';
import {
  KEYWORD_DATA,
  INTENT_DISTRIBUTION,
  HOURLY_ACTIVITY,
  DAILY_STATS,
  MOCK_SESSIONS,
} from './constants';
import { BuyerSession, CustomerProfile, ChatMessage, OrderRecord, IntentType } from './types';
import { apiClient, DashboardMetrics, BuyerProfile as APIBuyerProfile } from './api/client';
import { useDataFetchingWithRetry } from './hooks/useDataFetching';
import { LoadingSpinner, CardSkeleton, TableSkeleton, MetricCardSkeleton } from './components/common/LoadingState';
import { ErrorAlert, EmptyState } from './components/common/ErrorAlert';

// --- Notion Style Components ---

const NotionCard: React.FC<{ children: React.ReactNode; className?: string; title?: string; icon?: any; action?: React.ReactNode }> = ({ children, className = '', title, icon: Icon, action }) => (
  <div className={`bg-notion-bg border border-notion-border rounded-sm shadow-card p-4 ${className}`}>
    {title && (
      <div className="flex items-center justify-between mb-4 border-b border-notion-border pb-2">
        <div className="flex items-center gap-2">
            {Icon && <Icon size={16} className="text-notion-text opacity-80" />}
            <h3 className="text-notion-text font-semibold text-sm tracking-wide uppercase">{title}</h3>
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

// --- New Keyword Analysis Component ---

const KeywordAnalysisPanel: React.FC<{ timeRange: '7d' | '15d' | '30d' | '90d' | '1y' }> = ({ timeRange }) => {
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);

  // Cool Tone Palette (Blue, Cyan, Indigo, Slate) - Professional, Clean, Distinct
  const COOL_PALETTE = [
    '#3B82F6', // Blue 500 (Primary)
    '#0EA5E9', // Sky 500
    '#06B6D4', // Cyan 500
    '#6366F1', // Indigo 500
    '#64748B', // Slate 500 (Neutral Cool)
    '#8B5CF6', // Violet 500 (Accent)
  ];

  // ⚠️ 占位数据 - 后端API未实现，显示为0
  // TODO: 等待第四阶段开发完成后再替换为真实数据
  const { categoryData, keywordData, totalVolume } = useMemo(() => {
    // 创建空的分类数据（显示为0）
    const categoryDataList = [
      { name: 'Shipping', value: 0, fill: COOL_PALETTE[0] },
      { name: 'Specs', value: 0, fill: COOL_PALETTE[1] },
      { name: 'After-sales', value: 0, fill: COOL_PALETTE[2] },
      { name: 'Discount', value: 0, fill: COOL_PALETTE[3] },
      { name: 'Packaging', value: 0, fill: COOL_PALETTE[4] },
      { name: 'Gifted', value: 0, fill: COOL_PALETTE[5] },
    ];

    // 创建空的关键词数据（显示为0）
    const keywordDataList = [
      { text: 'Shipping Speed', value: 0, category: 'Shipping', fill: COOL_PALETTE[0] },
      { text: 'Product Quality', value: 0, category: 'Specs', fill: COOL_PALETTE[1] },
      { text: 'Return Policy', value: 0, category: 'After-sales', fill: COOL_PALETTE[2] },
      { text: 'Price', value: 0, category: 'Discount', fill: COOL_PALETTE[3] },
      { text: 'Packaging', value: 0, category: 'Packaging', fill: COOL_PALETTE[4] },
    ];

    return {
      categoryData: categoryDataList,
      keywordData: keywordDataList,
      totalVolume: 0
    };
  }, [timeRange, selectedCategory]);

  return (
    <NotionCard
        title="Keyword & Issue Analysis"
        icon={Database}
        className="h-[500px] flex flex-col"
        action={
            selectedCategory && (
                <button
                    onClick={() => setSelectedCategory(null)}
                    className="px-2 py-1 text-xs text-notion-muted hover:text-blue-600 border border-transparent hover:border-blue-200 rounded transition-colors flex items-center gap-1"
                >
                    <XCircle size={12}/> Clear Filter: {selectedCategory}
                </button>
            )
        }
    >
        <div className="flex flex-col lg:flex-row h-full gap-8">
            {/* Left: Category Distribution (Donut) */}
            <div className="flex-1 flex flex-col">
                <div className="flex items-center justify-between mb-2">
                    <h4 className="text-xs font-bold text-notion-muted uppercase tracking-wider flex items-center gap-2">
                        <PieIcon size={12} /> Categories Distribution
                    </h4>
                    <span className="px-2 py-1 bg-yellow-50 text-yellow-700 border border-yellow-200 rounded text-[10px] font-medium">
                        数据开发中 (Coming Soon)
                    </span>
                </div>
                <div className="flex-1 relative">
                    <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                            <Pie
                                data={categoryData}
                                cx="50%"
                                cy="50%"
                                innerRadius={60}
                                outerRadius={80}
                                paddingAngle={2}
                                dataKey="value"
                                onClick={(data) => setSelectedCategory(data.name === selectedCategory ? null : data.name)}
                                label={({ name, percent }) => percent > 0 ? `${name} ${(percent * 100).toFixed(0)}%` : ''}
                                labelLine={{ stroke: '#9B9A97', strokeWidth: 1 }}
                            >
                                {categoryData.map((entry, index) => (
                                    <Cell
                                        key={`cell-${index}`}
                                        fill={entry.fill}
                                        stroke={selectedCategory === entry.name ? '#1E3A8A' : 'none'}
                                        strokeWidth={selectedCategory === entry.name ? 2 : 0}
                                        className="cursor-pointer hover:opacity-80 transition-all"
                                    />
                                ))}
                            </Pie>
                            <Tooltip
                                contentStyle={{ backgroundColor: '#fff', borderColor: '#E9E9E7', borderRadius: '4px', fontSize: '12px' }}
                                itemStyle={{ color: '#37352F' }}
                                formatter={(value: number) => [`${value}`, 'Volume']}
                            />
                        </PieChart>
                    </ResponsiveContainer>
                    {/* Centered Label */}
                    <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                        <span className="text-2xl font-bold text-notion-muted">0</span>
                        <span className="text-[10px] text-notion-muted uppercase tracking-wider">Total</span>
                    </div>
                </div>
            </div>

            {/* Separator */}
            <div className="w-px bg-notion-border hidden lg:block my-4"></div>

            {/* Right: Top Keywords (Bar) */}
            <div className="flex-[1.2] flex flex-col">
                <div className="flex items-center justify-between mb-2">
                     <h4 className="text-xs font-bold text-notion-muted uppercase tracking-wider flex items-center gap-2">
                        <BarChartIcon size={12} />
                        {selectedCategory ? `${selectedCategory} Top Keywords` : 'Overall Top Keywords'}
                    </h4>
                </div>
                <div className="flex-1">
                    <ResponsiveContainer width="100%" height="100%">
                        <BarChart
                            layout="vertical"
                            data={keywordData}
                            margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                        >
                            <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#E9E9E7" />
                            <XAxis type="number" hide />
                            <YAxis
                                dataKey="text"
                                type="category"
                                width={100}
                                tick={{ fontSize: 11, fill: '#37352F' }}
                                axisLine={false}
                                tickLine={false}
                            />
                            <Tooltip
                                cursor={{ fill: '#F7F7F5' }}
                                contentStyle={{ backgroundColor: '#fff', borderColor: '#E9E9E7', borderRadius: '4px', fontSize: '12px' }}
                            />
                            <Bar dataKey="value" radius={[0, 4, 4, 0]} barSize={20} animationDuration={500}>
                                {keywordData.map((entry, index) => (
                                    <Cell key={`cell-${index}`} fill={entry.fill || '#9CA3AF'} />
                                ))}
                                <LabelList dataKey="value" position="right" fontSize={11} fill="#9CA3AF" />
                            </Bar>
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            </div>
        </div>

        {/* Insight Footer */}
        <div className="mt-4 pt-3 border-t border-notion-border flex items-start gap-3">
            <div className="p-1.5 bg-yellow-50 rounded text-yellow-600 shrink-0 mt-0.5">
                <Lightbulb size={14} />
            </div>
             <div className="text-xs text-notion-text">
                <span className="font-semibold text-yellow-800">数据开发中:</span>
                {' '}关键词分析功能正在开发中，将在第四阶段完成。届时将展示客户聊天中的关键词频率、问题类型分布等数据。
            </div>
        </div>
    </NotionCard>
  );
};

// --- Dashboard Sub-Components ---

const DashboardOverview: React.FC = () => {
  // 全局日期筛选器状态
  const [timeRange, setTimeRange] = useState<'7d' | '15d' | '30d' | '90d' | '1y'>('1y');

  // 获取Dashboard指标数据
  const { data: metrics, isLoading: metricsLoading, error: metricsError } = useDataFetchingWithRetry<DashboardMetrics>(
    () => apiClient.getDashboardMetrics(),
    2 // 重试2次
  );

  // 获取可操作客户数据
  const { data: actionableCustomers, isLoading: actionableLoading, error: actionableError } = useDataFetchingWithRetry(
    () => apiClient.getActionableCustomers(50),
    2
  );

  // 格式化数字
  const formatNumber = (num: number | string) => {
    const n = Number(num);
    if (n >= 10000) return (n / 10000).toFixed(1) + '万';
    if (n >= 1000) return (n / 1000).toFixed(1) + 'K';
    return n.toLocaleString();
  };

  // 格式化金额
  const formatCurrency = (num: number | string) => {
    const n = Number(num);
    if (n >= 10000) return '¥' + (n / 10000).toFixed(1) + '万';
    return '¥' + formatNumber(n);
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      {/* Global Time Range Filter */}
      <div className="flex justify-end">
        <div className="flex bg-notion-gray_bg p-0.5 rounded-md border border-notion-border shadow-sm">
          {[
            { id: '7d' as const, label: '7 Days' },
            { id: '15d' as const, label: '15 Days' },
            { id: '30d' as const, label: '1 Mo' },
            { id: '90d' as const, label: '1 Qtr' },
            { id: '1y' as const, label: '1 Yr' }
          ].map((range) => (
            <button
              key={range.id}
              onClick={() => setTimeRange(range.id)}
              className={`px-4 py-2 text-sm font-medium rounded-sm transition-all ${
                timeRange === range.id
                ? 'bg-white text-blue-700 shadow-sm border border-blue-100'
                : 'text-notion-muted hover:text-notion-text'
              }`}
            >
              {range.label}
            </button>
          ))}
        </div>
      </div>
      {/* Top Metrics - Minimalist */}
      {metricsLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCardSkeleton />
          <MetricCardSkeleton />
          <MetricCardSkeleton />
          <MetricCardSkeleton />
        </div>
      ) : metricsError ? (
        <ErrorAlert message="无法加载Dashboard指标" onRetry={() => window.location.reload()} />
      ) : metrics ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {[
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
          ].map((stat, idx) => (
            <NotionCard key={idx} className="hover:bg-notion-hover transition-colors cursor-pointer">
              <div className="flex items-center justify-between mb-2">
                <span className="text-notion-muted text-sm flex items-center gap-2">
                   <stat.icon size={14} /> {stat.label}
                </span>
              </div>
              <div className="flex items-end gap-2">
                 <h4 className="text-3xl font-serif text-notion-text">{stat.value}</h4>
              </div>
              <div className="text-xs text-notion-muted mt-1">{stat.change}</div>
            </NotionCard>
          ))}
        </div>
      ) : null}

      {/* Row 2: Keyword Analysis (New Module) */}
      <KeywordAnalysisPanel timeRange={timeRange} />

      {/* Row 3: Actionable Customers Table (New) */}
      <NotionCard
        title="Priority Attention Board (High Risk / Actionable)"
        icon={AlertTriangle}
        className="overflow-hidden"
        action={
            <button className="flex items-center gap-1.5 px-3 py-1.5 bg-notion-gray_bg text-notion-text border border-notion-border rounded text-xs font-medium hover:bg-gray-200 transition-colors">
                <Download size={12} /> Download CSV
            </button>
        }
      >
        {actionableLoading ? (
          <TableSkeleton rows={5} />
        ) : actionableError ? (
          <ErrorAlert message="无法加载可操作客户列表" />
        ) : actionableCustomers ? (
          <div className="flex flex-col h-[500px]">
            {/* Scrollable Table */}
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
                  {actionableCustomers.high_churn_risk.map((buyer: any, idx) => (
                    <tr key={`high-${idx}`} className="hover:bg-notion-hover transition-colors">
                      <td className="py-3 px-4 font-medium text-notion-text">{buyer.buyer_nick || buyer.user_nick || 'Unknown'}</td>
                      <td className="py-3 px-4">
                        <NotionTag text={buyer.vip_level} color="red" />
                      </td>
                      <td className="py-3 px-4 text-xs font-mono">¥{formatNumber(buyer.l6m_netsales)}</td>
                      <td className="py-3 px-4">
                        <span className="text-xs font-bold text-red-600">{buyer.churn_risk}</span>
                      </td>
                      <td className="py-3 px-4 text-notion-muted text-xs">{buyer.last_purchase_date}</td>
                      <td className="py-3 px-4 text-right">
                        <button className="text-blue-600 hover:text-blue-800 text-xs font-semibold underline">
                          Handle
                        </button>
                      </td>
                    </tr>
                  ))}
                  {/* 高价值客户 */}
                  {actionableCustomers.high_value.map((buyer: any, idx) => (
                    <tr key={`value-${idx}`} className="hover:bg-notion-hover transition-colors">
                      <td className="py-3 px-4 font-medium text-notion-text">{buyer.buyer_nick || buyer.user_nick || 'Unknown'}</td>
                      <td className="py-3 px-4">
                        <NotionTag text={buyer.vip_level} color="orange" />
                      </td>
                      <td className="py-3 px-4 text-xs font-mono">¥{formatNumber(buyer.l6m_netsales)}</td>
                      <td className="py-3 px-4">
                        <span className="text-xs font-bold text-green-600">{buyer.churn_risk}</span>
                      </td>
                      <td className="py-3 px-4 text-notion-muted text-xs">{buyer.last_purchase_date}</td>
                      <td className="py-3 px-4 text-right">
                        <button className="text-blue-600 hover:text-blue-800 text-xs font-semibold underline">
                          Follow Up
                        </button>
                      </td>
                    </tr>
                  ))}
                  {/* 中流失风险 */}
                  {actionableCustomers.medium_churn_risk.map((buyer: any, idx) => (
                    <tr key={`medium-${idx}`} className="hover:bg-notion-hover transition-colors">
                      <td className="py-3 px-4 font-medium text-notion-text">{buyer.buyer_nick || buyer.user_nick || 'Unknown'}</td>
                      <td className="py-3 px-4">
                        <NotionTag text={buyer.vip_level} color="yellow" />
                      </td>
                      <td className="py-3 px-4 text-xs font-mono">¥{formatNumber(buyer.l6m_netsales)}</td>
                      <td className="py-3 px-4">
                        <span className="text-xs font-bold text-yellow-600">{buyer.churn_risk}</span>
                      </td>
                      <td className="py-3 px-4 text-notion-muted text-xs">{buyer.last_purchase_date}</td>
                      <td className="py-3 px-4 text-right">
                        <button className="text-blue-600 hover:text-blue-800 text-xs font-semibold underline">
                          Monitor
                        </button>
                      </td>
                    </tr>
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

      {/* Row 4: Other Charts (Sentiment, Intent, Peak Hours) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <NotionCard title="Sentiment Trend (7 Days)" icon={TrendingUp} className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={DAILY_STATS}>
              <CartesianGrid strokeDasharray="3 3" stroke="#E9E9E7" vertical={false} />
              <XAxis dataKey="date" stroke="#9B9A97" tick={{ fill: '#9B9A97', fontSize: 10 }} axisLine={false} tickLine={false} />
              <YAxis stroke="#9B9A97" tick={{ fill: '#9B9A97', fontSize: 10 }} domain={[0, 1]} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={{ backgroundColor: '#fff', borderColor: '#E9E9E7' }} />
              <Line type="monotone" dataKey="sentimentScore" stroke="#EA580C" strokeWidth={2} dot={{ fill: '#fff', stroke: '#EA580C', strokeWidth: 2 }} activeDot={{ r: 4 }} />
            </LineChart>
          </ResponsiveContainer>
        </NotionCard>

        <NotionCard title="Intent Distribution" icon={Users} className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <RadarChart cx="50%" cy="50%" outerRadius="70%" data={INTENT_DISTRIBUTION}>
              <PolarGrid stroke="#E9E9E7" />
              <PolarAngleAxis dataKey="subject" tick={{ fill: '#37352F', fontSize: 10 }} />
              <PolarRadiusAxis angle={30} domain={[0, 150]} tick={false} axisLine={false} />
              <Radar name="Intents" dataKey="A" stroke="#F59E0B" fill="#F59E0B" fillOpacity={0.4} />
              <Tooltip contentStyle={{ backgroundColor: '#fff', borderColor: '#E9E9E7' }} />
            </RadarChart>
          </ResponsiveContainer>
        </NotionCard>
        
        <NotionCard title="Peak Hours" icon={Clock} className="h-80">
            <ResponsiveContainer width="100%" height="100%">
                <BarChart data={HOURLY_ACTIVITY}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E9E9E7" vertical={false} />
                <XAxis dataKey="hour" stroke="#9B9A97" tick={{ fill: '#9B9A97', fontSize: 10 }} axisLine={false} tickLine={false} />
                <YAxis stroke="#9B9A97" tick={{ fill: '#9B9A97', fontSize: 10 }} axisLine={false} tickLine={false} />
                <Tooltip cursor={{fill: '#F7F7F5'}} contentStyle={{ backgroundColor: '#fff', borderColor: '#E9E9E7' }} />
                <Bar dataKey="value" fill="#9B9A97" radius={[2, 2, 0, 0]} activeBar={{ fill: '#37352F' }} />
                </BarChart>
            </ResponsiveContainer>
        </NotionCard>
      </div>
    </div>
  );
};

// --- Chat Analysis with CRM Features ---

const ChatAnalysis: React.FC = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedSession, setSelectedSession] = useState<BuyerSession | null>(null);
  const [activeSubTab, setActiveSubTab] = useState<'profile' | 'orders' | 'chat'>('profile');
  const [enableAI, setEnableAI] = useState(false); // AI分析开关

  // Track open states for chat dates. Default empty.
  const [openDates, setOpenDates] = useState<Record<string, boolean>>({});

  // 获取买家列表数据（真实API）
  const { data: buyersData, isLoading: buyersLoading, error: buyersError } = useDataFetchingWithRetry(
    () => apiClient.getBuyers({ limit: 100, sort_by: 'last_purchase' }),
    2
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
          tags: [buyer.vip_level, buyer.churn_risk, buyer.buyer_type],
          intent_scores: INTENT_DISTRIBUTION,
          order_history: [],
          analysis: {
            summary: '点击查看详细分析',
            key_interests: [],
            pain_points: [],
            recommended_action: '建议跟进'
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

  // 当前选中的会话（如果没有选中，默认选择第一个）
  const currentSession = selectedSession || (filteredSessions.length > 0 ? filteredSessions[0] : null);

  // 当选中的用户改变时，获取其详细信息（包括AI分析）
  const { data: buyerProfile, isLoading: profileLoading, error: profileError, refetch: refetchProfile } = useDataFetchingWithRetry(
    async () => {
      if (!currentSession?.user_nick) return null;
      // 如果启用AI分析，传入include_ai=true
      const profile = await apiClient.getBuyerProfile(currentSession.user_nick, enableAI);

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
        } as BuyerProfile & { order_history: OrderRecord[], chat_history: ChatMessage[] };
      } catch (error) {
        console.error('Failed to fetch orders/chats:', error);
        // 即使orders/chats失败，也返回基本profile
        return {
          ...profile,
          order_history: [],
          chat_history: []
        } as BuyerProfile & { order_history: OrderRecord[], chat_history: ChatMessage[] };
      }
    },
    2,
    [currentSession?.user_nick, enableAI] // 当用户或AI开关改变时重新获取
  );

  const handleSelectUser = (session: BuyerSession) => {
    setSelectedSession(session);
    setActiveSubTab('profile'); // Reset to profile on user change
    // Open all dates by default when selecting a new user for better visibility
    const dates: Record<string, boolean> = {};
    session.messages.forEach(m => {
       const d = m.msg_time.split(' ')[0];
       dates[d] = true;
    });
    setOpenDates(dates);
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
      l6m_netsales: buyerProfile.l6m_netsales ?? currentSession.profile.l6m_netsales,
      l6m_orders: buyerProfile.l6m_orders ?? currentSession.profile.l6m_orders,
      l1y_netsales: (buyerProfile as any).l1y_netsales ?? currentSession.profile.l1y_netsales,
      l1y_orders: (buyerProfile as any).l1y_orders ?? currentSession.profile.l1y_orders,
      l6m_refund_rate: Number((buyerProfile as any).l6m_refund_rate ?? 0),
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
      // 包含订单历史和聊天记录
      order_history: (buyerProfile as any).order_history || currentSession.profile.order_history || [],
      chat_history: (buyerProfile as any).chat_history || currentSession.profile.chat_history || [],
    };
  }, [currentSession, buyerProfile]);

  // Calculations for Metrics
  const historicalAov = enrichedProfile?.total_orders > 0
    ? (enrichedProfile.historical_ltv || 0) / enrichedProfile.total_orders
    : 0;

  const l6mAov = enrichedProfile?.l6m_orders > 0
    ? (enrichedProfile.l6m_netsales || 0) / enrichedProfile.l6m_orders
    : 0;

  // Group messages by date and sort by date ascending (oldest first)
  const groupedMessages = useMemo<Record<string, ChatMessage[]>>(() => {
     const chatHistory = enrichedProfile?.chat_history || currentSession?.messages || [];
     if (!chatHistory || chatHistory.length === 0) return {};

     const groups: Record<string, ChatMessage[]> = {};
     chatHistory.forEach((msg: ChatMessage) => {
         const date = msg.msg_time.split(' ')[0];
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

  const toggleDate = (date: string) => {
     setOpenDates(prev => ({ ...prev, [date]: !prev[date] }));
  };
  
  if (!currentSession || !currentSession.profile) return <div className="p-8 text-center text-notion-muted">加载中...</div>;

  return (
    <div className="h-[calc(100vh-120px)] flex gap-6">
        {/* Left Sidebar: Search & User List */}
        <div className="w-64 flex-none border border-notion-border bg-notion-sidebar rounded-sm flex flex-col shadow-sm">
             <div className="p-3 border-b border-notion-border bg-white rounded-t-sm">
                <div className="relative">
                    <Search className="absolute left-2.5 top-2.5 text-notion-muted" size={14} />
                    <input
                        type="text"
                        placeholder="Search user..."
                        className="w-full bg-notion-gray_bg border-0 text-notion-text pl-9 pr-3 py-1.5 rounded text-sm focus:ring-1 focus:ring-blue-400 placeholder-notion-muted/70 transition-all"
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                    />
                </div>
             </div>
             <div className="flex-1 overflow-y-auto">
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
                        <div className="flex items-center gap-2 mb-1">
                            <div className={`w-2 h-2 rounded-full ${session.sentimentScore > 0.6 ? 'bg-green-400' : session.sentimentScore < 0.3 ? 'bg-red-400' : 'bg-gray-400'}`}></div>
                            <span className="font-medium text-sm text-notion-text truncate">{session.user_nick}</span>
                        </div>
                        <div className="flex items-center justify-between mt-1">
                             <span className="text-[10px] text-notion-muted bg-notion-gray_bg px-1.5 py-0.5 rounded">{session.dominantIntent}</span>
                             <span className="text-[10px] text-notion-muted group-hover:text-notion-text">{session.profile.last_interaction_date}</span>
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
                                <span className="text-notion-muted">Top 3: <span className="font-semibold text-notion-text">{(enrichedProfile as any)?.top_category || 'N/A'} / {(enrichedProfile as any)?.second_category || 'N/A'} / {(enrichedProfile as any)?.third_category || 'N/A'}</span></span>
                             </div>
                         </div>
                     </div>
                     <div className="flex items-center gap-3">
                         {/* AI分析开关 */}
                         <div className="flex items-center gap-2 px-3 py-1.5 bg-purple-50 border border-purple-200 rounded-md">
                            <Sparkles size={14} className="text-purple-600" />
                            <label className="flex items-center gap-2 cursor-pointer">
                              <span className="text-xs font-medium text-purple-900">AI分析</span>
                              <button
                                onClick={() => setEnableAI(!enableAI)}
                                className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
                                  enableAI ? 'bg-purple-600' : 'bg-purple-200'
                                }`}
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
                             {currentSession.profile.tags.map(t => <NotionTag key={t} text={t} color="orange" />)}
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
                         <NotionCard icon={Sparkles} title="AI Persona Analysis">
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

                                {/* 是否启用了AI分析的提示 */}
                                 {enableAI && !enrichedProfile?.analysis?.error && (
                                   <div className="flex items-center gap-2 text-xs text-purple-700 bg-purple-50 px-3 py-2 rounded border border-purple-200">
                                     <Sparkles size={12} />
                                     <span>AI分析已基于买家历史数据和聊天记录生成</span>
                                   </div>
                                 )}

                                 {!enableAI && (
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
                                              <span className="text-xs text-gray-500 italic">启用AI分析以获取兴趣点</span>
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
                                              <span className="text-xs text-gray-500 italic">启用AI分析以获取痛点</span>
                                            )}
                                        </div>
                                    </div>
                                </div>
                                <div className="flex gap-3 bg-yellow-50 p-3 rounded border border-yellow-100 items-start mt-2">
                                     <Zap size={18} className="text-yellow-600 shrink-0 mt-0.5"/>
                                     <div className="flex flex-col gap-1">
                                         <span className="text-xs font-bold text-yellow-800 uppercase">Recommended Action</span>
                                         <span className="text-sm text-yellow-900 leading-snug">
                                             {enrichedProfile?.analysis?.recommended_action || '建议根据买家情况制定跟进策略'}
                                         </span>
                                     </div>
                                </div>
                            </div>
                            )}
                         </NotionCard>

                         <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
                             {/* Financial Metrics */}
                             <NotionCard icon={TrendingUp} title="Recent Financial Performance">
                                 <div className="space-y-6">
                                     {/* Recent L6M Metrics */}
                                     <div>
                                         <h4 className="text-xs font-bold text-notion-muted uppercase mb-3 border-b border-notion-border pb-1">Last 6 Months Activity</h4>
                                         <div className="grid grid-cols-2 gap-3">
                                             <div className="bg-notion-gray_bg p-3 rounded border border-notion-border">
                                                 <div className="text-[10px] text-notion-muted uppercase">L6M NetSales</div>
                                                 <div className="text-lg font-mono font-semibold">¥{(enrichedProfile?.l6m_netsales || 0).toLocaleString()}</div>
                                             </div>
                                             <div className="bg-notion-gray_bg p-3 rounded border border-notion-border">
                                                 <div className="text-[10px] text-notion-muted uppercase">L6M Orders</div>
                                                 <div className="text-lg font-mono font-semibold">{(enrichedProfile?.l6m_orders || 0).toLocaleString()}</div>
                                             </div>
                                             <div className="bg-notion-gray_bg p-3 rounded border border-notion-border">
                                                 <div className="text-[10px] text-notion-muted uppercase">L6M AOV</div>
                                                 <div className="text-lg font-mono font-semibold">¥{l6mAov.toLocaleString(undefined, {minimumFractionDigits: 0, maximumFractionDigits: 0})}</div>
                                             </div>
                                             <div className="bg-notion-gray_bg p-3 rounded border border-notion-border">
                                                 <div className="text-[10px] text-notion-muted uppercase">L6M Refund Rate</div>
                                                 <div className="text-lg font-mono font-semibold">{((enrichedProfile?.l6m_refund_rate || 0) * 100).toFixed(1)}%</div>
                                             </div>
                                         </div>
                                     </div>

                                     {/* Latest Purchase */}
                                     {(enrichedProfile as any)?.order_history && (enrichedProfile as any).order_history.length > 0 && (
                                        <div>
                                            <h4 className="text-xs font-bold text-notion-muted uppercase mb-3 border-b border-notion-border pb-1">Latest Purchase</h4>
                                            <div className="bg-gradient-to-r from-green-50 to-emerald-50 border border-green-100 p-4 rounded-sm">
                                                <div className="flex items-center justify-between mb-2">
                                                    <div>
                                                        <div className="text-2xl font-serif text-green-900 font-bold">
                                                            ¥{Number((enrichedProfile as any).order_history?.[0]?.gmv || 0).toLocaleString()}
                                                        </div>
                                                        <div className="text-xs text-green-800 flex items-center gap-2 mt-1">
                                                            <Calendar size={12} /> {(enrichedProfile as any).order_history?.[0]?.date || 'N/A'}
                                                        </div>
                                                    </div>
                                                    <div className="p-2 bg-white rounded-full text-green-600 shadow-sm border border-green-100">
                                                        <CheckCircle size={24} />
                                                    </div>
                                                </div>
                                                <div className="text-xs text-green-800">
                                                    Items: {(enrichedProfile as any).order_history[0].items.join(', ')}
                                                </div>
                                            </div>
                                        </div>
                                     )}

                                     {/* Category Preferences */}
                                     <div>
                                         <h4 className="text-xs font-bold text-notion-muted uppercase mb-3 border-b border-notion-border pb-1">Category Preferences (Top 3)</h4>
                                         <div className="space-y-2">
                                             {[
                                                 { rank: 1, name: (enrichedProfile as any)?.top_category || 'N/A', color: 'bg-orange-100 text-orange-800 border-orange-200' },
                                                 { rank: 2, name: (enrichedProfile as any)?.second_category || 'N/A', color: 'bg-blue-100 text-blue-800 border-blue-200' },
                                                 { rank: 3, name: (enrichedProfile as any)?.third_category || 'N/A', color: 'bg-green-100 text-green-800 border-green-200' }
                                             ].map((cat) => (
                                                 <div key={cat.rank} className="flex items-center gap-3">
                                                     <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${cat.color}`}>
                                                         {cat.rank}
                                                     </div>
                                                     <div className="flex-1">
                                                         <div className="text-sm font-medium text-notion-text">{cat.name}</div>
                                                     </div>
                                                 </div>
                                             ))}
                                         </div>
                                     </div>
                                 </div>
                             </NotionCard>

                             {/* Individual Intent Radar */}
                             <NotionCard icon={Target} title="Intent Distribution">
                                 <div className="h-64">
                                    <ResponsiveContainer width="100%" height="100%">
                                        <RadarChart cx="50%" cy="50%" outerRadius="70%" data={currentSession.profile.intent_scores}>
                                        <PolarGrid stroke="#E9E9E7" />
                                        <PolarAngleAxis dataKey="subject" tick={{ fill: '#37352F', fontSize: 10 }} />
                                        <PolarRadiusAxis angle={30} domain={[0, 150]} tick={false} axisLine={false} />
                                        <Radar name="Intents" dataKey="A" stroke="#F59E0B" fill="#F59E0B" fillOpacity={0.4} />
                                        <Tooltip contentStyle={{ backgroundColor: '#fff', borderColor: '#E9E9E7' }} />
                                        </RadarChart>
                                    </ResponsiveContainer>
                                 </div>
                                 <p className="text-xs text-notion-muted text-center mt-2">
                                     Dominant Intent: <span className="font-semibold text-notion-text">{currentSession.dominantIntent}</span>
                                 </p>
                             </NotionCard>
                         </div>
                     </div>
                 )}

                 {/* VIEW 2: PURCHASE HISTORY (MOVED UP) */}
                 {activeSubTab === 'orders' && (
                     <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
                         {(enrichedProfile?.order_history || []).length > 0 ? (
                             <>
                                {/* Latest Order Highlight */}
                                <div className="bg-gradient-to-r from-green-50 to-emerald-50 border border-green-100 p-5 rounded-sm shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
                                     <div className="flex items-start gap-4">
                                         <div className="p-3 bg-white rounded-full text-green-600 shadow-sm border border-green-100">
                                             <Truck size={24} />
                                         </div>
                                         <div>
                                             <h3 className="text-sm font-bold text-green-900 uppercase tracking-wide mb-1">Latest Purchase</h3>
                                             <div className="text-2xl font-serif text-green-900">
                                                 ¥{Number((enrichedProfile?.order_history || [])[0]?.gmv || 0).toLocaleString()}
                                             </div>
                                             <div className="text-xs text-green-800 mt-1 flex items-center gap-2">
                                                 <Calendar size={12} /> {(enrichedProfile?.order_history || [])[0]?.date || 'N/A'}
                                                 <span className="w-1 h-1 bg-green-400 rounded-full"></span>
                                                 <span>{(enrichedProfile?.order_history || [])[0]?.fp_md || 'FP'}</span>
                                             </div>
                                         </div>
                                     </div>
                                     <div className="flex-1 bg-white/60 p-3 rounded border border-green-100/50">
                                         <span className="text-[10px] text-green-800 font-bold uppercase block mb-1">Items in this order:</span>
                                         <ul className="list-disc list-inside text-sm text-green-900">
                                             {(enrichedProfile?.order_history || [])[0].items.map((item: string, idx: number) => (
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

const SettingsView: React.FC = () => (
  <div className="max-w-2xl mx-auto space-y-8">
      <div>
          <h2 className="text-2xl font-serif text-notion-text mb-4">Pipeline Configuration</h2>
          <div className="bg-notion-bg border border-notion-border rounded-sm p-6 shadow-sm">
            <div className="flex items-start gap-4">
                <div className="p-2 bg-green-50 rounded text-green-700">
                    <Terminal size={20} />
                </div>
                <div>
                    <h3 className="font-medium text-notion-text">ETL Script Status</h3>
                    <p className="text-sm text-notion-muted mt-1 leading-relaxed">
                        Playwright crawler active. Targeting Qianniu Workbench.<br/>
                        Next scheduled run: 02:00 AM CST.
                    </p>
                    <div className="mt-4 flex items-center gap-2 text-xs font-mono text-notion-muted bg-notion-sidebar p-2 rounded border border-notion-border">
                        <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
                        Connected to PostgreSQL DB
                    </div>
                </div>
            </div>
          </div>
      </div>

      <div>
          <h2 className="text-lg font-serif text-notion-text mb-3">Dictionary Management</h2>
          <textarea
            className="w-full h-40 bg-notion-bg border border-notion-border rounded-sm p-4 text-sm font-mono text-notion-text focus:outline-none focus:ring-1 focus:ring-gray-300"
            defaultValue={`# Keywords for NLP Tagging
glass, grinder, leak, broken, shipping
discount, wholesale, return, refund
flavor, taste, clean, resin
14mm, 18mm, bowl, stem`}
          />
      </div>
  </div>
);

// --- App Layout ---

export default function App() {
  const [activeTab, setActiveTab] = useState<'overview' | 'analysis' | 'settings'>('overview');
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  const NavTab = ({ id, icon: Icon, label }: { id: typeof activeTab, icon: any, label: string }) => (
    <button
      onClick={() => setActiveTab(id)}
      className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium transition-all duration-200 ${
        activeTab === id
          ? 'bg-notion-hover text-notion-text shadow-sm'
          : 'text-notion-muted hover:bg-notion-hover/50 hover:text-notion-text'
      }`}
    >
      <Icon size={16} />
      <span>{label}</span>
    </button>
  );

  return (
    <div className="flex flex-col h-screen bg-white text-notion-text font-sans overflow-hidden">
      {/* Top Navigation Bar */}
      <header className="h-14 border-b border-notion-border bg-white flex items-center justify-between px-4 lg:px-6 shrink-0 z-50">
        <div className="flex items-center gap-8">
           {/* Brand */}
           <div className="flex items-center gap-2 cursor-default">
             <div className="w-5 h-5 bg-orange-500 rounded flex items-center justify-center text-white text-xs font-bold font-serif">S</div>
             <span className="font-semibold text-sm tracking-tight">SmokeSignal</span>
           </div>

           {/* Desktop Nav */}
           <nav className="hidden md:flex items-center gap-1 bg-notion-gray_bg/50 p-1 rounded-lg border border-notion-border/50">
             <NavTab id="overview" icon={LayoutDashboard} label="Overview" />
             <NavTab id="analysis" icon={Database} label="Chat & CRM" />
             <NavTab id="settings" icon={Settings} label="Configuration" />
           </nav>
        </div>

        {/* Right Actions */}
        <div className="flex items-center gap-4">
           {/* User Profile */}
           <div className="flex items-center gap-2 cursor-pointer hover:bg-notion-hover p-1.5 rounded-md transition-colors">
              <div className="w-6 h-6 rounded bg-gradient-to-tr from-gray-200 to-gray-300 flex items-center justify-center text-xs font-medium text-gray-600">A</div>
              <span className="text-sm font-medium hidden sm:block">Admin</span>
           </div>
           
           {/* Mobile Menu Toggle */}
            <button 
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              className="md:hidden p-2 text-notion-muted hover:bg-notion-hover rounded-md"
            >
              {isMobileMenuOpen ? <X size={20} /> : <Menu size={20} />}
            </button>
        </div>
      </header>
      
      {/* Mobile Nav Dropdown */}
      {isMobileMenuOpen && (
        <div className="md:hidden border-b border-notion-border bg-white p-4 space-y-2 absolute top-14 left-0 right-0 z-40 shadow-lg animate-in slide-in-from-top-2">
            <button onClick={() => {setActiveTab('overview'); setIsMobileMenuOpen(false)}} className={`w-full text-left px-4 py-3 rounded-md text-sm font-medium ${activeTab === 'overview' ? 'bg-notion-hover' : ''}`}>Overview</button>
            <button onClick={() => {setActiveTab('analysis'); setIsMobileMenuOpen(false)}} className={`w-full text-left px-4 py-3 rounded-md text-sm font-medium ${activeTab === 'analysis' ? 'bg-notion-hover' : ''}`}>Chat & CRM</button>
            <button onClick={() => {setActiveTab('settings'); setIsMobileMenuOpen(false)}} className={`w-full text-left px-4 py-3 rounded-md text-sm font-medium ${activeTab === 'settings' ? 'bg-notion-hover' : ''}`}>Configuration</button>
        </div>
      )}

      {/* Main Content Area */}
      <main className="flex-1 overflow-hidden bg-white relative">
        <div className="h-full overflow-y-auto p-4 lg:p-6 scrollbar-thin scrollbar-thumb-gray-200 scrollbar-track-transparent">
          <div className="max-w-[1600px] mx-auto h-full flex flex-col">
            {activeTab === 'overview' && <DashboardOverview />}
            {activeTab === 'analysis' && <ChatAnalysis />}
            {activeTab === 'settings' && <SettingsView />}
          </div>
        </div>
      </main>
    </div>
  );
}