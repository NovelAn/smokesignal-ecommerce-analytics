/**
 * 情感和意图分析图表组件
 *
 * 包含三个图表：
 * - 情感趋势（7天）
 * - 意图分布（雷达图）
 * - 高峰时段（柱状图）
 */

import React from 'react';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { TrendingUp, Users, Clock } from 'lucide-react';
import { NotionCard } from '../common/NotionCard';

// TODO: 这些数据应该从 API 获取，当前使用占位数据
const DAILY_STATS = [
  { date: 'Mon', sentimentScore: 0.65 },
  { date: 'Tue', sentimentScore: 0.72 },
  { date: 'Wed', sentimentScore: 0.68 },
  { date: 'Thu', sentimentScore: 0.75 },
  { date: 'Fri', sentimentScore: 0.80 },
  { date: 'Sat', sentimentScore: 0.77 },
  { date: 'Sun', sentimentScore: 0.70 },
];

const INTENT_DISTRIBUTION = [
  { subject: 'Pre-sale', A: 120, B: 110, fullMark: 150 },
  { subject: 'Post-sale', A: 98, B: 130, fullMark: 150 },
  { subject: 'Logistics', A: 86, B: 130, fullMark: 150 },
  { subject: 'Usage Guide', A: 99, B: 100, fullMark: 150 },
  { subject: 'Complaint', A: 85, B: 90, fullMark: 150 },
  { subject: 'Inquiry', A: 65, B: 85, fullMark: 150 },
];

const HOURLY_ACTIVITY = [
  { hour: '9AM', value: 30 },
  { hour: '10AM', value: 45 },
  { hour: '11AM', value: 60 },
  { hour: '12PM', value: 40 },
  { hour: '1PM', value: 35 },
  { hour: '2PM', value: 50 },
  { hour: '3PM', value: 65 },
  { hour: '4PM', value: 55 },
  { hour: '5PM', value: 40 },
  { hour: '6PM', value: 25 },
  { hour: '7PM', value: 20 },
  { hour: '8PM', value: 15 },
];

interface SentimentChartsProps {
  timeRange?: '7d' | '15d' | '30d' | '90d' | '1y';
}

/**
 * 情感和意图图表组合
 */
export const SentimentCharts: React.FC<SentimentChartsProps> = ({ timeRange = '1y' }) => {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* 情感趋势图 */}
      <SentimentTrendChart />

      {/* 意图分布图 */}
      <IntentDistributionChart />

      {/* 高峰时段图 */}
      <PeakHoursChart />
    </div>
  );
};

/**
 * 情感趋势图（7天）
 */
const SentimentTrendChart: React.FC = () => {
  return (
    <NotionCard title="Sentiment Trend (7 Days)" icon={TrendingUp} className="h-80">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={DAILY_STATS}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E9E9E7" vertical={false} />
          <XAxis
            dataKey="date"
            stroke="#9B9A97"
            tick={{ fill: '#9B9A97', fontSize: 10 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            stroke="#9B9A97"
            tick={{ fill: '#9B9A97', fontSize: 10 }}
            domain={[0, 1]}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            contentStyle={{ backgroundColor: '#fff', borderColor: '#E9E9E7' }}
          />
          <Line
            type="monotone"
            dataKey="sentimentScore"
            stroke="#EA580C"
            strokeWidth={2}
            dot={{ fill: '#fff', stroke: '#EA580C', strokeWidth: 2 }}
            activeDot={{ r: 4 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </NotionCard>
  );
};

/**
 * 意图分布雷达图
 */
const IntentDistributionChart: React.FC = () => {
  return (
    <NotionCard title="Intent Distribution" icon={Users} className="h-80">
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart cx="50%" cy="50%" outerRadius="70%" data={INTENT_DISTRIBUTION}>
          <PolarGrid stroke="#E9E9E7" />
          <PolarAngleAxis
            dataKey="subject"
            tick={{ fill: '#37352F', fontSize: 10 }}
          />
          <PolarRadiusAxis
            angle={30}
            domain={[0, 150]}
            tick={false}
            axisLine={false}
          />
          <Radar
            name="Intents"
            dataKey="A"
            stroke="#F59E0B"
            fill="#F59E0B"
            fillOpacity={0.4}
          />
          <Tooltip
            contentStyle={{ backgroundColor: '#fff', borderColor: '#E9E9E7' }}
          />
        </RadarChart>
      </ResponsiveContainer>
    </NotionCard>
  );
};

/**
 * 高峰时段柱状图
 */
const PeakHoursChart: React.FC = () => {
  return (
    <NotionCard title="Peak Hours" icon={Clock} className="h-80">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={HOURLY_ACTIVITY}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E9E9E7" vertical={false} />
          <XAxis
            dataKey="hour"
            stroke="#9B9A97"
            tick={{ fill: '#9B9A97', fontSize: 10 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            stroke="#9B9A97"
            tick={{ fill: '#9B9A97', fontSize: 10 }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            cursor={{ fill: '#F7F7F5' }}
            contentStyle={{ backgroundColor: '#fff', borderColor: '#E9E9E7' }}
          />
          <Bar
            dataKey="value"
            fill="#9B9A97"
            radius={[2, 2, 0, 0]}
            activeBar={{ fill: '#37352F' }}
          />
        </BarChart>
      </ResponsiveContainer>
    </NotionCard>
  );
};
