/**
 * 分页相关常量
 */

export const PAGINATION = {
  /** 默认每页数量 */
  DEFAULT_LIMIT: 100,

  /** 最大每页数量 */
  MAX_LIMIT: 1000,

  /** 默认偏移量 */
  DEFAULT_OFFSET: 0,

  /** 分页选项（下拉框） */
  LIMIT_OPTIONS: [10, 20, 50, 100, 200, 500],

  /** 移动端默认每页数量 */
  MOBILE_DEFAULT_LIMIT: 20,
} as const;

/**
 * 分页参数类型
 */
export interface PaginationParams {
  limit?: number;
  offset?: number;
  page?: number; // 页码（从1开始，可选）
}

/**
 * 计算偏移量
 * @param page 页码（从1开始）
 * @param limit 每页数量
 */
export function calculateOffset(page: number, limit: number): number {
  return (page - 1) * limit;
}

/**
 * 计算总页数
 * @param total 总记录数
 * @param limit 每页数量
 */
export function calculateTotalPages(total: number, limit: number): number {
  return Math.ceil(total / limit);
}
