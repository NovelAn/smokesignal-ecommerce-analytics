/**
 * 统一日志工具
 *
 * 提供开发环境和生产环境不同的日志行为
 * 开发环境：输出详细日志
 * 生产环境：只输出错误日志，可上报到监控服务
 */

import config from '../config/env';

/**
 * 日志级别
 */
export enum LogLevel {
  DEBUG = 0,
  INFO = 1,
  WARN = 2,
  ERROR = 3,
}

/**
 * 日志配置
 */
interface LogConfig {
  level: LogLevel;
  enableTimestamp: boolean;
  enableStackTrace: boolean;
}

/**
 * Logger 类
 */
export class Logger {
  private config: LogConfig;

  constructor(config?: Partial<LogConfig>) {
    this.config = {
      level: config?.level ?? (config.enableDebugMode ? LogLevel.DEBUG : LogLevel.INFO),
      enableTimestamp: config?.enableTimestamp ?? true,
      enableStackTrace: config?.enableStackTrace ?? true,
    };
  }

  /**
   * 格式化日志消息
   */
  private formatMessage(level: string, message: string, ...args: any[]): string {
    const timestamp = this.config.enableTimestamp
      ? `[${new Date().toISOString()}]`
      : '';
    const prefix = `${timestamp} [${level}]`;
    return `${prefix} ${message}`;
  }

  /**
   * 输出日志
   */
  private log(
    level: LogLevel,
    levelName: string,
    message: string,
    ...args: any[]
  ): void {
    // 检查日志级别
    if (level < this.config.level) {
      return;
    }

    const formattedMessage = this.formatMessage(levelName, message);

    switch (level) {
      case LogLevel.DEBUG:
      case LogLevel.INFO:
        console.log(formattedMessage, ...args);
        break;
      case LogLevel.WARN:
        console.warn(formattedMessage, ...args);
        break;
      case LogLevel.ERROR:
        console.error(formattedMessage, ...args);

        // 生产环境可以上报到监控服务
        if (config.enableErrorTracking && level === LogLevel.ERROR) {
          this.reportToErrorTracking(message, args);
        }
        break;
    }

    // 如果启用堆栈跟踪，在开发环境显示
    if (this.config.enableStackTrace && level >= LogLevel.WARN) {
      console.trace('Call stack:');
    }
  }

  /**
   * 上报错误到监控服务（占位符）
   * TODO: 集成 Sentry 或其他错误监控服务
   */
  private reportToErrorTracking(message: string, args: any[]): void {
    // 示例：发送到错误追踪服务
    // Sentry.captureException(new Error(message), { extra: { args } });

    // 当前仅作为占位符
    if (config.enableDebugMode) {
      console.warn('[Error Tracking]', message, args);
    }
  }

  /**
   * DEBUG 级别日志
   */
  debug(message: string, ...args: any[]): void {
    this.log(LogLevel.DEBUG, 'DEBUG', message, ...args);
  }

  /**
   * INFO 级别日志
   */
  info(message: string, ...args: any[]): void {
    this.log(LogLevel.INFO, 'INFO', message, ...args);
  }

  /**
   * WARN 级别日志
   */
  warn(message: string, ...args: any[]): void {
    this.log(LogLevel.WARN, 'WARN', message, ...args);
  }

  /**
   * ERROR 级别日志
   */
  error(message: string, ...args: any[]): void {
    this.log(LogLevel.ERROR, 'ERROR', message, ...args);
  }

  /**
   * 分组日志开始
   */
  group(label: string): void {
    console.group(label);
  }

  /**
   * 分组日志结束
   */
  groupEnd(): void {
    console.groupEnd();
  }

  /**
   * 表格形式显示数据
   */
  table(data: any): void {
    console.table(data);
  }
}

/**
 * 创建全局 logger 实例
 */
export const logger = new Logger({
  level: import.meta.env.DEV ? LogLevel.DEBUG : LogLevel.INFO,
  enableTimestamp: true,
  enableStackTrace: import.meta.env.DEV,
});

/**
 * 简化的日志导出（便捷使用）
 */
export const log = {
  debug: (message: string, ...args: any[]) => logger.debug(message, ...args),
  info: (message: string, ...args: any[]) => logger.info(message, ...args),
  warn: (message: string, ...args: any[]) => logger.warn(message, ...args),
  error: (message: string, ...args: any[]) => logger.error(message, ...args),
  group: (label: string) => logger.group(label),
  groupEnd: () => logger.groupEnd(),
  table: (data: any) => logger.table(data),
};

export default logger;
