import { useEffect, useMemo, useState } from 'react';

import { apiClient } from '../../api/client';
import type { V2ReviewItem, V2Sentiment } from '../../types/aiAnalysisV2';

const ISSUE_TAXONOMY: Record<string, string[]> = {
  product: ['material_expectation', 'color_appearance_mismatch', 'size_fit', 'quality_damage', 'packaging'],
  logistics: ['shipping_delay', 'delivery_failure', 'return_pickup', 'address_contact'],
  after_sales: ['return_request', 'exchange_request', 'refund_delay', 'repair_warranty'],
  pricing_promotion: ['price_change', 'discount_eligibility', 'price_difference'],
  inventory: ['out_of_stock', 'replenishment_wait'],
  service: ['response_slow', 'explanation_unclear', 'repeated_communication', 'service_attitude'],
  trust: ['authenticity_concern', 'advertising_mismatch'],
  usage_care: ['usage_instruction', 'care_maintenance'],
  other: ['other'],
};


export function ReviewWorkbench() {
  const [items, setItems] = useState<V2ReviewItem[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [mode, setMode] = useState<'correct' | 'reject' | null>(null);
  const [sentiment, setSentiment] = useState<V2Sentiment>('Neutral');
  const [sentimentBasis, setSentimentBasis] = useState('neutral_business');
  const [resolutionStatus, setResolutionStatus] = useState('unknown');
  const [draftIssues, setDraftIssues] = useState<Array<Record<string, any>>>([]);
  const [note, setNote] = useState('');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiClient.getAIAnalysisV2Reviews()
      .then(result => {
        setItems(result.items);
        setSelectedId(result.items[0]?.event_id ?? null);
      })
      .catch(err => setError(err instanceof Error ? err.message : '审核队列加载失败'));
  }, []);

  const selected = useMemo(
    () => items.find(item => item.event_id === selectedId) ?? null,
    [items, selectedId],
  );
  const reviewed = items.filter(item => ['approved', 'corrected'].includes(item.review_status)).length;
  const event = selected?.gold_payload?.events[0] ?? selected?.model_payload.events[0];

  const updateStatus = (eventId: number, status: V2ReviewItem['review_status'], reviewNote: string, goldPayload?: V2ReviewItem['gold_payload']) => {
    setItems(current => current.map(item => item.event_id === eventId
      ? { ...item, review_status: status, review_note: reviewNote, gold_payload: goldPayload ?? item.gold_payload }
      : item));
  };

  const approve = async () => {
    if (!selected) return;
    await apiClient.reviewAIAnalysisV2Event(selected.event_id, { action: 'approve' });
    updateStatus(selected.event_id, 'approved', '');
  };

  const submitReview = async () => {
    if (!selected || !note.trim() || !mode) return;
    if (mode === 'reject') {
      await apiClient.reviewAIAnalysisV2Event(selected.event_id, { action: 'reject', note });
      updateStatus(selected.event_id, 'rejected', note);
    } else {
      const gold = structuredClone(selected.gold_payload ?? selected.model_payload);
      const correctedEvent = gold.events[0];
      correctedEvent.sentiment_label = sentiment;
      correctedEvent.sentiment_score = sentiment === 'Positive' ? 0.8 : sentiment === 'Negative' ? 0.2 : 0.5;
      correctedEvent.sentiment_basis = sentimentBasis;
      correctedEvent.resolution_status = resolutionStatus;
      correctedEvent.issues = draftIssues;
      await apiClient.reviewAIAnalysisV2Event(selected.event_id, {
        action: 'correct',
        gold_payload: gold,
        note,
      });
      updateStatus(selected.event_id, 'corrected', note, gold);
    }
    setMode(null);
    setNote('');
  };

  const beginCorrection = () => {
    if (!event) return;
    setMode('correct');
    setSentiment(event.sentiment_label);
    setSentimentBasis(event.sentiment_basis);
    setResolutionStatus(event.resolution_status);
    setDraftIssues(structuredClone(event.issues ?? []));
  };

  const updateIssue = (index: number, field: string, value: string) => {
    setDraftIssues(current => current.map((issue, issueIndex) => {
      if (issueIndex !== index) return issue;
      if (field === 'issue_category') {
        return { ...issue, issue_category: value, issue_code: ISSUE_TAXONOMY[value][0] };
      }
      return { ...issue, [field]: value };
    }));
  };

  const changeSentiment = (value: V2Sentiment) => {
    setSentiment(value);
    setSentimentBasis(
      value === 'Positive'
        ? 'positive_expression'
        : value === 'Negative'
          ? 'explicit_complaint'
          : 'neutral_business',
    );
  };

  const addIssue = () => {
    if (!event) return;
    setDraftIssues(current => [...current, {
      issue_category: 'other', issue_code: 'other', issue_detail: '待人工补充',
      severity: 'low', owner: 'unknown', status: 'unknown', is_primary: current.length === 0,
      evidence_text: event.topic_summary, evidence_msg_time: event.event_started_at,
    }]);
  };

  return (
    <section className="space-y-3 text-slate-900" aria-label="人工审核工作台">
      <div className="flex items-center justify-between rounded border border-slate-200 bg-white px-4 py-3">
        <div>
          <h2 className="text-sm font-semibold">50 例人工审核</h2>
          <p className="text-xs text-slate-600">逐例确认情感边界、具体问题和处理结果。</p>
        </div>
        <strong className="text-sm">已审核 {reviewed} / 50</strong>
      </div>
      {error && <p role="alert" className="rounded border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-900">{error}</p>}

      <div className="grid min-h-[560px] grid-cols-1 overflow-hidden rounded border border-slate-300 bg-slate-100 lg:grid-cols-[280px_minmax(0,1fr)_minmax(360px,1fr)]">
        <aside className="border-b border-slate-300 bg-slate-100 p-3 lg:border-b-0 lg:border-r" aria-label="审核队列">
          <p className="mb-2 text-[11px] font-bold uppercase tracking-wider text-slate-600">审核队列</p>
          <div className="space-y-2">
            {items.map(item => (
              <button
                key={item.event_id}
                type="button"
                onClick={() => { setSelectedId(item.event_id); setMode(null); setNote(''); }}
                className={`w-full rounded border p-3 text-left focus:outline-none focus:ring-2 focus:ring-orange-500 ${selectedId === item.event_id ? 'border-orange-400 bg-white' : 'border-slate-200 bg-slate-50 hover:bg-white'}`}
              >
                <strong className="block text-sm text-slate-900">{item.buyer_nick}</strong>
                <span className="mt-1 block text-xs text-slate-600">{item.topic_summary}</span>
                <span className="mt-2 inline-block rounded bg-slate-200 px-1.5 py-0.5 text-[10px] font-semibold text-slate-700">{item.review_stratum ?? 'baseline'} · {item.review_status}</span>
              </button>
            ))}
          </div>
        </aside>

        <article className="border-b border-slate-300 bg-white p-4 lg:border-b-0 lg:border-r" aria-label="完整对话">
          <p className="mb-3 text-[11px] font-bold uppercase tracking-wider text-slate-600">完整对话</p>
          {selected ? (
            <div className="space-y-3">
              {selected.dialogue.map((message, index) => (
                <div key={`${message.msg_time}-${index}`} className={`max-w-[88%] rounded border p-3 ${message.role === 'buyer' ? 'border-orange-200 bg-orange-50 text-slate-900' : 'ml-auto border-slate-200 bg-slate-100 text-slate-900'}`}>
                  <div className="flex justify-between gap-3 text-[10px] font-semibold text-slate-600">
                    <span>{message.role === 'buyer' ? '买家' : '客服'}</span>
                    <time>{message.msg_time}</time>
                  </div>
                  <p className="mt-1 text-sm leading-relaxed">{message.content}</p>
                </div>
              ))}
            </div>
          ) : <p className="text-sm text-slate-600">审核队列为空。</p>}
        </article>

        <article className="bg-white p-4" aria-label="分析结果">
          <p className="mb-3 text-[11px] font-bold uppercase tracking-wider text-slate-600">分析结果</p>
          {selected && event ? (
            <div className="space-y-4">
              <div className="rounded border border-slate-200 bg-slate-50 p-3">
                <p className="text-xs text-slate-600">模型情感</p>
                <strong className="mt-1 block text-lg text-slate-900">{event.sentiment_label}</strong>
                <p className="mt-2 text-sm text-slate-700">{event.topic_summary}</p>
                <p className="mt-1 text-xs text-slate-600">处理结果：{event.resolution_status}</p>
              </div>

              {!mode ? (
                <div className="flex flex-wrap gap-2">
                  <button type="button" onClick={approve} className="rounded border border-emerald-300 bg-emerald-50 px-3 py-2 text-xs font-semibold text-emerald-900 hover:bg-emerald-100 focus:outline-none focus:ring-2 focus:ring-emerald-500">结果正确</button>
                  <button type="button" onClick={beginCorrection} className="rounded border border-orange-300 bg-orange-50 px-3 py-2 text-xs font-semibold text-orange-900 hover:bg-orange-100 focus:outline-none focus:ring-2 focus:ring-orange-500">修改结果</button>
                  <button type="button" onClick={() => setMode('reject')} className="rounded border border-red-300 bg-red-50 px-3 py-2 text-xs font-semibold text-red-900 hover:bg-red-100 focus:outline-none focus:ring-2 focus:ring-red-500">驳回结果</button>
                </div>
              ) : (
                <div className="space-y-3 rounded border border-slate-300 bg-slate-50 p-3">
                  {mode === 'correct' && (
                    <div className="space-y-3">
                      <label className="block text-xs font-semibold text-slate-800">最终情感
                        <select value={sentiment} onChange={e => changeSentiment(e.target.value as V2Sentiment)} className="mt-1 block w-full rounded border border-slate-300 bg-white px-2 py-2 text-sm text-slate-900">
                          <option value="Positive">Positive</option>
                          <option value="Neutral">Neutral</option>
                          <option value="Negative">Negative</option>
                        </select>
                      </label>
                      <label className="block text-xs font-semibold text-slate-800">情感依据
                        <select value={sentimentBasis} onChange={e => setSentimentBasis(e.target.value)} className="mt-1 block w-full rounded border border-slate-300 bg-white px-2 py-2 text-sm text-slate-900">
                          {sentiment === 'Positive' && <option value="positive_expression">positive_expression</option>}
                          {sentiment === 'Neutral' && <>
                            <option value="neutral_business">neutral_business</option>
                            <option value="authenticity_concern">authenticity_concern</option>
                          </>}
                          {sentiment === 'Negative' && <>
                            <option value="explicit_complaint">explicit_complaint</option>
                            <option value="abuse_or_threat">abuse_or_threat</option>
                            <option value="strong_negative_evaluation">strong_negative_evaluation</option>
                          </>}
                        </select>
                      </label>
                      <label className="block text-xs font-semibold text-slate-800">处理结果
                        <select value={resolutionStatus} onChange={e => setResolutionStatus(e.target.value)} className="mt-1 block w-full rounded border border-slate-300 bg-white px-2 py-2 text-sm text-slate-900">
                          <option value="unresolved">unresolved</option>
                          <option value="explained_pending_acceptance">explained_pending_acceptance</option>
                          <option value="resolved">resolved</option>
                          <option value="unknown">unknown</option>
                        </select>
                      </label>
                      {draftIssues.map((issue, index) => (
                        <fieldset key={index} className="space-y-2 rounded border border-slate-200 bg-white p-2">
                          <legend className="px-1 text-xs font-semibold text-slate-700">问题 {index + 1}</legend>
                          <label className="block text-xs text-slate-700">问题分类 {index + 1}
                            <select value={issue.issue_category} onChange={e => updateIssue(index, 'issue_category', e.target.value)} className="mt-1 block w-full rounded border border-slate-300 bg-white px-2 py-1.5 text-xs text-slate-900">
                              {Object.keys(ISSUE_TAXONOMY).map(category => <option key={category} value={category}>{category}</option>)}
                            </select>
                          </label>
                          <label className="block text-xs text-slate-700">问题代码 {index + 1}
                            <select value={issue.issue_code} onChange={e => updateIssue(index, 'issue_code', e.target.value)} className="mt-1 block w-full rounded border border-slate-300 bg-white px-2 py-1.5 text-xs text-slate-900">
                              {(ISSUE_TAXONOMY[issue.issue_category] ?? ['other']).map(code => <option key={code} value={code}>{code}</option>)}
                            </select>
                          </label>
                          <label className="block text-xs text-slate-700">问题详情 {index + 1}
                            <textarea value={issue.issue_detail} onChange={e => updateIssue(index, 'issue_detail', e.target.value)} rows={2} className="mt-1 block w-full rounded border border-slate-300 bg-white px-2 py-1.5 text-xs text-slate-900" />
                          </label>
                          <div className="grid grid-cols-2 gap-2">
                            <label className="block text-xs text-slate-700">严重度 {index + 1}
                              <select value={issue.severity} onChange={e => updateIssue(index, 'severity', e.target.value)} className="mt-1 block w-full rounded border border-slate-300 bg-white px-2 py-1.5 text-xs text-slate-900">
                                {['low', 'medium', 'high', 'critical'].map(value => <option key={value}>{value}</option>)}
                              </select>
                            </label>
                            <label className="block text-xs text-slate-700">问题状态 {index + 1}
                              <select value={issue.status} onChange={e => updateIssue(index, 'status', e.target.value)} className="mt-1 block w-full rounded border border-slate-300 bg-white px-2 py-1.5 text-xs text-slate-900">
                                {['open', 'explained_pending_acceptance', 'resolved', 'unknown'].map(value => <option key={value}>{value}</option>)}
                              </select>
                            </label>
                          </div>
                          <button type="button" onClick={() => setDraftIssues(current => current.filter((_, issueIndex) => issueIndex !== index))} className="text-xs font-semibold text-red-700">删除这个问题</button>
                        </fieldset>
                      ))}
                      <button type="button" onClick={addIssue} className="rounded border border-slate-300 bg-white px-2 py-1 text-xs font-semibold text-slate-700">新增问题</button>
                    </div>
                  )}
                  <label className="block text-xs font-semibold text-slate-800">审核备注
                    <textarea value={note} onChange={e => setNote(e.target.value)} rows={4} className="mt-1 block w-full rounded border border-slate-300 bg-white px-2 py-2 text-sm text-slate-900" />
                  </label>
                  <div className="flex gap-2">
                    <button type="button" disabled={!note.trim()} onClick={submitReview} className="rounded bg-slate-900 px-3 py-2 text-xs font-semibold text-white hover:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-orange-500 disabled:opacity-40">{mode === 'correct' ? '确认并加入金标准' : '确认驳回'}</button>
                    <button type="button" onClick={() => setMode(null)} className="rounded border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-800">取消</button>
                  </div>
                </div>
              )}
            </div>
          ) : <p className="text-sm text-slate-600">选择一个案例开始审核。</p>}
        </article>
      </div>
    </section>
  );
}
