import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Download, Filter, Loader2, Save, Search, Trash2, X } from 'lucide-react';
import { NotionCard } from '../common/NotionCard';
import { NotionTag } from '../common/NotionTag';
import { apiClient, FilterOptions, SegmentBuyer, SegmentFilters } from '../../api/client';

const SAVED_SEGMENTS_KEY = 'smokesignal_saved_segments';

interface SavedSegment {
  id: string;
  name: string;
  filters: SegmentFilters;
  created_at: string;
}

interface FilterChipProps {
  label: string;
  selected: string[];
  options: string[];
  onToggle: (value: string) => void;
  color?: 'blue' | 'green' | 'orange' | 'purple' | 'red';
}

function FilterChipGroup({ label, selected, options, onToggle, color = 'blue' }: FilterChipProps) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-xs text-notion-muted font-medium">{label}</span>
      <div className="flex flex-wrap gap-1">
        {options.map((opt) => {
          const active = selected.includes(opt);
          return (
            <button
              key={opt}
              type="button"
              onClick={() => onToggle(opt)}
              className={`px-2 py-1 rounded-sm text-xs transition-colors border ${
                active
                  ? color === 'red'
                    ? 'bg-red-50 border-red-300 text-red-700'
                    : color === 'orange'
                    ? 'bg-orange-50 border-orange-300 text-orange-700'
                    : color === 'green'
                    ? 'bg-green-50 border-green-300 text-green-700'
                    : color === 'purple'
                    ? 'bg-purple-50 border-purple-300 text-purple-700'
                    : 'bg-blue-50 border-blue-300 text-blue-700'
                  : 'bg-white border-notion-border text-notion-muted hover:bg-gray-50'
              }`}
            >
              {opt}
            </button>
          );
        })}
      </div>
    </div>
  );
}

interface RangeFilterProps {
  label: string;
  minKey: keyof SegmentFilters;
  maxKey: keyof SegmentFilters;
  filters: SegmentFilters;
  onChange: (min: number | undefined, max: number | undefined) => void;
  unit?: string;
}

function RangeFilter({ label, minKey, maxKey, filters, onChange, unit = '' }: RangeFilterProps) {
  const minVal = filters[minKey];
  const maxVal = filters[maxKey];

  return (
    <div className="flex flex-col gap-1">
      <span className="text-xs text-notion-muted font-medium">{label}{unit && ` (${unit})`}</span>
      <div className="flex items-center gap-1">
        <input
          type="number"
          placeholder="min"
          value={minVal ?? ''}
          onChange={(e) => {
            const v = e.target.value === '' ? undefined : Number(e.target.value);
            onChange(v, maxVal as number | undefined);
          }}
          className="w-20 px-2 py-1 text-xs border border-notion-border rounded-sm bg-white"
        />
        <span className="text-xs text-notion-muted">—</span>
        <input
          type="number"
          placeholder="max"
          value={maxVal ?? ''}
          onChange={(e) => {
            const v = e.target.value === '' ? undefined : Number(e.target.value);
            onChange(minVal as number | undefined, v);
          }}
          className="w-20 px-2 py-1 text-xs border border-notion-border rounded-sm bg-white"
        />
      </div>
    </div>
  );
}

export const SegmentationBuilder: React.FC = () => {
  const [filters, setFilters] = useState<SegmentFilters>({});
  const [filterOptions, setFilterOptions] = useState<FilterOptions | null>(null);
  const [optionsLoading, setOptionsLoading] = useState(true);

  const [count, setCount] = useState<number | null>(null);
  const [counting, setCounting] = useState(false);

  const [results, setResults] = useState<SegmentBuyer[]>([]);
  const [resultsTotal, setResultsTotal] = useState<number | null>(null);
  const [resultsLoading, setResultsLoading] = useState(false);
  const [page, setPage] = useState(1);
  const PAGE_SIZE = 20;

  const [segmentName, setSegmentName] = useState('');
  const [savedSegments, setSavedSegments] = useState<SavedSegment[]>([]);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    apiClient.getFilterOptions()
      .then(setFilterOptions)
      .catch((err: unknown) => {
        console.error('Failed to load filter options', err);
      })
      .finally(() => setOptionsLoading(false));

    try {
      const raw = localStorage.getItem(SAVED_SEGMENTS_KEY);
      if (raw) setSavedSegments(JSON.parse(raw) as SavedSegment[]);
    } catch {
      // 忽略 localStorage 解析错误
    }
  }, []);

  const persistSavedSegments = useCallback((next: SavedSegment[]) => {
    setSavedSegments(next);
    localStorage.setItem(SAVED_SEGMENTS_KEY, JSON.stringify(next));
  }, []);

  const toggleTagFilter = useCallback(
    (key: keyof SegmentFilters, value: string) => {
      setFilters((prev) => {
        const current = (prev[key] as string[] | undefined) ?? [];
        const next = current.includes(value)
          ? current.filter((v) => v !== value)
          : [...current, value];
        const updated: SegmentFilters = { ...prev };
        if (next.length === 0) {
          delete (updated as Record<string, unknown>)[key];
        } else {
          (updated as Record<string, unknown>)[key] = next;
        }
        return updated;
      });
    },
    [],
  );

  const setRange = useCallback(
    (minKey: keyof SegmentFilters, maxKey: keyof SegmentFilters, min: number | undefined, max: number | undefined) => {
      setFilters((prev) => {
        const updated: SegmentFilters = { ...prev };
        const rec = updated as Record<string, unknown>;
        if (min === undefined) delete rec[minKey];
        else rec[minKey] = min;
        if (max === undefined) delete rec[maxKey];
        else rec[maxKey] = max;
        return updated;
      });
    },
    [],
  );

  const hasAnyFilter = useMemo(() => {
    return Object.values(filters).some((v) =>
      Array.isArray(v) ? v.length > 0 : v !== undefined && v !== null,
    );
  }, [filters]);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (!hasAnyFilter) {
      setCount(null);
      return;
    }
    debounceRef.current = setTimeout(() => {
      setCounting(true);
      apiClient.getSegmentCount(filters)
        .then((r) => setCount(r.total))
        .catch((err: unknown) => console.error('count failed', err))
        .finally(() => setCounting(false));
    }, 500);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [filters, hasAnyFilter]);

  const runQuery = useCallback(
    (pageNum = 1) => {
      setResultsLoading(true);
      setPage(pageNum);
      apiClient
        .querySegment(filters, PAGE_SIZE, (pageNum - 1) * PAGE_SIZE, true)
        .then((r) => {
          setResults(r.buyers);
          setResultsTotal(r.total);
        })
        .catch((err: unknown) => console.error('query failed', err))
        .finally(() => setResultsLoading(false));
    },
    [filters],
  );

  const handleExport = useCallback(() => {
    window.open(apiClient.getSegmentExportUrl(filters), '_blank');
  }, [filters]);

  const handleSave = useCallback(() => {
    if (!segmentName.trim()) return;
    const next: SavedSegment[] = [
      ...savedSegments,
      { id: String(Date.now()), name: segmentName.trim(), filters, created_at: new Date().toISOString() },
    ];
    persistSavedSegments(next);
    setSegmentName('');
  }, [segmentName, filters, savedSegments, persistSavedSegments]);

  const handleLoad = useCallback((seg: SavedSegment) => {
    setFilters(seg.filters);
  }, []);

  const handleDelete = useCallback((id: string) => {
    persistSavedSegments(savedSegments.filter((s) => s.id !== id));
  }, [savedSegments, persistSavedSegments]);

  const handleReset = useCallback(() => {
    setFilters({});
    setResults([]);
    setResultsTotal(null);
    setCount(null);
  }, []);

  const totalPages = resultsTotal ? Math.max(1, Math.ceil(resultsTotal / PAGE_SIZE)) : 1;

  if (optionsLoading) {
    return (
      <NotionCard title="人群分群构建器" subtitle="按标签和指标自由组合,圈选目标客户">
        <div className="flex items-center justify-center py-8 text-notion-muted">
          <Loader2 size={20} className="animate-spin mr-2" />
          <span className="text-sm">加载筛选条件中...</span>
        </div>
      </NotionCard>
    );
  }

  if (!filterOptions) {
    return (
      <NotionCard title="人群分群构建器">
        <div className="text-sm text-red-600">无法加载筛选条件,请刷新页面</div>
      </NotionCard>
    );
  }

  return (
    <NotionCard
      title="人群分群构建器"
      subtitle="按标签和指标自由组合,圈选目标客户"
      icon={Filter}
      action={
        <div className="flex items-center gap-2">
          {hasAnyFilter && (
            <button
              type="button"
              onClick={handleReset}
              className="text-xs text-notion-muted hover:text-notion-text flex items-center gap-1 px-2 py-1 rounded-sm"
            >
              <X size={12} />
              清空筛选
            </button>
          )}
          <button
            type="button"
            onClick={handleExport}
            disabled={!hasAnyFilter}
            className="text-xs px-2 py-1 border border-notion-border rounded-sm flex items-center gap-1 hover:bg-gray-50 disabled:opacity-50"
          >
            <Download size={12} />
            导出 CSV
          </button>
        </div>
      }
    >
      {/* 保存/加载区 */}
      <div className="flex items-center gap-2 mb-4 pb-3 border-b border-notion-border">
        <input
          type="text"
          placeholder="为当前分群命名..."
          value={segmentName}
          onChange={(e) => setSegmentName(e.target.value)}
          className="flex-1 px-2 py-1 text-xs border border-notion-border rounded-sm"
        />
        <button
          type="button"
          onClick={handleSave}
          disabled={!segmentName.trim() || !hasAnyFilter}
          className="text-xs px-3 py-1 bg-blue-600 text-white rounded-sm flex items-center gap-1 disabled:opacity-50"
        >
          <Save size={12} />
          保存
        </button>
        {savedSegments.length > 0 && (
          <select
            value=""
            onChange={(e) => {
              const seg = savedSegments.find((s) => s.id === e.target.value);
              if (seg) handleLoad(seg);
            }}
            className="text-xs px-2 py-1 border border-notion-border rounded-sm bg-white"
          >
            <option value="">加载已保存 ({savedSegments.length})</option>
            {savedSegments.map((s) => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>
        )}
      </div>

      {/* 标签筛选 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 mb-4">
        <FilterChipGroup
          label="VIP 等级"
          selected={filters.vip_level ?? []}
          options={filterOptions.vip_levels}
          onToggle={(v) => toggleTagFilter('vip_level', v)}
          color="purple"
        />
        <FilterChipGroup
          label="生命周期"
          selected={filters.lifecycle_stage ?? []}
          options={filterOptions.lifecycle_stages}
          onToggle={(v) => toggleTagFilter('lifecycle_stage', v)}
          color="blue"
        />
        <FilterChipGroup
          label="买家类型"
          selected={filters.buyer_type ?? []}
          options={filterOptions.buyer_types}
          onToggle={(v) => toggleTagFilter('buyer_type', v)}
          color="green"
        />
        <FilterChipGroup
          label="流失风险"
          selected={filters.churn_risk ?? []}
          options={filterOptions.churn_risks}
          onToggle={(v) => toggleTagFilter('churn_risk', v)}
          color="red"
        />
        <FilterChipGroup
          label="渠道"
          selected={filters.channel ?? []}
          options={filterOptions.channels}
          onToggle={(v) => toggleTagFilter('channel', v)}
          color="blue"
        />
        <FilterChipGroup
          label="情感"
          selected={filters.sentiment_label ?? []}
          options={filterOptions.sentiment_labels}
          onToggle={(v) => toggleTagFilter('sentiment_label', v)}
          color="green"
        />
        <FilterChipGroup
          label="跟进优先级"
          selected={filters.follow_priority ?? []}
          options={filterOptions.follow_priorities}
          onToggle={(v) => toggleTagFilter('follow_priority', v)}
          color="orange"
        />
        <FilterChipGroup
          label="新老客"
          selected={filters.client_monthly_tag ?? []}
          options={filterOptions.client_monthly_tags}
          onToggle={(v) => toggleTagFilter('client_monthly_tag', v)}
          color="purple"
        />
      </div>

      {/* 指标范围 */}
      <details className="mb-4">
        <summary className="text-xs text-notion-muted cursor-pointer hover:text-notion-text font-medium">
          指标范围筛选
        </summary>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3 mt-3 pt-3 border-t border-notion-border">
          <RangeFilter label="历史GMV" minKey="min_gmv" maxKey="max_gmv" filters={filters} onChange={(a, b) => setRange('min_gmv', 'max_gmv', a, b)} unit="元" />
          <RangeFilter label="总订单数" minKey="min_orders" maxKey="max_orders" filters={filters} onChange={(a, b) => setRange('min_orders', 'max_orders', a, b)} />
          <RangeFilter label="L6M净销售" minKey="min_l6m_netsales" maxKey="max_l6m_netsales" filters={filters} onChange={(a, b) => setRange('min_l6m_netsales', 'max_l6m_netsales', a, b)} unit="元" />
          <RangeFilter label="退款率" minKey="min_refund_rate" maxKey="max_refund_rate" filters={filters} onChange={(a, b) => setRange('min_refund_rate', 'max_refund_rate', a, b)} unit="%" />
          <RangeFilter label="购买间隔" minKey="min_purchase_interval" maxKey="max_purchase_interval" filters={filters} onChange={(a, b) => setRange('min_purchase_interval', 'max_purchase_interval', a, b)} unit="天" />
          <RangeFilter label="距今未购买" minKey="min_days_since_purchase" maxKey="max_days_since_purchase" filters={filters} onChange={(a, b) => setRange('min_days_since_purchase', 'max_days_since_purchase', a, b)} unit="天" />
        </div>
      </details>

      {/* 实时计数 + 操作 */}
      <div className="flex items-center gap-3 mb-4 p-3 bg-gray-50 rounded-sm">
        <div className="flex-1">
          <div className="text-xs text-notion-muted">匹配买家数</div>
          <div className="text-2xl font-semibold text-notion-text">
            {counting ? <Loader2 size={20} className="animate-spin inline" /> : (count ?? '—')}
          </div>
        </div>
        <button
          type="button"
          onClick={() => runQuery(1)}
          disabled={!hasAnyFilter || resultsLoading}
          className="px-4 py-2 bg-blue-600 text-white text-sm rounded-sm flex items-center gap-2 disabled:opacity-50"
        >
          <Search size={14} />
          {resultsLoading ? '查询中...' : '查看结果'}
        </button>
      </div>

      {/* 已保存分群列表 */}
      {savedSegments.length > 0 && (
        <div className="mb-4 p-3 bg-blue-50/30 rounded-sm">
          <div className="text-xs font-medium text-notion-text mb-2">已保存的分群</div>
          <div className="flex flex-wrap gap-2">
            {savedSegments.map((s) => (
              <div key={s.id} className="flex items-center gap-1 bg-white px-2 py-1 rounded-sm border border-notion-border">
                <NotionTag text={s.name} color="blue" size="xs" />
                <button
                  type="button"
                  onClick={() => handleDelete(s.id)}
                  className="text-notion-muted hover:text-red-600"
                >
                  <Trash2 size={12} />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 结果表格 */}
      {results.length > 0 && (
        <div className="border border-notion-border rounded-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead className="bg-gray-50 border-b border-notion-border">
                <tr>
                  <th className="px-3 py-2 text-left font-medium text-notion-muted whitespace-nowrap">客户</th>
                  <th className="px-2 py-2 text-left font-medium text-notion-muted whitespace-nowrap">VIP</th>
                  <th className="px-2 py-2 text-left font-medium text-notion-muted whitespace-nowrap">生命周期</th>
                  <th className="px-2 py-2 text-left font-medium text-notion-muted whitespace-nowrap">类型</th>
                  <th className="px-2 py-2 text-left font-medium text-notion-muted whitespace-nowrap">流失</th>
                  <th className="px-2 py-2 text-right font-medium text-notion-muted whitespace-nowrap">Rolling 24M</th>
                  <th className="px-2 py-2 text-right font-medium text-notion-muted whitespace-nowrap">L6M</th>
                  <th className="px-2 py-2 text-right font-medium text-notion-muted whitespace-nowrap">订单数</th>
                  <th className="px-2 py-2 text-left font-medium text-notion-muted whitespace-nowrap">品类偏好</th>
                  <th className="px-2 py-2 text-left font-medium text-notion-muted whitespace-nowrap">城市</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-notion-border">
                {results.map((b) => (
                  <tr key={b.buyer_nick} className="hover:bg-gray-50">
                    <td className="px-3 py-2 text-notion-text">{b.buyer_nick}</td>
                    <td className="px-2 py-2">
                      <NotionTag text={b.vip_level || 'N/A'} size="xs" color={b.vip_level === 'V3' || b.vip_level === 'V2' ? 'red' : 'gray'} />
                    </td>
                    <td className="px-2 py-2">
                      <NotionTag text={b.lifecycle_stage || '-'} size="xs" color={getLifecycleColor(b.lifecycle_stage)} />
                    </td>
                    <td className="px-2 py-2 text-notion-text">{b.buyer_type}</td>
                    <td className="px-2 py-2">
                      <NotionTag text={b.churn_risk || '-'} size="xs" color={b.churn_risk === '高' ? 'red' : b.churn_risk === '中' ? 'orange' : 'green'} />
                    </td>
                    <td className="px-2 py-2 text-right tabular-nums">¥{(b.rolling_24m_netsales ?? 0).toLocaleString()}</td>
                    <td className="px-2 py-2 text-right tabular-nums">¥{(b.l6m_netsales ?? 0).toLocaleString()}</td>
                    <td className="px-2 py-2 text-right tabular-nums">{b.total_orders}</td>
                    <td className="px-2 py-2 text-notion-muted">{b.top_category}</td>
                    <td className="px-2 py-2 text-notion-muted">{b.city || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* 分页 */}
          <div className="flex items-center justify-between px-3 py-2 border-t border-notion-border bg-gray-50">
            <span className="text-xs text-notion-muted">
              第 {page} 页 / 共 {totalPages} 页 (总计 {resultsTotal ?? 0} 人)
            </span>
            <div className="flex gap-1">
              <button
                type="button"
                disabled={page === 1 || resultsLoading}
                onClick={() => runQuery(page - 1)}
                className="px-2 py-1 text-xs border border-notion-border rounded-sm disabled:opacity-50"
              >
                上一页
              </button>
              <button
                type="button"
                disabled={page >= totalPages || resultsLoading}
                onClick={() => runQuery(page + 1)}
                className="px-2 py-1 text-xs border border-notion-border rounded-sm disabled:opacity-50"
              >
                下一页
              </button>
            </div>
          </div>
        </div>
      )}

      {!hasAnyFilter && (
        <div className="text-center py-6 text-notion-muted text-sm">
          请选择至少一个筛选条件开始构建分群
        </div>
      )}
    </NotionCard>
  );
};

function getLifecycleColor(stage: string): 'blue' | 'green' | 'purple' | 'orange' | 'red' {
  const map: Record<string, 'blue' | 'green' | 'purple' | 'orange' | 'red'> = {
    '新客': 'blue',
    '成长': 'green',
    '成熟': 'purple',
    '预流失': 'orange',
    '流失': 'red',
  };
  return map[stage] || 'blue';
}
