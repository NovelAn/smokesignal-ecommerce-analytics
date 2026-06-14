import { useEffect, useState } from 'react';
import { Activity, ClipboardCheck } from 'lucide-react';
import { apiClient, type DashboardMetrics } from '../api/client';
import { useDataFetchingWithRetry } from '../hooks/useDataFetching';
import { TimeRangeFilter } from '../components/common/TimeRangeFilter';
import { MetricCards } from '../components/dashboard/MetricCards';
import { KeywordAnalysisPanel } from '../components/dashboard/KeywordAnalysisPanel';
import { PriorityAttentionBoard } from '../components/dashboard/PriorityAttentionBoard';
import { VicPersonaCard } from '../components/dashboard/VicPersonaCard';
import { PeriodComparisonCard } from '../components/dashboard/PeriodComparisonCard';
import { CustomerTrendsGrid } from '../components/dashboard/CustomerTrendsGrid';
import { InventoryInquiriesCard } from '../components/dashboard/InventoryInquiriesCard';
import { fetchInventoryInquiries } from '../api/insights';

type OverviewTab = 'trends' | 'actions';

interface DashboardOverviewProps {
  onOpenBuyerInCrm?: (buyerNick: string, currentPage: number) => void;
  lastClickedBuyerNick?: string | null;
  lastClickedPage?: number;
  onClearClickedHighlight?: () => void;
  highlightTrigger?: number;
  appActiveTab?: string;
}

export function DashboardOverview({
  onOpenBuyerInCrm,
  lastClickedBuyerNick = null,
  lastClickedPage = 1,
  onClearClickedHighlight,
  highlightTrigger = 0,
  appActiveTab,
}: DashboardOverviewProps) {
  const [activeTab, setActiveTab] = useState<OverviewTab>('trends');
  const { data: metrics, isLoading, error } = useDataFetchingWithRetry<DashboardMetrics>(
    () => apiClient.getDashboardMetrics(),
    2,
  );

  useEffect(() => {
    void fetchInventoryInquiries();
  }, []);

  const openBuyer = (buyerNick: string, page = 1) => onOpenBuyerInCrm?.(buyerNick, page);

  return (
    <div className="space-y-5 animate-in fade-in duration-500">
      <TimeRangeFilter />

      <MetricCards
        metrics={metrics!}
        isLoading={isLoading}
        error={error}
        onRetry={() => window.location.reload()}
      />

      <KeywordAnalysisPanel />

      <section className="rounded-sm border border-notion-border bg-white shadow-sm">
        <div className="flex items-center gap-1 border-b border-notion-border bg-notion-gray_bg/30 px-2 pt-2" role="tablist" aria-label="Overview sections">
          <TabButton active={activeTab === 'trends'} onClick={() => setActiveTab('trends')} icon={<Activity size={15} />}>
            趋势概览
          </TabButton>
          <TabButton active={activeTab === 'actions'} onClick={() => setActiveTab('actions')} icon={<ClipboardCheck size={15} />}>
            行动看板
          </TabButton>
        </div>

        <div className="p-4 lg:p-5">
          {activeTab === 'trends' ? (
            <div className="space-y-5" role="tabpanel">
              <VicPersonaCard />
              <PeriodComparisonCard />
              <CustomerTrendsGrid />
            </div>
          ) : (
            <div className="space-y-5" role="tabpanel">
              <InventoryInquiriesCard onOpenBuyer={openBuyer} />
              <PriorityAttentionBoard
                onRowAction={(buyer, actionType, currentPage) => {
                  if (actionType === 'view_details' && buyer?.buyer_nick) openBuyer(buyer.buyer_nick, currentPage ?? 1);
                }}
                highlightBuyerNick={lastClickedBuyerNick}
                highlightBuyerPage={lastClickedPage}
                onClearClickedHighlight={onClearClickedHighlight}
                highlightTrigger={highlightTrigger}
                appActiveTab={appActiveTab}
              />
            </div>
          )}
        </div>
      </section>
    </div>
  );
}

function TabButton({ active, onClick, icon, children }: { active: boolean; onClick: () => void; icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <button
      type="button"
      role="tab"
      aria-selected={active}
      onClick={onClick}
      className={`inline-flex items-center gap-2 rounded-t px-4 py-2.5 text-sm font-medium transition-colors ${
        active
          ? 'border border-b-white border-notion-border bg-white text-notion-text -mb-px'
          : 'border border-transparent text-notion-muted hover:bg-white/60 hover:text-notion-text'
      }`}
    >
      {icon}{children}
    </button>
  );
}
