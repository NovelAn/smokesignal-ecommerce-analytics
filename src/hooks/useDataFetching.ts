/**
 * 数据获取Hook
 * 封装常用的数据获取逻辑，包括加载状态、错误处理、重试等
 */
import { useState, useEffect } from 'react';

interface UseDataFetchingResult<T> {
  data: T | null;
  isLoading: boolean;
  error: string | null;
  refetch: () => void;
}

/**
 * 通用数据获取Hook
 */
export function useDataFetching<T>(
  fetchFn: () => Promise<T>,
  dependencies: any[] = []
): UseDataFetchingResult<T> {
  const [data, setData] = useState<T | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const result = await fetchFn();
      setData(result);
    } catch (err: any) {
      console.error('Data fetching error:', err);
      setError(err.message || '加载数据失败');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, dependencies);

  return { data, isLoading, error, refetch: fetchData };
}

/**
 * 带自动重试的数据获取Hook
 */
export function useDataFetchingWithRetry<T>(
  fetchFn: () => Promise<T>,
  retries = 2,
  dependencies: any[] = []
): UseDataFetchingResult<T> {
  const [data, setData] = useState<T | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async (attempt = 0) => {
    try {
      setIsLoading(true);
      setError(null);
      const result = await fetchFn();
      setData(result);
    } catch (err: any) {
      console.error(`Data fetching error (attempt ${attempt + 1}):`, err);

      if (attempt < retries) {
        console.log(`Retrying... (${attempt + 1}/${retries})`);
        setTimeout(() => fetchData(attempt + 1), 1000 * (attempt + 1)); // 递增延迟
      } else {
        setError(err.message || '加载数据失败，请稍后重试');
      }
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, dependencies);

  return { data, isLoading, error, refetch: () => fetchData() };
}
