import { AlertTriangle, BrainCircuit, RefreshCw } from 'lucide-react';

import { EmptyState } from '../common/ErrorAlert';
import { LoadingSpinner } from '../common/LoadingState';
import { NotionCard } from '../common/NotionCard';
import type {
  AttentionPriority,
  IssueSeverity,
  V2BuyerAnalysis,
  V2Sentiment,
} from '../../types/aiAnalysisV2';


interface Props {
  analysis: V2BuyerAnalysis | null;
  loading: boolean;
  error: string | null;
  onAnalyze: (mode: 'full' | 'incremental') => void;
}

const sentimentStyle: Record<V2Sentiment, string> = {
  Positive: 'border-emerald-300 bg-emerald-50 text-emerald-900',
  Neutral: 'border-slate-300 bg-slate-50 text-slate-800',
  Negative: 'border-red-300 bg-red-50 text-red-900',
  Unknown: 'border-gray-300 bg-gray-50 text-gray-700',
};

const priorityStyle: Record<AttentionPriority, string> = {
  urgent: 'border-red-400 bg-red-100 text-red-950',
  high: 'border-orange-300 bg-orange-50 text-orange-950',
  medium: 'border-amber-300 bg-amber-50 text-amber-950',
  low: 'border-slate-300 bg-slate-50 text-slate-800',
};

const severityRail: Record<IssueSeverity, string> = {
  critical: 'border-l-red-600',
  high: 'border-l-orange-500',
  medium: 'border-l-amber-400',
  low: 'border-l-slate-300',
};

export function CustomerV2StateCard({ analysis, loading, error, onAnalyze }: Props) {
  const state = analysis?.customer_state;
  const unresolved = analysis?.issues.filter(issue => issue.status !== 'resolved') ?? [];

  const action = (
    <button
      type="button"
      disabled={loading}
      onClick={() => onAnalyze(state ? 'incremental' : 'full')}
      className="inline-flex items-center gap-1.5 rounded border border-orange-300 bg-orange-50 px-2.5 py-1.5 text-xs font-semibold text-orange-900 transition-colors hover:bg-orange-100 focus:outline-none focus:ring-2 focus:ring-orange-500 focus:ring-offset-1 disabled:cursor-wait disabled:opacity-60"
    >
      <RefreshCw size={12} className={loading ? 'animate-spin' : ''} />
      {state ? '分析新对话' : '生成分析'}
    </button>
  );

  return (
    <NotionCard icon={BrainCircuit} title="Customer signals" subtitle="情感、问题与处理状态" action={state ? action : undefined}>
      {loading && !state ? (
        <div className="py-8">
          <LoadingSpinner size={24} text="正在分析对话中的事件和问题..." />
        </div>
      ) : !state ? (
        <EmptyState
          icon={BrainCircuit}
          title="尚未生成客户信号"
          description={error || '从最近 50 条对话开始，识别情感、具体问题和处理结果。'}
          action={action}
        />
      ) : (
        <div className="space-y-4 text-notion-text">
          {error && (
            <div className="flex items-start gap-2 rounded border border-red-300 bg-red-50 px-3 py-2 text-xs text-red-900" role="alert">
              <AlertTriangle size={14} className="mt-0.5 shrink-0" />
              <span>{error}。上一次成功结果仍保留，可再次重试。</span>
            </div>
          )}

          <div className="flex flex-wrap items-center gap-2">
            <span className={`rounded border px-2 py-1 text-xs font-semibold ${sentimentStyle[state.current_sentiment_label]}`}>
              {state.current_sentiment_label}
            </span>
            <span className={`rounded border px-2 py-1 text-xs font-semibold uppercase ${priorityStyle[state.attention_priority]}`}>
              {state.attention_priority} priority
            </span>
            <span className="text-xs text-notion-muted">{state.active_issue_count} 个未解决问题</span>
          </div>

          <div className="border-l-2 border-orange-400 pl-3">
            <p className="text-[11px] font-bold uppercase tracking-wider text-notion-muted">当前最需要处理</p>
            <p className="mt-1 text-sm font-semibold text-notion-text">{state.primary_issue_detail || '暂无主要问题'}</p>
            <p className="mt-1 text-xs leading-relaxed text-notion-muted">{state.recommended_action || '暂无后续动作'}</p>
          </div>

          <div>
            <p className="mb-2 text-[11px] font-bold uppercase tracking-wider text-notion-muted">未解决问题</p>
            {unresolved.length ? (
              <ul className="space-y-2">
                {unresolved.map(issue => (
                  <li key={issue.id} className={`border border-l-4 border-notion-border bg-white p-3 ${severityRail[issue.severity]}`}>
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <strong className="text-sm text-notion-text">{issue.issue_detail}</strong>
                      <span className="rounded bg-notion-gray_bg px-1.5 py-0.5 text-[10px] font-semibold text-gray-700">{issue.status}</span>
                    </div>
                    <p className="mt-1 text-xs text-notion-muted">{issue.issue_category} · {issue.issue_code} · {issue.severity}</p>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="rounded border border-dashed border-notion-border bg-notion-gray_bg/30 px-3 py-2 text-xs text-notion-muted">当前没有未解决问题。</p>
            )}
          </div>

          <details className="rounded border border-notion-border bg-white text-sm text-notion-text">
            <summary className="cursor-pointer px-3 py-2 font-medium focus:outline-none focus:ring-2 focus:ring-orange-500">
              历史事件（{analysis.events.length}）
            </summary>
            <ol className="divide-y divide-notion-border border-t border-notion-border">
              {analysis.events.map(event => (
                <li key={event.id} className="px-3 py-2.5">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="font-medium text-notion-text">{event.topic_summary}</span>
                    <span className="text-[11px] text-notion-muted">{event.resolution_status}</span>
                  </div>
                  <p className="mt-1 text-xs text-notion-muted">{new Date(event.event_ended_at).toLocaleString('zh-CN')}</p>
                </li>
              ))}
            </ol>
          </details>
        </div>
      )}
    </NotionCard>
  );
}
