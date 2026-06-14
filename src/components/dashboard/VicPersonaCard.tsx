import { useEffect, useMemo, useState } from 'react';
import { Crown, HeartCrack, Sparkles, Target } from 'lucide-react';
import { fetchVicPersona } from '../../api/insights';
import type { KeywordItem, MotivationItem, VicPersona } from '../../types/insights';
import { ErrorAlert } from '../common/ErrorAlert';
import { LoadingSpinner } from '../common/LoadingState';

const MAX_THEME_COUNT = 8;

export function VicPersonaCard() {
  const [data, setData] = useState<VicPersona | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    fetchVicPersona(controller.signal)
      .then(setData)
      .catch((requestError) => {
        if (requestError?.name !== 'AbortError') {
          setError(requestError instanceof Error ? requestError.message : 'VIC 群体画像加载失败');
        }
      })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, []);

  if (loading) return <CardShell><LoadingSpinner /></CardShell>;
  if (error) return <CardShell><ErrorAlert message={error} /></CardShell>;
  if (!data) return null;

  return (
    <CardShell>
      <div className="mb-5 flex flex-col gap-2 border-b border-notion-border pb-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <div className="mb-1 flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.14em] text-orange-700">
            <Crown size={14} /> VIC cohort intelligence
          </div>
          <h2 className="text-lg font-semibold text-notion-text">VIC 群体画像</h2>
        </div>
        <div className="text-sm text-notion-muted">
          当前样本 <strong className="font-serif text-2xl font-medium text-notion-text">{data.total_vic_count}</strong> 人
        </div>
      </div>

      <div className="mb-5 rounded-sm border border-orange-100 bg-orange-50/60 px-4 py-3">
        <p className="text-sm font-semibold text-notion-text">{data.summary.headline}</p>
        <div className="mt-2 space-y-1 text-xs leading-relaxed text-notion-muted">
          {data.summary.bullets.map((bullet) => <p key={bullet}>{bullet}</p>)}
        </div>
        <p className="mt-2 text-[10px] text-orange-800/70">
          {data.raw_label_count} 个原始标签已归并为 {data.aggregated_theme_count} 个语义主题
        </p>
      </div>

      <div className="grid gap-5 xl:grid-cols-[1fr_1fr_0.72fr]">
        <KeywordSection
          title="关键兴趣"
          icon={<Sparkles size={15} />}
          items={data.key_interests}
          tone="blue"
        />
        <KeywordSection
          title="关键痛点"
          icon={<HeartCrack size={15} />}
          items={data.key_pain_points}
          tone="red"
        />
        <MotivationSection items={data.purchase_motivations} />
      </div>
    </CardShell>
  );
}

function CardShell({ children }: { children: React.ReactNode }) {
  return <section className="rounded-sm border border-notion-border bg-white p-5 shadow-sm">{children}</section>;
}

function KeywordSection({
  title,
  icon,
  items,
  tone,
}: {
  title: string;
  icon: React.ReactNode;
  items: KeywordItem[];
  tone: 'blue' | 'red';
}) {
  const visibleItems = useMemo(
    () => items
      .filter((item) => !item.keyword.startsWith('其他'))
      .sort((a, b) => b.count - a.count)
      .slice(0, MAX_THEME_COUNT),
    [items],
  );
  const chipClass = tone === 'blue'
    ? 'border-blue-100 bg-blue-50 text-blue-800'
    : 'border-red-100 bg-red-50 text-red-800';

  return (
    <div>
      <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-notion-text">{icon}{title}</h3>
      {visibleItems.length === 0 ? (
        <p className="rounded border border-dashed border-notion-border py-8 text-center text-xs text-notion-muted">数据不足</p>
      ) : (
        <div className="flex flex-wrap gap-2">
          {visibleItems.map((item) => (
            <div key={`${title}-${item.keyword}`} className={`max-w-full rounded border px-2.5 py-1.5 text-xs ${chipClass}`}>
              <div className="flex items-center gap-1.5">
                <span className="font-medium">{item.keyword}</span>
                <span className="shrink-0 opacity-60">{item.count} 人 · {item.percentage}%</span>
              </div>
              {item.examples && item.examples.length > 0 && (
                <div className="mt-1 max-w-[300px] truncate text-[10px] opacity-60" title={item.examples.join(' · ')}>
                  {item.examples.join(' · ')}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function MotivationSection({ items }: { items: MotivationItem[] }) {
  const maxCount = Math.max(...items.map((item) => item.count), 1);
  return (
    <div>
      <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-notion-text"><Target size={15} />购买动机</h3>
      <div className="space-y-3">
        {items.length === 0 && <p className="text-xs text-notion-muted">数据不足</p>}
        {items.map((item) => (
          <div key={item.pattern}>
            <div className="mb-1 flex justify-between gap-2 text-xs">
              <span className="text-notion-text">{item.pattern}</span>
              <span className="tabular-nums text-notion-muted">{item.count} 人</span>
            </div>
            <div className="h-1.5 overflow-hidden rounded-full bg-notion-gray_bg">
              <div className="h-full rounded-full bg-orange-500" style={{ width: `${(item.count / maxCount) * 100}%` }} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
