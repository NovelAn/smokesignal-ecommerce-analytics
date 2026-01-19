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
  BarChart as BarChartIcon
} from 'lucide-react';
import {
  KEYWORD_DATA,
  DAILY_STATS,
  INTENT_DISTRIBUTION,
  HOURLY_ACTIVITY,
  MOCK_SESSIONS,
  ACTIONABLE_CUSTOMERS
} from './constants';
import { BuyerSession, CustomerProfile, ChatMessage, OrderRecord } from './types';

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

const KeywordAnalysisPanel: React.FC = () => {
  const [timeRange, setTimeRange] = useState<'7d' | '15d' | '30d' | '90d' | '1y'>('1y');
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

  // Aggregation Logic (Simulated reactivity based on timeRange)
  // In a real app, this would filter data by date. Here we assume KEYWORD_DATA is the source.
  const { categoryData, keywordData, totalVolume } = useMemo(() => {
    // Group by Category
    const catMap: Record<string, { name: string; value: number; fill: string }> = {};
    const sortedKeywords = [...KEYWORD_DATA].sort((a, b) => b.value - a.value).slice(0, 8); // Top 8 keywords
    let total = 0;

    // 1. Scale Data based on Time Range
    let multiplier = 1;
    if (timeRange === '7d') multiplier = 0.1;
    if (timeRange === '15d') multiplier = 0.2;
    if (timeRange === '30d') multiplier = 0.35;
    if (timeRange === '90d') multiplier = 0.6;

    const scaledData = KEYWORD_DATA.map(item => ({
        ...item,
        value: Math.floor(item.value * multiplier)
    }));
    
    // Calculate Total
    total = scaledData.reduce((acc, curr) => acc + curr.value, 0);

    // 2. Prepare Category Data for Pie
    scaledData.forEach((item) => {
        if (!catMap[item.category]) {
            catMap[item.category] = { name: item.category, value: 0, fill: '' };
        }
        catMap[item.category].value += item.value;
    });

    const categoryDataList = Object.values(catMap).sort((a, b) => b.value - a.value);
    
    // Assign Cool Colors
    categoryDataList.forEach((cat, index) => {
        cat.fill = COOL_PALETTE[index % COOL_PALETTE.length];
    });

    // 3. Prepare Keyword Data for Bar (Filtered)
    let finalKeywords = scaledData;
    if (selectedCategory) {
        finalKeywords = scaledData.filter(k => k.category === selectedCategory);
    }
    
    // Sort and Top 10
    const keywordDataList = [...finalKeywords]
        .sort((a, b) => b.value - a.value)
        .slice(0, 10);

    return { categoryData: categoryDataList, keywordData: keywordDataList, totalVolume: total };
  }, [timeRange, selectedCategory]);

  return (
    <NotionCard 
        title="Keyword & Issue Analysis" 
        icon={Database} 
        className="h-[500px] flex flex-col"
        action={
            <div className="flex gap-2 items-center">
                {selectedCategory && (
                    <button 
                        onClick={() => setSelectedCategory(null)}
                        className="px-2 py-1 text-xs text-notion-muted hover:text-blue-600 border border-transparent hover:border-blue-200 rounded transition-colors flex items-center gap-1"
                    >
                        <XCircle size={12}/> Clear Filter: {selectedCategory}
                    </button>
                )}
                <div className="flex bg-notion-gray_bg p-0.5 rounded-md border border-notion-border">
                    {[
                        { id: '7d', label: '7 Days' },
                        { id: '15d', label: '15 Days' },
                        { id: '30d', label: '1 Mo' },
                        { id: '90d', label: '1 Qtr' },
                        { id: '1y', label: '1 Yr' }
                    ].map((range) => (
                        <button
                            key={range.id}
                            onClick={() => setTimeRange(range.id as any)}
                            className={`px-3 py-1 text-xs font-medium rounded-sm transition-all ${
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
        }
    >
        <div className="flex flex-col lg:flex-row h-full gap-8">
            {/* Left: Category Distribution (Donut) */}
            <div className="flex-1 flex flex-col">
                <div className="flex items-center justify-between mb-2">
                    <h4 className="text-xs font-bold text-notion-muted uppercase tracking-wider flex items-center gap-2">
                        <PieIcon size={12} /> Categories Distribution
                    </h4>
                    <span className="text-xs text-notion-muted italic">Click slices to filter</span>
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
                                label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
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
                        <span className="text-2xl font-bold text-notion-text">{categoryData.length}</span>
                        <span className="text-[10px] text-notion-muted uppercase tracking-wider">Types</span>
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
                                {keywordData.map((entry, index) => {
                                    // If a category is selected, use that color. If not, use the color of the category for that specific keyword.
                                    // Default to Primary Blue if not found
                                    const categoryColor = categoryData.find(c => c.name === entry.category)?.fill || '#3B82F6';
                                    return <Cell key={`cell-${index}`} fill={categoryColor} />;
                                })}
                                <LabelList dataKey="value" position="right" fontSize={11} fill="#666" />
                            </Bar>
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            </div>
        </div>
        
        {/* Insight Footer */}
        <div className="mt-4 pt-3 border-t border-notion-border flex items-start gap-3">
            <div className="p-1.5 bg-blue-50 rounded text-blue-600 shrink-0 mt-0.5">
                <Lightbulb size={14} />
            </div>
             <div className="text-xs text-notion-text">
                <span className="font-semibold text-blue-800">Top Insight:</span> 
                {' '}Pre-sale inquiries regarding <span className="font-medium bg-blue-100 text-blue-800 px-1 rounded">Specs</span> constitute {((categoryData.find(c => c.name === 'Specs')?.value || 0) / totalVolume * 100).toFixed(0)}% of traffic this period. 
                Users are specifically asking about "Dimensions" and "Materials". Consider adding a comparison table to the product detail page.
            </div>
        </div>
    </NotionCard>
  );
};

// --- Dashboard Sub-Components ---

const DashboardOverview: React.FC = () => {
  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      {/* Top Metrics - Minimalist */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: 'Total Conversations', value: '1,284', change: '+12%', icon: MessageSquare },
          { label: 'Avg Sentiment', value: '7.8', change: '+2.4%', icon: TrendingUp },
          { label: 'Urgent Issues', value: '14', change: '-5%', icon: AlertCircle },
          { label: 'Product Inquiries', value: '856', change: '+18%', icon: Package },
        ].map((stat, idx) => (
          <NotionCard key={idx} className="hover:bg-notion-hover transition-colors cursor-pointer">
            <div className="flex items-center justify-between mb-2">
              <span className="text-notion-muted text-sm flex items-center gap-2">
                 <stat.icon size={14} /> {stat.label}
              </span>
            </div>
            <div className="flex items-end gap-2">
               <h4 className="text-3xl font-serif text-notion-text">{stat.value}</h4>
               <span className={`text-xs font-medium mb-1 ${stat.change.startsWith('+') ? 'text-green-600' : 'text-red-600'}`}>
                {stat.change}
              </span>
            </div>
          </NotionCard>
        ))}
      </div>

      {/* Row 2: Keyword Analysis (New Module) */}
      <KeywordAnalysisPanel />

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
        <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
                <thead>
                    <tr className="border-b border-notion-border text-notion-muted text-xs uppercase bg-notion-gray_bg/30">
                        <th className="py-2.5 px-4 font-semibold">User</th>
                        <th className="py-2.5 px-4 font-semibold">Issue Type</th>
                        <th className="py-2.5 px-4 font-semibold">Priority</th>
                        <th className="py-2.5 px-4 font-semibold">Last Active</th>
                        <th className="py-2.5 px-4 font-semibold">Suggested Action</th>
                        <th className="py-2.5 px-4 font-semibold text-right">Action</th>
                    </tr>
                </thead>
                <tbody className="divide-y divide-notion-border">
                    {ACTIONABLE_CUSTOMERS.map((cust) => (
                        <tr key={cust.id} className="hover:bg-notion-hover transition-colors">
                            <td className="py-3 px-4 font-medium text-notion-text">{cust.user_nick}</td>
                            <td className="py-3 px-4">
                                <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium border ${
                                    cust.issue_type === 'Churn Risk' ? 'bg-red-50 text-red-700 border-red-100' :
                                    cust.issue_type === 'Negative Review' ? 'bg-orange-50 text-orange-700 border-orange-100' :
                                    cust.issue_type === 'Stockout Request' ? 'bg-yellow-50 text-yellow-700 border-yellow-100' :
                                    'bg-blue-50 text-blue-700 border-blue-100'
                                }`}>
                                    {cust.issue_type}
                                </span>
                            </td>
                            <td className="py-3 px-4">
                                <span className={`text-xs font-bold ${
                                    cust.priority === 'High' ? 'text-red-600' : 
                                    cust.priority === 'Medium' ? 'text-yellow-600' : 'text-green-600'
                                }`}>
                                    {cust.priority}
                                </span>
                            </td>
                            <td className="py-3 px-4 text-notion-muted text-xs">{cust.last_active}</td>
                            <td className="py-3 px-4 text-xs italic text-gray-600">{cust.action_suggestion}</td>
                            <td className="py-3 px-4 text-right">
                                <button className="text-blue-600 hover:text-blue-800 text-xs font-semibold underline">
                                    Handle
                                </button>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
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
  
  // Track open states for chat dates. Default empty.
  const [openDates, setOpenDates] = useState<Record<string, boolean>>({});

  // Filter based on user_nick only as requested for precise lookup
  const filteredSessions = useMemo(() => {
    if (!searchTerm) return MOCK_SESSIONS;
    return MOCK_SESSIONS.filter(s =>
      s.user_nick.toLowerCase().includes(searchTerm.toLowerCase())
    );
  }, [searchTerm]);

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

  const currentSession = selectedSession || filteredSessions[0];

  // Calculations for Metrics
  const historicalAov = currentSession?.profile.total_orders > 0 
    ? currentSession.profile.historical_ltv / currentSession.profile.total_orders 
    : 0;
  
  const l6mAov = currentSession?.profile.l6m_frequency > 0
    ? currentSession.profile.l6m_spend / currentSession.profile.l6m_frequency
    : 0;

  // Group messages by date
  const groupedMessages = useMemo<Record<string, ChatMessage[]>>(() => {
     if (!currentSession) return {};
     const groups: Record<string, ChatMessage[]> = {};
     currentSession.messages.forEach(msg => {
         const date = msg.msg_time.split(' ')[0];
         if (!groups[date]) groups[date] = [];
         groups[date].push(msg);
     });
     return groups;
  }, [currentSession]);

  const toggleDate = (date: string) => {
     setOpenDates(prev => ({ ...prev, [date]: !prev[date] }));
  };
  
  if (!currentSession) return <div className="p-8 text-center text-notion-muted">No data found.</div>;

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
                 {filteredSessions.map((session, idx) => (
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
                             <span className="text-[10px] text-notion-muted group-hover:text-notion-text">{session.messages[session.messages.length-1]?.msg_time.split(' ')[0]}</span>
                        </div>
                    </div>
                 ))}
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
                            {currentSession.profile.user_nick.slice(0, 2)}
                         </div>
                         <div>
                             <h2 className="text-xl font-bold text-notion-text flex items-center gap-3">
                                {currentSession.profile.user_nick}
                                {currentSession.profile.is_new_customer ? (
                                    <span className="text-xs bg-green-100 text-green-700 border border-green-200 px-2 py-0.5 rounded font-medium shadow-sm">New</span>
                                ) : (
                                    <span className="text-xs bg-blue-100 text-blue-700 border border-blue-200 px-2 py-0.5 rounded font-medium shadow-sm">Existing</span>
                                )}
                             </h2>
                             <div className="flex items-center gap-3 text-xs text-notion-muted mt-0.5">
                                <span className="flex items-center gap-1"><MapPin size={12} /> {currentSession.profile.city}</span>
                                <span className="w-1 h-1 bg-gray-300 rounded-full"></span>
                                <span className="flex items-center gap-1"><Activity size={12} /> LTV: ¥{currentSession.profile.historical_ltv.toLocaleString()}</span>
                             </div>
                         </div>
                     </div>
                     <div className="flex gap-2">
                         {currentSession.profile.tags.map(t => <NotionTag key={t} text={t} color="orange" />)}
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
                 
                 {/* VIEW 1: 360 PROFILE & INSIGHTS */}
                 {activeSubTab === 'profile' && (
                     <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
                         {/* AI Summary Section */}
                         <NotionCard icon={Sparkles} title="AI Persona Analysis">
                             <div className="flex flex-col gap-4">
                                <div className="bg-purple-50 p-4 rounded border border-purple-100 text-sm text-notion-text leading-relaxed italic">
                                     "{currentSession.profile.analysis.summary}"
                                </div>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                    <div>
                                        <span className="text-xs font-bold text-notion-muted uppercase tracking-wider block mb-2">Key Interests</span>
                                        <div className="flex flex-wrap gap-2">
                                            {currentSession.profile.analysis.key_interests.map((tag, i) => (
                                            <span key={i} className="px-2.5 py-1 bg-blue-50 text-blue-700 border border-blue-100 rounded text-xs font-medium">
                                                {tag}
                                            </span>
                                            ))}
                                        </div>
                                    </div>
                                    <div>
                                        <span className="text-xs font-bold text-notion-muted uppercase tracking-wider block mb-2">Pain Points</span>
                                        <div className="flex flex-wrap gap-2">
                                            {currentSession.profile.analysis.pain_points.map((tag, i) => (
                                            <span key={i} className="px-2.5 py-1 bg-red-50 text-red-700 border border-red-100 rounded text-xs font-medium">
                                                {tag}
                                            </span>
                                            ))}
                                        </div>
                                    </div>
                                </div>
                                <div className="flex gap-3 bg-yellow-50 p-3 rounded border border-yellow-100 items-start mt-2">
                                     <Zap size={18} className="text-yellow-600 shrink-0 mt-0.5"/>
                                     <div className="flex flex-col gap-1">
                                         <span className="text-xs font-bold text-yellow-800 uppercase">Recommended Action</span>
                                         <span className="text-sm text-yellow-900 leading-snug">
                                             {currentSession.profile.analysis.recommended_action}
                                         </span>
                                     </div>
                                </div>
                             </div>
                         </NotionCard>

                         <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
                             {/* Financial Metrics */}
                             <NotionCard icon={Activity} title="Financial Performance">
                                 <div className="space-y-6">
                                     {/* LTV & Orders */}
                                     <div className="grid grid-cols-3 gap-4">
                                         <div className="bg-notion-gray_bg p-3 rounded border border-notion-border">
                                             <div className="text-[10px] text-notion-muted uppercase">Lifetime Value</div>
                                             <div className="text-lg font-mono font-semibold">¥{currentSession.profile.historical_ltv.toLocaleString()}</div>
                                         </div>
                                         <div className="bg-notion-gray_bg p-3 rounded border border-notion-border">
                                             <div className="text-[10px] text-notion-muted uppercase">Total Orders</div>
                                             <div className="text-lg font-mono font-semibold">{currentSession.profile.total_orders}</div>
                                         </div>
                                         <div className="bg-notion-gray_bg p-3 rounded border border-notion-border">
                                             <div className="text-[10px] text-notion-muted uppercase">Avg Order Value</div>
                                             <div className="text-lg font-mono font-semibold">¥{Math.round(historicalAov).toLocaleString()}</div>
                                         </div>
                                     </div>
                                     
                                     {/* L6M */}
                                     <div>
                                         <h4 className="text-xs font-bold text-notion-muted uppercase mb-3 border-b border-notion-border pb-1">Last 6 Months Activity</h4>
                                         <div className="flex justify-between items-center text-sm mb-1">
                                             <span className="text-notion-text">Spend:</span>
                                             <span className="font-mono">¥{currentSession.profile.l6m_spend.toLocaleString()}</span>
                                         </div>
                                         <div className="flex justify-between items-center text-sm">
                                             <span className="text-notion-text">Frequency:</span>
                                             <span className="font-mono">{currentSession.profile.l6m_frequency} orders</span>
                                         </div>
                                     </div>

                                     {/* Discount Sensitivity */}
                                     <div>
                                        <div className="flex justify-between items-end mb-1">
                                            <span className="text-[10px] font-bold text-notion-muted uppercase tracking-wider flex items-center gap-1">
                                                <Percent size={10}/> Discount Sensitivity
                                            </span>
                                            <span className={`font-mono font-bold text-xs ${currentSession.profile.discount_ratio > 50 ? 'text-red-600' : 'text-green-600'}`}>
                                                {currentSession.profile.discount_ratio}%
                                            </span>
                                        </div>
                                        <div className="w-full bg-gray-100 rounded-full h-1.5 overflow-hidden border border-notion-border">
                                            <div 
                                                className={`h-full rounded-full transition-all duration-500 ${currentSession.profile.discount_ratio > 50 ? 'bg-red-400' : 'bg-green-400'}`} 
                                                style={{ width: `${currentSession.profile.discount_ratio}%` }}
                                            ></div>
                                        </div>
                                        <p className="text-[10px] text-notion-muted mt-1.5 leading-tight">
                                            {currentSession.profile.discount_ratio > 50 
                                            ? "High sensitivity. Responds well to coupons and sales events." 
                                            : "Low sensitivity. Prioritizes quality/speed over price."}
                                        </p>
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
                         {currentSession.profile.order_history.length > 0 ? (
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
                                                 ¥{currentSession.profile.order_history[0].amount.toLocaleString()}
                                             </div>
                                             <div className="text-xs text-green-800 mt-1 flex items-center gap-2">
                                                 <Calendar size={12} /> {currentSession.profile.order_history[0].date}
                                                 <span className="w-1 h-1 bg-green-400 rounded-full"></span>
                                                 <span>{currentSession.profile.order_history[0].status}</span>
                                             </div>
                                         </div>
                                     </div>
                                     <div className="flex-1 bg-white/60 p-3 rounded border border-green-100/50">
                                         <span className="text-[10px] text-green-800 font-bold uppercase block mb-1">Items in this order:</span>
                                         <ul className="list-disc list-inside text-sm text-green-900">
                                             {currentSession.profile.order_history[0].items.map((item: string, idx: number) => (
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
                                                     <th className="py-2 px-3 font-semibold">Items</th>
                                                     <th className="py-2 px-3 font-semibold">Amount</th>
                                                     <th className="py-2 px-3 font-semibold">Status</th>
                                                 </tr>
                                             </thead>
                                             <tbody className="divide-y divide-notion-border">
                                                 {currentSession.profile.order_history.map((order: OrderRecord) => (
                                                     <tr key={order.order_id} className="hover:bg-notion-hover transition-colors">
                                                         <td className="py-3 px-3 font-mono text-xs">{order.date}</td>
                                                         <td className="py-3 px-3 font-mono text-xs text-notion-muted">{order.order_id}</td>
                                                         <td className="py-3 px-3">
                                                             <div className="flex flex-col gap-0.5">
                                                                 {(order.items as string[]).map((item: string, i: number) => (
                                                                     <span key={i} className="text-xs">{item}</span>
                                                                 ))}
                                                             </div>
                                                         </td>
                                                         <td className="py-3 px-3 font-semibold">¥{order.amount.toLocaleString()}</td>
                                                         <td className="py-3 px-3">
                                                             <span className={`text-[10px] px-2 py-0.5 rounded-full border ${
                                                                 order.status === 'Completed' ? 'bg-green-50 text-green-700 border-green-100' :
                                                                 order.status === 'Shipped' ? 'bg-blue-50 text-blue-700 border-blue-100' :
                                                                 'bg-gray-100 text-gray-700 border-gray-200'
                                                             }`}>
                                                                 {order.status}
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
                         <div className="grid grid-cols-3 gap-4 bg-white border border-notion-border p-3 rounded-sm shadow-sm flex-none">
                             <div className="flex flex-col items-center justify-center border-r border-notion-border">
                                 <div className="text-[10px] text-notion-muted uppercase font-bold tracking-wider mb-1">Recent Freq (30d)</div>
                                 <div className="text-lg font-mono text-notion-text">{currentSession.profile.recent_chat_frequency} msgs</div>
                             </div>
                             <div className="flex flex-col items-center justify-center border-r border-notion-border">
                                 <div className="text-[10px] text-notion-muted uppercase font-bold tracking-wider mb-1">Avg Interval</div>
                                 <div className="text-lg font-mono text-notion-text">{currentSession.profile.avg_reply_interval_days} days</div>
                             </div>
                             <div className="flex flex-col items-center justify-center">
                                 <div className="text-[10px] text-notion-muted uppercase font-bold tracking-wider mb-1">Last Contact</div>
                                 <div className="text-lg font-mono text-notion-text">{currentSession.profile.last_interaction_date}</div>
                             </div>
                         </div>

                         {/* Chat Log */}
                         <div className="flex-1 bg-notion-sidebar border border-notion-border rounded-sm flex flex-col overflow-hidden shadow-inner relative">
                            <div className="flex-1 overflow-y-auto p-4 scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-transparent space-y-6 bg-white">
                                {Object.entries(groupedMessages).map(([date, msgs]: [string, ChatMessage[]], grpIdx) => (
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
                                                                <p className="leading-relaxed whitespace-pre-wrap mt-1">{msg.content}</p>
                                                            </div>
                                                        </div>
                                                    )
                                                })}
                                            </div>
                                        )}
                                    </div>
                                ))}
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