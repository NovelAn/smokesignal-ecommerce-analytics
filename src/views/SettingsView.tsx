import React, { useState, useEffect } from 'react';
import { Terminal, Play, RefreshCw, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import { apiClient, BatchAnalysisStatus, SentimentSummary } from '../api/client';

const SettingsView: React.FC = () => {
  const [batchStatus, setBatchStatus] = useState<BatchAnalysisStatus | null>(null);
  const [sentimentSummary, setSentimentSummary] = useState<SentimentSummary | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isPolling, setIsPolling] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 加载情感分析汇总
  useEffect(() => {
    loadSentimentSummary();
  }, []);

  // 轮询任务状态
  useEffect(() => {
    if (!isPolling || !batchStatus?.task_id) return;

    const interval = setInterval(async () => {
      try {
        const status = await apiClient.getBatchAnalysisStatus(batchStatus.task_id);
        setBatchStatus(status);

        if (status.status === 'completed' || status.status === 'failed' || status.status === 'cancelled') {
          setIsPolling(false);
          // 刷新汇总数据
          loadSentimentSummary();
        }
      } catch (err) {
        console.error('Failed to poll task status:', err);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [isPolling, batchStatus?.task_id]);

  const loadSentimentSummary = async () => {
    try {
      const summary = await apiClient.getSentimentSummary();
      setSentimentSummary(summary);
    } catch (err) {
      console.error('Failed to load sentiment summary:', err);
    }
  };

  const handleStartBatchAnalysis = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await apiClient.startBatchAnalysis(200);
      setBatchStatus({
        task_id: response.task_id,
        status: 'pending',
        total_buyers: 0,
        processed_buyers: 0,
        skipped_buyers: 0,
        failed_buyers: 0,
        progress_percent: 0,
        started_at: null,
        completed_at: null,
        error_message: null,
      });
      setIsPolling(true);
    } catch (err: any) {
      setError(err.message || '启动批量分析失败');
    } finally {
      setIsLoading(false);
    }
  };

  const getStatusIcon = () => {
    if (!batchStatus) return null;

    switch (batchStatus.status) {
      case 'pending':
        return <Loader2 className="w-4 h-4 animate-spin text-blue-500" />;
      case 'running':
        return <Loader2 className="w-4 h-4 animate-spin text-blue-500" />;
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'failed':
        return <AlertCircle className="w-4 h-4 text-red-500" />;
      default:
        return null;
    }
  };

  const getStatusText = () => {
    if (!batchStatus) return null;

    switch (batchStatus.status) {
      case 'pending':
        return '等待中...';
      case 'running':
        return `分析中... ${batchStatus.processed_buyers}/${batchStatus.total_buyers}`;
      case 'completed':
        return `完成! 已分析 ${batchStatus.processed_buyers} 个客户`;
      case 'failed':
        return `失败: ${batchStatus.error_message}`;
      case 'cancelled':
        return '已取消';
      default:
        return batchStatus.status;
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-8">
      {/* Pipeline Configuration */}
      <div>
        <h2 className="text-2xl font-serif text-notion-text mb-4">Pipeline Configuration</h2>
        <div className="bg-notion-bg border border-notion-border rounded-sm p-6 shadow-sm">
          <div className="flex items-start gap-4">
            <div className="p-2 bg-green-50 rounded text-green-700">
              <Terminal size={20} />
            </div>
            <div>
              <h3 className="font-medium text-notion-text">ETL Script Status</h3>
              <p className="text-sm text-notion-muted mt-1 leading-relaxed">
                Playwright crawler active. Targeting Qianniu Workbench.<br />
                Next scheduled run: 02:00 AM CST.
              </p>
              <div className="mt-4 flex items-center gap-2 text-xs font-mono text-notion-muted bg-notion-sidebar p-2 rounded border border-notion-border">
                <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
                Connected to PostgreSQL DB
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* AI Batch Analysis */}
      <div>
        <h2 className="text-2xl font-serif text-notion-text mb-4">AI Analysis</h2>
        <div className="bg-notion-bg border border-notion-border rounded-sm p-6 shadow-sm">
          <div className="flex items-start gap-4">
            <div className="p-2 bg-purple-50 rounded text-purple-700">
              <RefreshCw size={20} />
            </div>
            <div className="flex-1">
              <h3 className="font-medium text-notion-text">Batch Sentiment & Intent Analysis</h3>
              <p className="text-sm text-notion-muted mt-1 leading-relaxed">
                Analyze customer sentiment and intent from chat records.
                Only customers with 5+ messages will be analyzed.
              </p>

              {/* Sentiment Summary */}
              {sentimentSummary && sentimentSummary.total_analyzed > 0 && (
                <div className="mt-4 grid grid-cols-4 gap-2 text-xs">
                  <div className="bg-notion-sidebar p-2 rounded border border-notion-border text-center">
                    <div className="text-notion-muted">Total</div>
                    <div className="font-medium text-notion-text">{sentimentSummary.total_analyzed}</div>
                  </div>
                  <div className="bg-green-50 p-2 rounded border border-green-200 text-center">
                    <div className="text-green-600">Positive</div>
                    <div className="font-medium text-green-700">{sentimentSummary.distribution_percent.positive}%</div>
                  </div>
                  <div className="bg-gray-50 p-2 rounded border border-gray-200 text-center">
                    <div className="text-gray-600">Neutral</div>
                    <div className="font-medium text-gray-700">{sentimentSummary.distribution_percent.neutral}%</div>
                  </div>
                  <div className="bg-red-50 p-2 rounded border border-red-200 text-center">
                    <div className="text-red-600">Negative</div>
                    <div className="font-medium text-red-700">{sentimentSummary.distribution_percent.negative}%</div>
                  </div>
                </div>
              )}

              {/* Task Status */}
              {batchStatus && (
                <div className="mt-4 flex items-center gap-2 text-sm bg-notion-sidebar p-3 rounded border border-notion-border">
                  {getStatusIcon()}
                  <span className="text-notion-text">{getStatusText()}</span>
                  {batchStatus.status === 'running' && (
                    <div className="flex-1 ml-2">
                      <div className="h-2 bg-notion-border rounded-full overflow-hidden">
                        <div
                          className="h-full bg-blue-500 transition-all duration-300"
                          style={{ width: `${batchStatus.progress_percent}%` }}
                        />
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Error */}
              {error && (
                <div className="mt-4 flex items-center gap-2 text-sm text-red-600 bg-red-50 p-3 rounded border border-red-200">
                  <AlertCircle className="w-4 h-4" />
                  {error}
                </div>
              )}

              {/* Start Button */}
              <button
                onClick={handleStartBatchAnalysis}
                disabled={isLoading || isPolling}
                className="mt-4 flex items-center gap-2 px-4 py-2 bg-notion-text text-white rounded-sm hover:bg-gray-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
              >
                {isLoading || isPolling ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Play className="w-4 h-4" />
                )}
                {isLoading ? 'Starting...' : isPolling ? 'Analyzing...' : 'Start Batch Analysis'}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Dictionary Management */}
      <div>
        <h2 className="text-lg font-serif text-notion-text mb-3">Dictionary Management</h2>
        <textarea
          className="w-full h-40 bg-notion-bg border border-notion-border rounded-sm p-4 text-sm font-mono text-notion-text focus:outline-none focus:ring-1 focus:ring-gray-300"
          defaultValue={`# Keywords for NLP Tagging
glass, grinder, leak, broken, shipping
discount, wholesale, return, refund
flavor, taste, clean, resin
14mm, 18mm, bowl, stem`}
        />
      </div>
    </div>
  );
};

export default SettingsView;
