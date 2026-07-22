import { useState } from 'react';
import { BrainCircuit, ClipboardCheck, TrendingUp } from 'lucide-react';

import { IssueTrendsPanel } from '../components/ai-analysis-v2/IssueTrendsPanel';
import { ReviewWorkbench } from '../components/ai-analysis-v2/ReviewWorkbench';


export default function AIAnalysisV2View() {
  const [activeTab, setActiveTab] = useState<'trends' | 'reviews'>('trends');

  return (
    <div className="flex h-full flex-col gap-4 bg-slate-50 text-slate-900">
      <header className="rounded border border-slate-200 bg-white px-5 py-4">
        <div className="flex items-start gap-3">
          <span className="rounded border border-orange-200 bg-orange-50 p-2 text-orange-900"><BrainCircuit size={20} /></span>
          <div>
            <h1 className="text-lg font-semibold text-slate-900">AI 问题洞察</h1>
            <p className="mt-1 text-sm text-slate-600">把客户优先级与共性产品、服务问题分开查看。</p>
          </div>
        </div>
        <div className="mt-4 flex gap-1 border-b border-slate-200" role="tablist" aria-label="AI 问题洞察视图">
          <TabButton active={activeTab === 'trends'} onClick={() => setActiveTab('trends')} icon={TrendingUp}>问题趋势</TabButton>
          <TabButton active={activeTab === 'reviews'} onClick={() => setActiveTab('reviews')} icon={ClipboardCheck}>人工审核</TabButton>
        </div>
      </header>
      <div className="min-h-0 flex-1 overflow-y-auto pb-4">
        {activeTab === 'trends' ? <IssueTrendsPanel /> : <ReviewWorkbench />}
      </div>
    </div>
  );
}


function TabButton({ active, onClick, icon: Icon, children }: { active: boolean; onClick: () => void; icon: typeof TrendingUp; children: string }) {
  return (
    <button
      type="button"
      role="tab"
      aria-selected={active}
      onClick={onClick}
      className={`flex items-center gap-2 border-b-2 px-4 py-2.5 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-orange-500 ${active ? 'border-orange-500 text-slate-900' : 'border-transparent text-slate-600 hover:text-slate-900'}`}
    >
      <Icon size={15} />
      {children}
    </button>
  );
}
