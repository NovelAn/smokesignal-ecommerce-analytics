/**
 * 关键词和问题分析面板组件
 *
 * 显示：
 * - 问题分类分布（甜甜圈图）
 * - 热门关键词（柱状图）
 *
 * 注意：当前使用占位数据，等待后端API实现
 */

import React, { useState, useMemo } from 'react';
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LabelList,
} from 'recharts';
import { Database, XCircle, PieChart as PieChartIcon, BarChart as BarChartIcon, Lightbulb } from 'lucide-react';
import { NotionCard } from '../common/NotionCard';

type TimeRange = '7d' | '15d' | '30d' | '90d' | '1y';

interface KeywordAnalysisPanelProps {
  timeRange: TimeRange;
}

/**
 * 关键词分析面板
 */
export const KeywordAnalysisPanel: React.FC<KeywordAnalysisPanelProps> = ({ timeRange }) => {
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);

  // Cool Tone Palette (Blue, Cyan, Indigo, Slate) - Professional, Clean, Distinct
  const COOL_PALETTE = [
    '#3B82F6', // Blue 500 (Primary)
    '#0EA5E9', // Sky 500
    '#06B6D4', // Cyan 500
    '#6366F1', // Indigo 500
    '#64748B', // Slate 500 (Neutral Cool)
    '#8B5CF6', // Violet 500 (Accent)
  ];

  // ⚠️ 占位数据 - 后端API未实现，显示为0
  // TODO: 等待第四阶段开发完成后再替换为真实数据
  const { categoryData, keywordData, totalVolume } = useMemo(() => {
    // 创建空的分类数据（显示为0）
    const categoryDataList = [
      { name: 'Shipping', value: 0, fill: COOL_PALETTE[0] },
      { name: 'Specs', value: 0, fill: COOL_PALETTE[1] },
      { name: 'After-sales', value: 0, fill: COOL_PALETTE[2] },
      { name: 'Discount', value: 0, fill: COOL_PALETTE[3] },
      { name: 'Packaging', value: 0, fill: COOL_PALETTE[4] },
      { name: 'Gifted', value: 0, fill: COOL_PALETTE[5] },
    ];

    // 创建空的关键词数据（显示为0）
    const keywordDataList = [
      { text: 'Shipping Speed', value: 0, category: 'Shipping', fill: COOL_PALETTE[0] },
      { text: 'Product Quality', value: 0, category: 'Specs', fill: COOL_PALETTE[1] },
      { text: 'Return Policy', value: 0, category: 'After-sales', fill: COOL_PALETTE[2] },
      { text: 'Price', value: 0, category: 'Discount', fill: COOL_PALETTE[3] },
      { text: 'Packaging', value: 0, category: 'Packaging', fill: COOL_PALETTE[4] },
    ];

    return {
      categoryData: categoryDataList,
      keywordData: keywordDataList,
      totalVolume: 0
    };
  }, [timeRange, selectedCategory]);

  return (
    <NotionCard
        title="Keyword & Issue Analysis"
        icon={Database}
        className="h-[500px] flex flex-col"
        action={
            selectedCategory && (
                <button
                    onClick={() => setSelectedCategory(null)}
                    className="px-2 py-1 text-xs text-notion-muted hover:text-blue-600 border border-transparent hover:border-blue-200 rounded transition-colors flex items-center gap-1"
                >
                    <XCircle size={12}/> Clear Filter: {selectedCategory}
                </button>
            )
        }
    >
        <div className="flex flex-col lg:flex-row h-full gap-8">
            {/* Left: Category Distribution (Donut) */}
            <div className="flex-1 flex flex-col">
                <div className="flex items-center justify-between mb-2">
                    <h4 className="text-xs font-bold text-notion-muted uppercase tracking-wider flex items-center gap-2">
                        <PieChartIcon size={12} /> Categories Distribution
                    </h4>
                    <span className="px-2 py-1 bg-yellow-50 text-yellow-700 border border-yellow-200 rounded text-[10px] font-medium">
                        数据开发中 (Coming Soon)
                    </span>
                </div>
                <div className="flex-1 relative">
                    <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                            <Pie
                                data={categoryData}
                                cx="50%"
                                cy="50%"
                                innerRadius={60}
                                outerRadius={80}
                                paddingAngle={2}
                                dataKey="value"
                                onClick={(data) => setSelectedCategory(data.name === selectedCategory ? null : data.name)}
                                label={({ name, percent }) => percent > 0 ? `${name} ${(percent * 100).toFixed(0)}%` : ''}
                                labelLine={{ stroke: '#9B9A97', strokeWidth: 1 }}
                            >
                                {categoryData.map((entry, index) => (
                                    <Cell
                                        key={`cell-${index}`}
                                        fill={entry.fill}
                                        stroke={selectedCategory === entry.name ? '#1E3A8A' : 'none'}
                                        strokeWidth={selectedCategory === entry.name ? 2 : 0}
                                        className="cursor-pointer hover:opacity-80 transition-all"
                                    />
                                ))}
                            </Pie>
                            <Tooltip
                                contentStyle={{ backgroundColor: '#fff', borderColor: '#E9E9E7', borderRadius: '4px', fontSize: '12px' }}
                                itemStyle={{ color: '#37352F' }}
                                formatter={(value: number) => [`${value}`, 'Volume']}
                            />
                        </PieChart>
                    </ResponsiveContainer>
                    {/* Centered Label */}
                    <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                        <span className="text-2xl font-bold text-notion-muted">0</span>
                        <span className="text-[10px] text-notion-muted uppercase tracking-wider">Total</span>
                    </div>
                </div>
            </div>

            {/* Separator */}
            <div className="w-px bg-notion-border hidden lg:block my-4"></div>

            {/* Right: Top Keywords (Bar) */}
            <div className="flex-[1.2] flex flex-col">
                <div className="flex items-center justify-between mb-2">
                     <h4 className="text-xs font-bold text-notion-muted uppercase tracking-wider flex items-center gap-2">
                        <BarChartIcon size={12} />
                        {selectedCategory ? `${selectedCategory} Top Keywords` : 'Overall Top Keywords'}
                    </h4>
                </div>
                <div className="flex-1">
                    <ResponsiveContainer width="100%" height="100%">
                        <BarChart
                            layout="vertical"
                            data={keywordData}
                            margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                        >
                            <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#E9E9E7" />
                            <XAxis type="number" hide />
                            <YAxis
                                dataKey="text"
                                type="category"
                                width={100}
                                tick={{ fontSize: 11, fill: '#37352F' }}
                                axisLine={false}
                                tickLine={false}
                            />
                            <Tooltip
                                cursor={{ fill: '#F7F7F5' }}
                                contentStyle={{ backgroundColor: '#fff', borderColor: '#E9E9E7', borderRadius: '4px', fontSize: '12px' }}
                            />
                            <Bar dataKey="value" radius={[0, 4, 4, 0]} barSize={20} animationDuration={500}>
                                {keywordData.map((entry, index) => (
                                    <Cell key={`cell-${index}`} fill={entry.fill || '#9CA3AF'} />
                                ))}
                                <LabelList dataKey="value" position="right" fontSize={11} fill="#9CA3AF" />
                            </Bar>
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            </div>
        </div>

        {/* Insight Footer */}
        <div className="mt-4 pt-3 border-t border-notion-border flex items-start gap-3">
            <div className="p-1.5 bg-yellow-50 rounded text-yellow-600 shrink-0 mt-0.5">
                <Lightbulb size={14} />
            </div>
             <div className="text-xs text-notion-text">
                <span className="font-semibold text-yellow-800">数据开发中:</span>
                {' '}关键词分析功能正在开发中，将在第四阶段完成。届时将展示客户聊天中的关键词频率、问题类型分布等数据。
            </div>
        </div>
    </NotionCard>
  );
};
