/**
 * 数据验证相关常量
 */

export const VALIDATION = {
  /** 用户昵称最大长度 */
  MAX_NICK_LENGTH: 255,

  /** 搜索关键词最大长度 */
  MAX_SEARCH_LENGTH: 100,

  /** 搜索关键词最小长度 */
  MIN_SEARCH_LENGTH: 1,

  /** 文本域最大长度 */
  MAX_TEXT_LENGTH: 5000,

  /** URL最大长度 */
  MAX_URL_LENGTH: 2048,

  /** 电话号码最大长度 */
  MAX_PHONE_LENGTH: 20,

  /** 邮箱最大长度 */
  MAX_EMAIL_LENGTH: 255,
} as const;

/**
 * 验证规则正则表达式
 */
export const REGEX = {
  /** 邮箱验证 */
  EMAIL: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,

  /** 手机号（中国） */
  PHONE_CN: /^1[3-9]\d{9}$/,

  /** 用户昵称（允许中英文、数字、下划线） */
  NICKNAME: /^[\u4e00-\u9fa5a-zA-Z0-9_]+$/,

  /** URL */
  URL: /^https?:\/\/.+/,
} as const;

/**
 * 验证函数
 */
export const validators = {
  /**
   * 验证邮箱
   */
  isEmail: (value: string): boolean => REGEX.EMAIL.test(value),

  /**
   * 验证手机号
   */
  isPhone: (value: string): boolean => REGEX.PHONE_CN.test(value),

  /**
   * 验证用户昵称
   */
  isNickname: (value: string): boolean =>
    REGEX.NICKNAME.test(value) &&
    value.length > 0 &&
    value.length <= VALIDATION.MAX_NICK_LENGTH,

  /**
   * 验证搜索关键词
   */
  isSearchTerm: (value: string): boolean =>
    value.length >= VALIDATION.MIN_SEARCH_LENGTH &&
    value.length <= VALIDATION.MAX_SEARCH_LENGTH,

  /**
   * 验证 URL
   */
  isURL: (value: string): boolean => REGEX.URL.test(value),

  /**
   * 验证字符串长度
   */
  isValidLength: (
    value: string,
    min: number,
    max: number
  ): boolean => value.length >= min && value.length <= max,
};
