/**
 * 防抖 Hook
 *
 * 用于延迟执行函数，常用于搜索框等场景
 * 避免频繁触发请求，提升性能
 */

import { useState, useEffect } from 'react';

/**
 * 防抖 Hook
 * @param value 需要防抖的值
 * @param delay 延迟时间（毫秒），默认 500ms
 * @returns 防抖后的值
 */
export function useDebounce<T>(value: T, delay = 500): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    // 设置定时器
    const timer = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    // 清理函数：在 value 或 delay 变化时取消之前的定时器
    return () => {
      clearTimeout(timer);
    };
  }, [value, delay]);

  return debouncedValue;
}

/**
 * 防抖函数 Hook
 * 返回一个防抖后的函数
 * @param fn 需要防抖的函数
 * @param delay 延迟时间（毫秒），默认 500ms
 * @returns 防抖后的函数
 */
export function useDebouncedFn<T extends (...args: any[]) => any>(
  fn: T,
  delay = 500
): T {
  return ((...args: Parameters<T>) => {
    // 这里可以使用 lodash 的 debounce，或者简单实现
    // 为了避免额外依赖，建议使用 useDebounce 处理值
    // 或者直接在组件中使用 lodash.debounce

    // 简单实现：
    const timeoutRef = { current: null as NodeJS.Timeout | null };

    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }

    timeoutRef.current = setTimeout(() => {
      fn(...args);
    }, delay);
  }) as T;
}

/**
 * 节流 Hook
 * @param value 需要节流的值
 * @param delay 间隔时间（毫秒），默认 500ms
 * @returns 节流后的值
 */
export function useThrottle<T>(value: T, delay = 500): T {
  const [throttledValue, setThrottledValue] = useState<T>(value);
  const lastExecuted = useState(Date.now())[0];

  useEffect(() => {
    const now = Date.now();
    const timeSinceLastExecution = now - lastExecuted;

    if (timeSinceLastExecution > delay) {
      setThrottledValue(value);
    } else {
      const timer = setTimeout(() => {
        setThrottledValue(value);
      }, delay - timeSinceLastExecution);

      return () => clearTimeout(timer);
    }
  }, [value, delay, lastExecuted]);

  return throttledValue;
}
