import React, { useEffect, useRef, useState } from 'react';
import type { PriorityCustomer, ServiceStatus } from '../../api/client';

interface StatusButtonGroupProps {
  buyer: PriorityCustomer;
  /** 父组件处理实际 API 调用 + confirm 弹窗 + 30秒撤销 state */
  onChange: (newStatus: ServiceStatus) => void;
  /** 该 buyer 是否处于"30 秒可撤销"状态，父组件控制 */
  canUndo?: boolean;
  /** 撤销回调 */
  onUndo?: () => void;
}

const STATUS_CONFIG: Record<ServiceStatus, { label: string; activeClass: string }> = {
  pending: {
    label: '未处理',
    activeClass: 'bg-gray-100 text-gray-700 border-gray-300',
  },
  contacted: {
    label: '已触达',
    activeClass: 'bg-blue-50 text-blue-700 border-blue-300',
  },
  resolved: {
    label: '已解决',
    activeClass: 'bg-green-50 text-green-700 border-green-300',
  },
};

const STATUS_ORDER: ServiceStatus[] = ['pending', 'contacted', 'resolved'];

/**
 * 状态切换按钮组 (Round 1 CRM)
 *
 * - 三按钮：未处理 / 已触达 / 已解决
 * - 当前状态高亮（颜色 + 加粗），其他灰色
 * - 点击切换触发 onChange（父组件弹 confirm / 调 API / 设置 30秒撤销）
 * - canUndo 时显示 "(撤销)" 链接，点击触发 onUndo
 */
export const StatusButtonGroup: React.FC<StatusButtonGroupProps> = ({
  buyer,
  onChange,
  canUndo = false,
  onUndo,
}) => {
  const current: ServiceStatus = buyer.service_status || 'pending';

  if (canUndo) {
    return (
      <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
        <span
          className={`text-xs px-2 py-0.5 rounded font-semibold border ${STATUS_CONFIG[current].activeClass}`}
        >
          {STATUS_CONFIG[current].label}
        </span>
        {onUndo && (
          <button
            type="button"
            onClick={onUndo}
            className="text-xs text-notion-muted underline hover:text-notion-text transition-colors"
            title="30秒内可撤销"
          >
            撤销
          </button>
        )}
      </div>
    );
  }

  return (
    <div
      className="flex items-center gap-1"
      onClick={(e) => e.stopPropagation()}
    >
      {STATUS_ORDER.map((s) => {
        const isActive = s === current;
        return (
          <button
            key={s}
            type="button"
            onClick={() => {
              if (!isActive) onChange(s);
            }}
            className={
              isActive
                ? `text-xs px-2 py-0.5 rounded font-semibold border transition-colors ${STATUS_CONFIG[s].activeClass}`
                : 'text-xs px-2 py-0.5 rounded text-notion-muted border border-notion-border hover:bg-notion-hover transition-colors'
            }
            disabled={isActive}
            title={isActive ? '当前状态' : `切换为「${STATUS_CONFIG[s].label}」`}
          >
            {STATUS_CONFIG[s].label}
          </button>
        );
      })}
    </div>
  );
};
