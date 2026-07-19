import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Eye, Loader2, RotateCcw, Save } from 'lucide-react';
import { NotionCard } from '../common/NotionCard';
import { NotionTag } from '../common/NotionTag';
import { apiClient, TagConfig } from '../../api/client';

type Category = TagConfig['category'];

const CATEGORY_LABEL: Record<Category, string> = {
  vip: 'VIP 等级',
  churn: '流失风险',
  discount: '折扣敏感度',
  lifecycle: '生命周期',
  purchase_freq: '购买频次',
  chat_recent: '近期聊天活跃度',
  smoker: '烟具品类',
};

const CATEGORY_ORDER: Category[] = ['vip', 'churn', 'discount', 'lifecycle', 'purchase_freq', 'chat_recent'];

interface DraftRow {
  config_key: string;
  config_value: number;
  config_label: string;
  category: Category;
  dirty: boolean;
}

export const ThresholdConfigPanel: React.FC = () => {
  const [configs, setConfigs] = useState<TagConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [drafts, setDrafts] = useState<Record<string, DraftRow>>({});
  const [savingKey, setSavingKey] = useState<string | null>(null);
  const [previewKey, setPreviewKey] = useState<string | null>(null);
  const [previewResult, setPreviewResult] = useState<string>('');

  useEffect(() => {
    apiClient.getTagConfig()
      .then((r) => {
        setConfigs(r.configs);
        setDrafts(
          Object.fromEntries(
            r.configs.map((c) => [
              c.config_key,
              { config_key: c.config_key, config_value: c.config_value, config_label: c.config_label, category: c.category, dirty: false },
            ]),
          ),
        );
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : '加载失败'))
      .finally(() => setLoading(false));
  }, []);

  const grouped = useMemo(() => {
    const map: Record<Category, DraftRow[]> = {} as Record<Category, DraftRow[]>;
    for (const row of Object.values(drafts)) {
      (map[row.category] ??= []).push(row);
    }
    for (const cat of Object.keys(map) as Category[]) {
      map[cat].sort((a, b) => a.config_key.localeCompare(b.config_key));
    }
    return map;
  }, [drafts]);

  const dirtyCount = useMemo(
    () => Object.values(drafts).filter((d) => d.dirty).length,
    [drafts],
  );

  const setDraftValue = useCallback((key: string, value: number) => {
    setDrafts((prev) => {
      const cur = prev[key];
      if (!cur) return prev;
      return { ...prev, [key]: { ...cur, config_value: value, dirty: true } };
    });
    setPreviewResult('');
  }, []);

  const resetDraft = useCallback((key: string) => {
    const original = configs.find((c) => c.config_key === key);
    if (!original) return;
    setDrafts((prev) => {
      const cur = prev[key];
      if (!cur) return prev;
      return { ...prev, [key]: { ...cur, config_value: original.config_value, dirty: false } };
    });
  }, [configs]);

  const handleSave = useCallback(async (key: string) => {
    const row = drafts[key];
    if (!row || !row.dirty) return;
    setSavingKey(key);
    setError(null);
    try {
      const r = await apiClient.updateTagConfig(key, row.config_value);
      setDrafts((prev) => {
        const cur = prev[key];
        if (!cur) return prev;
        return { ...prev, [key]: { ...cur, dirty: false } };
      });
      setPreviewResult(r.message);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '保存失败');
    } finally {
      setSavingKey(null);
    }
  }, [drafts]);

  const handlePreview = useCallback(async (key: string) => {
    const row = drafts[key];
    if (!row) return;
    setPreviewKey(key);
    setError(null);
    try {
      const r = await apiClient.previewTagConfig({ [key]: row.config_value });
      setPreviewResult(JSON.stringify(r.preview, null, 2));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '预览失败');
    } finally {
      setPreviewKey(null);
    }
  }, [drafts]);

  if (loading) {
    return (
      <NotionCard title="阈值与标签配置">
        <div className="flex items-center justify-center py-8 text-notion-muted">
          <Loader2 size={20} className="animate-spin mr-2" />
          <span className="text-sm">加载配置中...</span>
        </div>
      </NotionCard>
    );
  }

  if (error && !configs.length) {
    return (
      <NotionCard title="阈值与标签配置">
        <div className="text-sm text-red-600">{error}</div>
      </NotionCard>
    );
  }

  return (
    <NotionCard
      title="阈值与标签配置"
      subtitle={`P2: 调整 VIP/流失/折扣/生命周期 等标签的阈值规则 (${configs.length} 项)`}
      action={
        dirtyCount > 0 ? (
          <NotionTag text={`${dirtyCount} 项待保存`} color="orange" size="xs" />
        ) : (
          <NotionTag text="已同步" color="green" size="xs" />
        )
      }
    >
      <div className="text-xs text-notion-muted mb-4 p-2 bg-yellow-50 border border-yellow-200 rounded-sm">
        ⚠️ 调整后需在数据库端手动 <code className="text-notion-text">CALL refresh_target_buyers_precomputed()</code> 让目标买家表字段按新阈值重算, 否则前后端展示会出现分歧。
      </div>

      {CATEGORY_ORDER.map((cat) => {
        const rows = grouped[cat] ?? [];
        if (rows.length === 0) return null;
        return (
          <div key={cat} className="mb-6">
            <h3 className="text-sm font-medium text-notion-text mb-2">{CATEGORY_LABEL[cat]}</h3>
            <div className="space-y-2">
              {rows.map((row) => (
                <div
                  key={row.config_key}
                  className={`grid grid-cols-12 gap-2 items-center p-2 border rounded-sm ${
                    row.dirty ? 'border-orange-300 bg-orange-50/30' : 'border-notion-border bg-white'
                  }`}
                >
                  <div className="col-span-12 md:col-span-6">
                    <div className="text-xs text-notion-text">{row.config_label}</div>
                    <code className="text-xs text-notion-muted">{row.config_key}</code>
                  </div>
                  <div className="col-span-6 md:col-span-3">
                    <input
                      type="number"
                      step="any"
                      value={row.config_value}
                      onChange={(e) => setDraftValue(row.config_key, Number(e.target.value))}
                      className="w-full px-2 py-1 text-xs border border-notion-border rounded-sm bg-white"
                    />
                  </div>
                  <div className="col-span-6 md:col-span-3 flex justify-end gap-1">
                    <button
                      type="button"
                      onClick={() => handlePreview(row.config_key)}
                      disabled={previewKey === row.config_key}
                      className="text-xs px-2 py-1 border border-notion-border rounded-sm flex items-center gap-1 hover:bg-gray-50 disabled:opacity-50"
                      title="预览影响"
                    >
                      <Eye size={12} />
                      预览
                    </button>
                    <button
                      type="button"
                      onClick={() => resetDraft(row.config_key)}
                      disabled={!row.dirty}
                      className="text-xs px-2 py-1 border border-notion-border rounded-sm flex items-center gap-1 hover:bg-gray-50 disabled:opacity-50"
                      title="还原"
                    >
                      <RotateCcw size={12} />
                    </button>
                    <button
                      type="button"
                      onClick={() => handleSave(row.config_key)}
                      disabled={!row.dirty || savingKey === row.config_key}
                      className="text-xs px-2 py-1 bg-blue-600 text-white rounded-sm flex items-center gap-1 disabled:opacity-50"
                    >
                      {savingKey === row.config_key ? (
                        <Loader2 size={12} className="animate-spin" />
                      ) : (
                        <Save size={12} />
                      )}
                      保存
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        );
      })}

      {error && (
        <div className="mt-3 p-2 text-xs text-red-600 bg-red-50 border border-red-200 rounded-sm">
          {error}
        </div>
      )}

      {previewResult && (
        <div className="mt-3 p-3 bg-gray-50 border border-notion-border rounded-sm">
          <div className="text-xs text-notion-muted mb-1">预览结果</div>
          <pre className="text-xs text-notion-text whitespace-pre-wrap break-all">{previewResult}</pre>
        </div>
      )}
    </NotionCard>
  );
};