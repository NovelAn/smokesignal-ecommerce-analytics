/**
 * useAIAnalysis Hook - 异步AI分析轮询
 * 自动处理AI分析任务，支持轮询和超时
 */

import { useState, useCallback, useRef } from 'react';

export type TaskStatus = 'pending' | 'processing' | 'completed' | 'failed';

export interface AIAnalysisResult {
  task_id: string;
  status: TaskStatus;
  created_at?: string;
  started_at?: string;
  completed_at?: string;
  result?: {
    summary: string;
    key_interests: string[];
    pain_points: string[];
    recommended_action: string;
    confidence_level: string;
    analysis_method: string;
    evidence?: any;
  };
  error?: string;
  buyer_nick?: string;
}

export interface UseAIAnalysisReturn {
  startAnalysis: (userNick: string) => Promise<string>;
  taskStatus: TaskStatus | null;
  result: AIAnalysisResult | null;
  isLoading: boolean;
  error: string | null;
  reset: () => void;
}

const POLL_INTERVAL = 2000; // 轮询间隔：2秒
const MAX_POLL_TIME = 120000; // 最大轮询时间：2分钟

export function useAIAnalysis(): UseAIAnalysisReturn {
  const [taskStatus, setTaskStatus] = useState<TaskStatus | null>(null);
  const [result, setResult] = useState<AIAnalysisResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const pollingTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);

  /**
   * 轮询任务状态
   */
  const pollTaskStatus = useCallback(async (taskId: string): Promise<void> => {
    try {
      const response = await fetch(`http://localhost:8000/api/v2/tasks/${taskId}`);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data: AIAnalysisResult = await response.json();

      setTaskStatus(data.status);
      setResult(data);

      // 检查是否完成
      if (data.status === 'completed' || data.status === 'failed') {
        setIsLoading(false);
        stopPolling();

        if (data.status === 'failed') {
          setError(data.error || 'AI分析失败');
        } else {
          setError(null);
        }
      }
    } catch (err) {
      console.error('[useAIAnalysis] 轮询失败:', err);
      setError(err instanceof Error ? err.message : '轮询失败');
      setIsLoading(false);
      stopPolling();
    }
  }, []);

  /**
   * 开始轮询
   */
  const startPolling = useCallback((taskId: string) => {
    // 立即查询一次
    pollTaskStatus(taskId);

    // 设置轮询
    pollingIntervalRef.current = setInterval(() => {
      pollTaskStatus(taskId);
    }, POLL_INTERVAL);

    // 设置超时
    pollingTimeoutRef.current = setTimeout(() => {
      console.error('[useAIAnalysis] 轮询超时');
      setError('AI分析超时，请稍后重试');
      setIsLoading(false);
      stopPolling();
    }, MAX_POLL_TIME);
  }, [pollTaskStatus]);

  /**
   * 停止轮询
   */
  const stopPolling = useCallback(() => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }
    if (pollingTimeoutRef.current) {
      clearTimeout(pollingTimeoutRef.current);
      pollingTimeoutRef.current = null;
    }
  }, []);

  /**
   * 启动AI分析
   */
  const startAnalysis = useCallback(async (userNick: string): Promise<string> => {
    try {
      // 重置状态
      setIsLoading(true);
      setError(null);
      setResult(null);
      setTaskStatus(null);

      // 停止之前的轮询
      stopPolling();

      // 调用异步分析API
      const response = await fetch(
        `http://localhost:8000/api/v2/buyers/${encodeURIComponent(userNick)}/analyze-async`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
        }
      );

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      const taskId = data.task_id;

      // 开始轮询
      startPolling(taskId);

      return taskId;
    } catch (err) {
      console.error('[useAIAnalysis] 启动分析失败:', err);
      setError(err instanceof Error ? err.message : '启动分析失败');
      setIsLoading(false);
      throw err;
    }
  }, [startPolling, stopPolling]);

  /**
   * 重置状态
   */
  const reset = useCallback(() => {
    stopPolling();
    setTaskStatus(null);
    setResult(null);
    setIsLoading(false);
    setError(null);
  }, [stopPolling]);

  return {
    startAnalysis,
    taskStatus,
    result,
    isLoading,
    error,
    reset,
  };
}

/**
 * 示例用法：
 *
 * function BuyerProfile({ userNick }) {
 *   const { startAnalysis, taskStatus, result, isLoading, error } = useAIAnalysis();
 *
 *   const handleAnalyze = async () => {
 *     try {
 *       await startAnalysis(userNick);
 *     } catch (err) {
 *       console.error('启动分析失败:', err);
 *     }
 *   };
 *
 *   return (
 *     <div>
 *       <button onClick={handleAnalyze} disabled={isLoading}>
 *         {isLoading ? '分析中...' : 'AI分析'}
 *       </button>
 *
 *       {taskStatus === 'pending' && <p>任务排队中...</p>}
 *       {taskStatus === 'processing' && <p>AI分析中...</p>}
 *
 *       {result?.status === 'completed' && (
 *         <div>
 *           <h3>分析结果</h3>
 *           <p>{result.result?.summary}</p>
 *         </div>
 *       )}
 *
 *       {error && <p className="error">{error}</p>}
 *     </div>
 *   );
 * }
 */
