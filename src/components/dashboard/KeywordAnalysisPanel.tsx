/**
 * KeywordAnalysisPanel - 关键词分析面板
 *
 * 设计风格：Notion 简约风格
 * - 柔和低饱和度的 pastel 色调
 * - 标签式筛选器
 * - 清晰的视觉层次
 */

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  LabelList,
} from 'recharts';
import { Database, X, RefreshCw, Loader2 } from 'lucide-react';
import { NotionCard } from '../common/NotionCard';
import { apiClient, BuyerTypeForKeyword, KeywordAnalysisResponse } from '../../api/client';

// ============================================================
// 设计系统：Notion 风格颜色（低饱和度 pastel）
// ============================================================

const CATEGORY_COLORS: Record<string, string> = {
  '赠品': '#E7DEFF',       // 淡紫色 - 礼物感
  '包装': '#E7F3F8',       // 淡蓝色 - 包装
  '维修保养': '#EDF3EC',   // 淡绿色 - 服务
  '退换货': '#FDEBEC',     // 淡红色 - 警示
  '产品推荐咨询': '#FBF3DB', // 淡黄色 - 咨询
  '产品参数咨询': '#F4EEEE', // 淡棕色 - 技术
  '价格': '#FAF1F5',       // 淡粉色 - 价格
  '物流': '#E7F3F8',       // 淡蓝色 - 物流
  '投诉反馈': '#FDEBEC',   // 淡红色 - 投诉
};

// 图表边框颜色（比背景稍深）
const CATEGORY_STROKES: Record<string, string> = {
  '赠品': '#C4B5FD',
  '包装': '#93C5FD',
  '维修保养': '#86EFAC',
  '退换货': '#FCA5A5',
  '产品推荐咨询': '#FCD34D',
  '产品参数咨询': '#D4A574',
  '价格': '#F9A8D4',
  '物流': '#93C5FD',
  '投诉反馈': '#FCA5A5',
};

const DEFAULT_COLOR = '#F1F1EF';
const DEFAULT_STROKE = '#D1D5DB';

// 客户类型选项（移除 NON_SMOKER_VIC）
const BUYER_TYPE_OPTIONS: { value: BuyerTypeForKeyword; label: string }[] = [
  { value: 'ALL', label: '全部' },
  { value: 'SMOKER', label: 'SMOKER' },
  { value: 'BOTH', label: 'BOTH' },
  { value: 'VIC', label: 'VIC' },
];

interface KeywordAnalysisPanelProps {
  timeRange?: string;
}

export const KeywordAnalysisPanel: React.FC<KeywordAnalysisPanelProps> = () => {
  // ============================================================
  // 状态管理
  // ============================================================
  const [selectedBuyerTypes, setSelectedBuyerTypes] = useState<BuyerTypeForKeyword[]>(['ALL']);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [data, setData] = useState<KeywordAnalysisResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // ============================================================
  // 数据加载
  // ============================================================
  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await apiClient.getKeywordAnalysis({
        buyer_types: selectedBuyerTypes,
        category: selectedCategory || undefined,
        limit: 15,
      });
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载失败');
    } finally {
      setLoading(false);
    }
  }, [selectedBuyerTypes, selectedCategory]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // ============================================================
  // 交互处理
  // ============================================================
  const handleBuyerTypeChange = (type: BuyerTypeForKeyword) => {
    setSelectedCategory(null);

    if (type === 'ALL') {
      setSelectedBuyerTypes(['ALL']);
    } else {
      setSelectedBuyerTypes((prev) => {
        const filtered = prev.filter((t) => t !== 'ALL');
        if (filtered.includes(type)) {
          const newTypes = filtered.filter((t) => t !== type);
          return newTypes.length === 0 ? ['ALL'] : newTypes;
        }
        return [...filtered, type];
      });
    }
  };

  const handleCategoryClick = (category: string) => {
    setSelectedCategory((prev) => (prev === category ? null : category));
  };

  // ============================================================
  // 图表数据准备
  // ============================================================
  const categoryData = useMemo(() => {
    if (!data) return [];
    return data.category_distribution
      .map((item) => ({
        ...item,
        fill: CATEGORY_COLORS[item.name] || DEFAULT_COLOR,
        stroke: CATEGORY_STROKES[item.name] || DEFAULT_STROKE,
      }))
      .sort((a, b) => b.value - a.value); // 按占比降序排列（顺时针从大到小）
  }, [data]);

  const keywordData = useMemo(() => {
    if (!data) return [];
    return data.keywords.map((item) => ({
      ...item,
      fill: CATEGORY_COLORS[item.category] || DEFAULT_COLOR,
      stroke: CATEGORY_STROKES[item.category] || DEFAULT_STROKE,
    }));
  }, [data]);

  const totalCategoryCount = useMemo(
    () => categoryData.reduce((sum, item) => sum + item.value, 0),
    [categoryData]
  );

  // ============================================================
  // 渲染
  // ============================================================
  return (
    <NotionCard
      title="Keyword & Issue Analysis"
      icon={Database}
      className="h-[680px] flex flex-col"
      action={
        <div className="flex items-center gap-2">
          {selectedCategory && (
            <button
              onClick={() => setSelectedCategory(null)}
              className="inline-flex items-center gap-1 px-2 py-1 text-xs text-notion-muted hover:text-notion-text bg-notion-gray_bg rounded transition-colors"
            >
              <X size={10} />
              {selectedCategory}
            </button>
          )}
          <button
            onClick={loadData}
            disabled={loading}
            className="p-1.5 text-notion-muted hover:text-notion-text hover:bg-notion-hover rounded transition-colors"
            title="刷新"
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          </button>
        </div>
      }
    >
      {/* 筛选器 - 标签式设计 */}
      <div className="flex items-center gap-3 mb-4 pb-3 border-b border-notion-border">
        <span className="text-xs text-notion-muted shrink-0">客户类型</span>
        <div className="flex items-center gap-1.5 flex-wrap">
          {BUYER_TYPE_OPTIONS.map((option) => {
            const isSelected = selectedBuyerTypes.includes(option.value);
            return (
              <button
                key={option.value}
                onClick={() => handleBuyerTypeChange(option.value)}
                className={`
                  px-2.5 py-1 text-xs rounded-full transition-all duration-150
                  ${isSelected
                    ? 'bg-notion-text text-white shadow-sm'
                    : 'bg-notion-gray_bg text-notion-muted hover:bg-notion-hover hover:text-notion-text'
                  }
                `}
              >
                {option.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* 主内容区 */}
      <div className="flex-1 relative min-h-0">
        {/* 加载遮罩 */}
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center bg-white/60 backdrop-blur-[2px] z-10 transition-opacity duration-300">
            <Loader2 className="animate-spin text-notion-muted" size={20} />
          </div>
        )}
        {/* 错误状态 */}
        {error && !loading && (
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="text-xs text-red-500">{error}</span>
          </div>
        )}
        {/* 内容区 */}
        {!error && (
        <div className="flex flex-1 gap-6 min-h-0">
          {/* 左侧：分类分布 */}
          <div className="flex-1 flex flex-col min-w-0">
            <div className="text-[10px] text-notion-muted uppercase tracking-wider mb-2">
              分类分布 · {totalCategoryCount}
            </div>
            <div className="h-[280px] relative">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={categoryData}
                    cx="50%"
                    cy="50%"
                    innerRadius={45}
                    outerRadius={75}
                    paddingAngle={1}
                    dataKey="value"
                    startAngle={90}
                    endAngle={-270}
                    onClick={(data) => data?.name && handleCategoryClick(data.name)}
                    className="cursor-pointer"
                    label={({ name, value, cx, cy, midAngle, outerRadius, index, percent }: any) => {
                      // 只显示前6大分类的标签
                      if (index >= 6) return null;
                      const RADIAN = Math.PI / 180;
                      const radius = outerRadius + 18;
                      const x = cx + radius * Math.cos(-midAngle * RADIAN);
                      const y = cy + radius * Math.sin(-midAngle * RADIAN);
                      return (
                        <text
                          x={x}
                          y={y}
                          fill="#37352F"
                          textAnchor={x > cx ? 'start' : 'end'}
                          dominantBaseline="central"
                          fontSize={9}
                          fontWeight={500}
                        >
                          {name} {(percent * 100).toFixed(0)}%
                        </text>
                      );
                    }}
                    labelLine={((props: any) => props.index < 6) as any}
                  >
                    {categoryData.map((entry, index) => (
                      <Cell
                        key={`cell-${index}`}
                        fill={entry.fill}
                        stroke={selectedCategory === entry.name ? entry.stroke : 'white'}
                        strokeWidth={selectedCategory === entry.name ? 2 : 1}
                        className="transition-all duration-150 hover:opacity-80"
                      />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      background: 'white',
                      border: '1px solid #E9E9E7',
                      borderRadius: '6px',
                      fontSize: '12px',
                      padding: '8px 12px',
                      boxShadow: '0 2px 8px rgba(0,0,0,0.12)',
                    }}
                    formatter={(value: number, _: string, props: any) => [
                      `${value} (${props.payload.percentage}%)`,
                      props.payload.name,
                    ]}
                  />
                </PieChart>
              </ResponsiveContainer>
              {/* 中心数字 */}
              <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                <span className="text-lg font-semibold text-notion-text">
                  {data?.total_messages || 0}
                </span>
                <span className="text-[9px] text-notion-muted uppercase tracking-wider">
                  消息
                </span>
              </div>
            </div>

            {/* 分类图例 - 两列布局 */}
            <div className="mt-4 grid grid-cols-2 gap-x-3 gap-y-1.5 overflow-y-auto scrollbar-thin max-h-[100px]">
              {categoryData.map((item) => (
                <button
                  key={item.name}
                  onClick={() => handleCategoryClick(item.name)}
                  className={`
                    flex items-center gap-2 px-1.5 py-0.5 rounded text-left transition-colors
                    ${selectedCategory === item.name ? 'bg-notion-hover' : 'hover:bg-notion-hover/50'}
                  `}
                >
                  <span
                    className="w-2 h-2 rounded-full shrink-0"
                    style={{ backgroundColor: item.stroke }}
                  />
                  <span className="text-[10px] text-notion-text truncate">{item.name}</span>
                </button>
              ))}
            </div>
          </div>

          {/* 分隔线 */}
          <div className="w-px bg-notion-border shrink-0" />

          {/* 右侧：关键词排行 */}
          <div className="flex-1 flex flex-col min-w-0">
            <div className="text-[10px] text-notion-muted uppercase tracking-wider mb-2">
              {selectedCategory ? `${selectedCategory} · Top Keywords` : 'Top Keywords'}
            </div>
            <div className="flex-1 min-h-0">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  layout="vertical"
                  data={keywordData}
                  margin={{ top: 0, right: 50, left: 0, bottom: 0 }}
                >
                  <XAxis type="number" hide />
                  <YAxis
                    dataKey="text"
                    type="category"
                    width={60}
                    tick={{ fontSize: 10, fill: '#37352F' }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <Tooltip
                    cursor={{ fill: '#F7F7F5' }}
                    contentStyle={{
                      background: 'white',
                      border: '1px solid #E9E9E7',
                      borderRadius: '4px',
                      fontSize: '11px',
                      padding: '6px 10px',
                    }}
                    formatter={(value: number, _: string, props: any) => [
                      `${value} (${props.payload.percentage}%) · ${props.payload.category}`,
                      '',
                    ]}
                  />
                  <Bar dataKey="value" radius={[0, 3, 3, 0]} barSize={14}>
                    {keywordData.map((entry, index) => (
                      <Cell
                        key={`cell-${index}`}
                        fill={entry.fill}
                        stroke={entry.stroke}
                        strokeWidth={1}
                      />
                    ))}
                    <LabelList
                      dataKey="value"
                      position="right"
                      fontSize={9}
                      fill="#9B9A97"
                      formatter={(value: number, entry?: any) => {
                        if (!entry) return String(value);
                        const percentage = entry.percentage ?? 0;
                        return `${value} (${percentage}%)`;
                      }}
                    />
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
        )}
      </div>

      {/* 底部洞察 */}
      {!loading && !error && data && data.category_distribution.length > 0 && (
        <div className="mt-3 pt-3 border-t border-notion-border">
          {/* TOP 3 分类 */}
          <div className="mb-2">
            <span className="text-[11px] text-notion-text font-medium">TOP 3 分类：</span>
            <span className="text-[11px] text-notion-muted">
              {data.category_distribution.slice(0, 3).map((cat, idx) => (
                <span key={cat.name}>
                  {idx > 0 && '、'}
                  <span className="text-notion-text">{cat.name}</span>
                  {' '}({cat.percentage}%)
                </span>
              ))}
            </span>
          </div>
          {/* TOP 5 关键词 */}
          <div>
            <span className="text-[11px] text-notion-text font-medium">TOP 5 关键词：</span>
            <span className="text-[11px] text-notion-muted">
              {data.keywords.slice(0, 5).map((kw, idx) => (
                <span key={kw.text}>
                  {idx > 0 && '、'}
                  <span className="text-notion-text">{kw.text}</span>
                  {' '}({kw.percentage}%)
                </span>
              ))}
            </span>
          </div>
        </div>
      )}
    </NotionCard>
  );
};
