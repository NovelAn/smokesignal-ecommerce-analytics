/**
 * 环境变量配置管理
 *
 * 集中管理所有环境变量，提供类型安全和默认值
 * 在开发环境会验证必需的环境变量
 */

interface EnvConfig {
  // API 配置
  apiBaseUrl: string;
  apiTimeout: number;

  // 缓存配置
  enableCache: boolean;
  cacheTimeout: number;

  // 功能开关
  enableErrorTracking: boolean;
  enableDebugMode: boolean;

  // 应用信息
  appTitle: string;
  appVersion: string;
}

/**
 * 从环境变量读取配置，提供默认值
 */
const config: EnvConfig = {
  // API 配置
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL || '/api/v2',
  apiTimeout: Number(import.meta.env.VITE_API_TIMEOUT) || 30000,

  // 缓存配置
  enableCache: import.meta.env.VITE_ENABLE_CACHE === 'true',
  cacheTimeout: Number(import.meta.env.VITE_CACHE_TIMEOUT) || 300000, // 5分钟

  // 功能开关
  enableErrorTracking: import.meta.env.VITE_ENABLE_ERROR_TRACKING === 'true',
  enableDebugMode: import.meta.env.VITE_ENABLE_DEBUG_MODE === 'true',

  // 应用信息
  appTitle: import.meta.env.VITE_APP_TITLE || 'SmokeSignal Analytics',
  appVersion: import.meta.env.VITE_APP_VERSION || '1.0.0',
};

/**
 * 验证必需的环境变量
 * 在开发环境显示警告
 */
const validateEnv = () => {
  if (import.meta.env.DEV) {
    const warnings: string[] = [];

    // 检查推荐配置的变量
    if (!import.meta.env.VITE_API_BASE_URL) {
      warnings.push('VITE_API_BASE_URL (使用默认值: /api/v2)');
    }

    if (warnings.length > 0) {
      console.warn(
        '[Env Config] Missing recommended environment variables:\n' +
        warnings.map(w => `  - ${w}`).join('\n')
      );
    }

    // 开发环境显示配置信息
    console.group('[Env Config] Current Configuration');
    console.log('API Base URL:', config.apiBaseUrl);
    console.log('API Timeout:', config.apiTimeout);
    console.log('Cache Enabled:', config.enableCache);
    console.log('Cache Timeout:', config.cacheTimeout);
    console.log('Debug Mode:', config.enableDebugMode);
    console.groupEnd();
  }
};

// 在模块加载时验证
validateEnv();

/**
 * 导出配置对象（只读）
 */
export default config as Readonly<EnvConfig>;

/**
 * 导出配置类型，供其他模块使用
 */
export type { EnvConfig };
