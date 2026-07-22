import { useEffect, useState } from 'react';

import { apiClient } from '../../api/client';
import type { V2AffectedBuyer, V2IssueTrend } from '../../types/aiAnalysisV2';


const periods = [30, 90, 180] as const;

export function IssueTrendsPanel() {
  const [days, setDays] = useState<(typeof periods)[number]>(30);
  const [filters, setFilters] = useState({ category: '', code: '', status: '', severity: '', buyerType: '' });
  const [items, setItems] = useState<V2IssueTrend[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [buyers, setBuyers] = useState<V2AffectedBuyer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    apiClient.getAIAnalysisV2Trends({
      days,
      issue_category: filters.category || undefined,
      issue_code: filters.code || undefined,
      status: filters.status || undefined,
      severity: filters.severity || undefined,
      buyer_type: filters.buyerType || undefined,
    }).then(result => {
      if (active) setItems(result.items);
    }).catch(err => {
      if (active) setError(err instanceof Error ? err.message : '趋势加载失败');
    }).finally(() => {
      if (active) setLoading(false);
    });
    return () => { active = false; };
  }, [days, filters]);

  const drillDown = async (issueCode: string) => {
    if (selected === issueCode) {
      setSelected(null);
      return;
    }
    setSelected(issueCode);
    try {
      const result = await apiClient.getAIAnalysisV2AffectedBuyers(issueCode, days);
      setBuyers(result.items);
    } catch (err) {
      setBuyers([]);
      setError(err instanceof Error ? err.message : '客户明细加载失败');
    }
  };

  return (
    <section className="space-y-4" aria-label="问题趋势">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded border border-slate-200 bg-white p-3">
        <div className="flex gap-1" aria-label="分析周期">
          {periods.map(period => (
            <button
              key={period}
              type="button"
              aria-pressed={days === period}
              onClick={() => setDays(period)}
              className={`rounded border px-3 py-1.5 text-xs font-semibold focus:outline-none focus:ring-2 focus:ring-orange-500 ${days === period ? 'border-orange-400 bg-orange-50 text-orange-950' : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50'}`}
            >
              {period} 天
            </button>
          ))}
        </div>
        <div className="grid w-full grid-cols-2 gap-2 sm:w-auto sm:grid-cols-5">
          <FilterSelect label="问题分类" value={filters.category} onChange={category => setFilters(current => ({ ...current, category }))} options={['product', 'logistics', 'after_sales', 'pricing_promotion', 'inventory', 'service', 'trust', 'usage_care', 'other']} />
          <label className="text-[11px] font-semibold text-slate-700">问题编码
            <input value={filters.code} onChange={event => setFilters(current => ({ ...current, code: event.target.value }))} className="mt-1 w-full rounded border border-slate-300 bg-white px-2 py-1.5 text-xs text-slate-900" placeholder="issue_code" />
          </label>
          <FilterSelect label="状态" value={filters.status} onChange={status => setFilters(current => ({ ...current, status }))} options={['open', 'explained_pending_acceptance', 'resolved', 'unknown']} />
          <FilterSelect label="严重度" value={filters.severity} onChange={severity => setFilters(current => ({ ...current, severity }))} options={['low', 'medium', 'high', 'critical']} />
          <FilterSelect label="客户类型" value={filters.buyerType} onChange={buyerType => setFilters(current => ({ ...current, buyerType }))} options={['SMOKER', 'VIC', 'BOTH', 'SEASON', 'BULK']} />
        </div>
      </div>

      {error && <p role="alert" className="rounded border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-900">{error}</p>}
      <div className="overflow-hidden rounded border border-slate-200 bg-white">
        <table className="w-full text-left text-xs text-slate-800">
          <thead className="bg-slate-100 text-slate-700">
            <tr>
              {['问题', '事件', '客户', '未解决', '高严重度', '周期变化'].map(label => <th key={label} className="px-3 py-2 font-semibold">{label}</th>)}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200">
            {!loading && items.map(item => (
              <tr key={item.issue_code}>
                <td className="px-3 py-3">
                  <button type="button" onClick={() => drillDown(item.issue_code)} className="font-semibold text-slate-900 underline decoration-slate-300 underline-offset-2 hover:text-orange-800 focus:outline-none focus:ring-2 focus:ring-orange-500">
                    {item.issue_code}
                  </button>
                  <p className="mt-0.5 text-slate-500">{item.issue_category}</p>
                </td>
                <td className="px-3 py-3">{item.event_count}</td>
                <td className="px-3 py-3">{item.affected_buyers} 位客户</td>
                <td className="px-3 py-3">{item.unresolved_count}</td>
                <td className="px-3 py-3">{item.high_severity_count}</td>
                <td className={`px-3 py-3 font-semibold ${item.change_percent > 0 ? 'text-red-800' : 'text-emerald-800'}`}>{item.change_percent > 0 ? '+' : ''}{item.change_percent}%</td>
              </tr>
            ))}
          </tbody>
        </table>
        {loading && <p className="p-6 text-center text-sm text-slate-600">正在加载问题趋势...</p>}
        {!loading && !items.length && !error && <p className="p-6 text-center text-sm text-slate-600">当前筛选范围没有问题事件。</p>}
      </div>

      {selected && (
        <div className="rounded border border-slate-200 bg-slate-50 p-3">
          <h3 className="text-sm font-semibold text-slate-900">受影响客户 · {selected}</h3>
          <ul className="mt-2 grid gap-2 md:grid-cols-2">
            {buyers.map(buyer => (
              <li key={`${buyer.buyer_nick}-${buyer.event_ended_at}`} className="rounded border border-slate-200 bg-white p-2 text-xs text-slate-800">
                <strong>{buyer.buyer_nick}</strong>
                <p className="mt-1 text-slate-600">{buyer.issue_detail}</p>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}


function FilterSelect({ label, value, options, onChange }: { label: string; value: string; options: string[]; onChange: (value: string) => void }) {
  return (
    <label className="text-[11px] font-semibold text-slate-700">{label}
      <select value={value} onChange={event => onChange(event.target.value)} className="mt-1 w-full rounded border border-slate-300 bg-white px-2 py-1.5 text-xs text-slate-900">
        <option value="">全部</option>
        {options.map(option => <option key={option} value={option}>{option}</option>)}
      </select>
    </label>
  );
}
