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
import { DashboardOverview } from './views/DashboardOverview';
import ChatAnalysis from './views/ChatAnalysis';
import ExternalInfoConfig from './views/ExternalInfoConfig';
import SettingsView from './views/SettingsView';
import { NotionCard } from './components/common/NotionCard';
import { NotionTag } from './components/common/NotionTag';

// --- Notion Style Components (moved to components/common/) ---

// --- Chat Analysis with CRM Features (moved to views/ChatAnalysis.tsx) ---

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

// --- App Layout ---

export default function App() {
  const [activeTab, setActiveTab] = useState<'overview' | 'analysis' | 'external' | 'settings'>('overview');
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
             <NavTab id="external" icon={Database} label="External Info" />
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
            <button onClick={() => {setActiveTab('external'); setIsMobileMenuOpen(false)}} className={`w-full text-left px-4 py-3 rounded-md text-sm font-medium ${activeTab === 'external' ? 'bg-notion-hover' : ''}`}>External Info</button>
            <button onClick={() => {setActiveTab('settings'); setIsMobileMenuOpen(false)}} className={`w-full text-left px-4 py-3 rounded-md text-sm font-medium ${activeTab === 'settings' ? 'bg-notion-hover' : ''}`}>Configuration</button>
        </div>
      )}

      {/* Main Content Area */}
      <main className="flex-1 overflow-hidden bg-white relative">
        <div className="h-full overflow-y-auto p-4 lg:p-6 scrollbar-thin scrollbar-thumb-gray-200 scrollbar-track-transparent">
          <div className="max-w-[1600px] mx-auto h-full flex flex-col">
            {activeTab === 'overview' && <DashboardOverview />}
            {activeTab === 'analysis' && <ChatAnalysis />}
            {activeTab === 'external' && <ExternalInfoConfig />}
            {activeTab === 'settings' && <SettingsView />}
          </div>
        </div>
      </main>
    </div>
  );
}