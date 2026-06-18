import { useEffect, useState } from 'react';
import { ArrowRight, Boxes, MessageSquareText } from 'lucide-react';
import { fetchInventoryInquiries } from '../../api/insights';
import { apiClient, type ServiceStatus } from '../../api/client';
import type { InventoryInquiries, InventoryInquiry } from '../../types/insights';
import { ErrorAlert } from '../common/ErrorAlert';
import { LoadingSpinner } from '../common/LoadingState';
import { StatusButtonGroup } from '../common/StatusButtonGroup';

const SOURCE_LABELS = {
  ai: { label: 'AI 识别', className: 'border-blue-200 bg-blue-50 text-blue-700' },
  keyword: { label: '关键词', className: 'border-amber-200 bg-amber-50 text-amber-700' },
  both: { label: 'AI + 关键词', className: 'border-emerald-200 bg-emerald-50 text-emerald-700' },
};

interface InventoryInquiriesCardProps {
  onOpenBuyer?: (buyerNick: string) => void;
}

export function InventoryInquiriesCard({ onOpenBuyer }: InventoryInquiriesCardProps) {
  const [data, setData] = useState<InventoryInquiries | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    fetchInventoryInquiries(controller.signal)
      .then(setData)
      .catch((requestError) => {
        if (requestError?.name !== 'AbortError') {
          setError(requestError instanceof Error ? requestError.message : '库存需求加载失败');
        }
      })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, []);

  return (
    <section className="overflow-hidden rounded-sm border border-notion-border bg-white shadow-sm">
      <header className="flex flex-col gap-2 border-b border-notion-border bg-amber-50/50 px-5 py-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <div className="mb-1 flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.14em] text-amber-700"><Boxes size={14} /> Demand radar</div>
          <h2 className="text-lg font-semibold text-notion-text">库存需求</h2>
        </div>
        {data && <span className="text-sm text-notion-muted"><strong className="font-serif text-2xl text-amber-800">{data.total_count}</strong> 位客户正在询问</span>}
      </header>

      <div className="p-5">
        {loading && <LoadingSpinner />}
        {error && <ErrorAlert message={error} />}
        {!loading && !error && data?.inquiries.length === 0 && (
          <div className="rounded border border-dashed border-notion-border py-10 text-center text-sm text-notion-muted">暂无库存需求</div>
        )}
        {!loading && !error && data && data.inquiries.length > 0 && (
          <div className="grid max-h-[680px] gap-3 overflow-y-auto pr-1 lg:grid-cols-2" data-testid="inventory-inquiry-list">
            {data.inquiries.map((inquiry) => (
              <InquiryCard key={inquiry.buyer_nick} inquiry={inquiry} onOpenBuyer={onOpenBuyer} />
            ))}
          </div>
        )}
      </div>
    </section>
  );
}

function InquiryCard({ inquiry, onOpenBuyer }: { inquiry: InventoryInquiry; onOpenBuyer?: (buyerNick: string) => void }) {
  const source = SOURCE_LABELS[inquiry.detected_by] ?? SOURCE_LABELS.keyword;
  const [serviceStatus, setServiceStatus] = useState<ServiceStatus>(inquiry.service_status || 'pending');
  const [saving, setSaving] = useState(false);

  const updateStatus = async (newStatus: ServiceStatus) => {
    setSaving(true);
    try {
      await apiClient.markService({
        buyer_nick: inquiry.buyer_nick,
        status: newStatus,
        workstream: 'inventory',
      });
      setServiceStatus(newStatus);
    } finally {
      setSaving(false);
    }
  };
  return (
    <article className="rounded-sm border border-notion-border bg-notion-gray_bg/20 p-4 transition-colors hover:bg-notion-hover/40">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="font-medium text-notion-text">{inquiry.buyer_nick}</h3>
            <span className="rounded bg-purple-50 px-2 py-0.5 text-[10px] font-semibold text-purple-700">{inquiry.vip_level}</span>
            <span className={`rounded border px-2 py-0.5 text-[10px] font-semibold ${source.className}`}>{source.label}</span>
          </div>
          <p className="mt-1 text-xs text-notion-muted">共 {inquiry.question_count} 次库存提问 · 最近 {formatDate(inquiry.last_inventory_msg_time)}</p>
        </div>
        <button type="button" onClick={() => onOpenBuyer?.(inquiry.buyer_nick)} className="inline-flex shrink-0 items-center gap-1 text-xs font-medium text-blue-700 hover:underline">查看 <ArrowRight size={12} /></button>
      </div>

      <div className="mt-3 space-y-2">
        {inquiry.inventory_questions.length > 0 ? inquiry.inventory_questions.map((question, index) => (
          <blockquote key={`${inquiry.buyer_nick}-${index}`} className="flex gap-2 rounded border-l-2 border-amber-400 bg-white px-3 py-2 text-xs leading-relaxed text-notion-text">
            <MessageSquareText size={13} className="mt-0.5 shrink-0 text-amber-700" />
            <span>{question}</span>
          </blockquote>
        )) : <p className="text-xs text-notion-muted">暂无可展示的提问原文</p>}
      </div>

      <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 border-t border-notion-border pt-2 text-[10px] text-notion-muted">
        <span>主意图：{inquiry.dominant_intent || 'Unknown'}</span>
        <span>情感：{inquiry.sentiment_label}</span>
        <span>最近聊天：{formatDate(inquiry.last_chat_date)}</span>
      </div>
      <div className="mt-3 flex flex-wrap items-center justify-between gap-2 border-t border-notion-border pt-3">
        <span className="text-[10px] text-notion-muted">库存跟进状态{saving ? ' · 保存中' : ''}</span>
        <StatusButtonGroup buyer={{ service_status: serviceStatus }} onChange={updateStatus} />
      </div>
    </article>
  );
}

function formatDate(value: string | null) {
  return value ? value.slice(0, 10) : '—';
}
