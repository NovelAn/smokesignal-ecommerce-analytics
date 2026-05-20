import React, { useMemo } from 'react';
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
import { TrendingUp, Users, Activity } from 'lucide-react';
import { NotionCard } from '../common/NotionCard';
import { apiClient, BuyersListResponse } from '../../api/client';
import { useDataFetchingWithRetry } from '../../hooks/useDataFetching';

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

type TimeRange = '7d' | '15d' | '30d' | '90d' | '1y';

interface SentimentChartsProps {
  timeRange?: TimeRange;
}

export const SentimentCharts: React.FC<SentimentChartsProps> = ({ timeRange = '1y' }) => {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <SentimentTrendChart />
      <IntentDistributionChart />
      <VICActivityChart timeRange={timeRange} />
    </div>
  );
};

const SentimentTrendChart: React.FC = () => {
  return (
    <NotionCard title="Sentiment Trend (7 Days)" icon={TrendingUp} className="h-80">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={DAILY_STATS}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E9E9E7" vertical={false} />
          <XAxis dataKey="date" stroke="#9B9A97" tick={{ fill: '#9B9A97', fontSize: 10 }} axisLine={false} tickLine={false} />
          <YAxis stroke="#9B9A97" tick={{ fill: '#9B9A97', fontSize: 10 }} domain={[0, 1]} axisLine={false} tickLine={false} />
          <Tooltip contentStyle={{ backgroundColor: '#fff', borderColor: '#E9E9E7' }} />
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

const IntentDistributionChart: React.FC = () => {
  return (
    <NotionCard title="Intent Distribution" icon={Users} className="h-80">
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart cx="50%" cy="50%" outerRadius="70%" data={INTENT_DISTRIBUTION}>
          <PolarGrid stroke="#E9E9E7" />
          <PolarAngleAxis dataKey="subject" tick={{ fill: '#37352F', fontSize: 10 }} />
          <PolarRadiusAxis angle={30} domain={[0, 150]} tick={false} axisLine={false} />
          <Radar name="Intents" dataKey="A" stroke="#F59E0B" fill="#F59E0B" fillOpacity={0.4} />
          <Tooltip contentStyle={{ backgroundColor: '#fff', borderColor: '#E9E9E7' }} />
        </RadarChart>
      </ResponsiveContainer>
    </NotionCard>
  );
};

const VICActivityChart: React.FC<{ timeRange: TimeRange }> = ({ timeRange }) => {
  const rangeStart = useMemo(() => getRangeStartDate(timeRange), [timeRange]);
  const { data, isLoading, error } = useDataFetchingWithRetry<BuyersListResponse>(
    () => apiClient.getBuyers({
      buyer_type: 'VIC',
      sort_by: 'last_purchase',
      last_purchase_after: rangeStart,
      limit: 1000,
    }),
    1,
    [rangeStart]
  );

  const activityData = useMemo(() => {
    const buyers = data?.buyers || [];
    return buildActivityBuckets(buyers.map((buyer) => buyer.last_purchase_date), timeRange);
  }, [data, timeRange]);

  return (
    <NotionCard title="VIC Activity" subtitle={formatRangeLabel(timeRange)} icon={Activity} className="h-80">
      {error ? (
        <div className="h-full flex items-center justify-center text-xs text-red-600">Failed to load VIC activity</div>
      ) : isLoading ? (
        <div className="h-full flex items-center justify-center text-xs text-notion-muted">Loading activity...</div>
      ) : (
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={activityData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#E9E9E7" vertical={false} />
            <XAxis dataKey="label" stroke="#9B9A97" tick={{ fill: '#9B9A97', fontSize: 10 }} axisLine={false} tickLine={false} />
            <YAxis stroke="#9B9A97" tick={{ fill: '#9B9A97', fontSize: 10 }} axisLine={false} tickLine={false} allowDecimals={false} />
            <Tooltip
              cursor={{ fill: '#F7F7F5' }}
              contentStyle={{ backgroundColor: '#fff', borderColor: '#E9E9E7' }}
              formatter={(value: number) => [value, 'Active VICs']}
            />
            <Bar dataKey="activeVics" fill="#2563EB" radius={[2, 2, 0, 0]} activeBar={{ fill: '#1D4ED8' }} />
          </BarChart>
        </ResponsiveContainer>
      )}
    </NotionCard>
  );
};

const getRangeStartDate = (timeRange: TimeRange) => {
  const date = new Date();
  const daysByRange: Record<TimeRange, number> = {
    '7d': 7,
    '15d': 15,
    '30d': 30,
    '90d': 90,
    '1y': 365,
  };
  date.setDate(date.getDate() - daysByRange[timeRange]);
  return date.toISOString().split('T')[0];
};

const formatRangeLabel = (timeRange: TimeRange) => {
  const labels: Record<TimeRange, string> = {
    '7d': 'Last 7 days',
    '15d': 'Last 15 days',
    '30d': 'Last 30 days',
    '90d': 'Last 90 days',
    '1y': 'Last 1 year',
  };
  return labels[timeRange];
};

const buildActivityBuckets = (dates: string[], timeRange: TimeRange) => {
  const bucketCount = timeRange === '1y' ? 12 : timeRange === '90d' ? 6 : 7;
  const now = new Date();
  const start = new Date(getRangeStartDate(timeRange));
  const spanMs = Math.max(1, now.getTime() - start.getTime());
  const bucketMs = spanMs / bucketCount;

  const buckets = Array.from({ length: bucketCount }, (_, index) => {
    const bucketStart = new Date(start.getTime() + bucketMs * index);
    const bucketEnd = new Date(start.getTime() + bucketMs * (index + 1));
    return {
      label: formatBucketLabel(bucketStart, bucketEnd, timeRange),
      activeVics: 0,
    };
  });

  dates.forEach((rawDate) => {
    const date = new Date(rawDate);
    if (Number.isNaN(date.getTime()) || date < start || date > now) return;
    const index = Math.min(bucketCount - 1, Math.floor((date.getTime() - start.getTime()) / bucketMs));
    buckets[index].activeVics += 1;
  });

  return buckets;
};

const formatBucketLabel = (start: Date, end: Date, timeRange: TimeRange) => {
  if (timeRange === '1y') {
    return start.toLocaleString(undefined, { month: 'short' });
  }
  const startLabel = `${start.getMonth() + 1}/${start.getDate()}`;
  const endLabel = `${end.getMonth() + 1}/${end.getDate()}`;
  return `${startLabel}-${endLabel}`;
};
