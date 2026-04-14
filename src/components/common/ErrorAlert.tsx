import React, { Component } from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';

/**
 * 错误提示组件
 */
export const ErrorAlert: React.FC<{
  message: string;
  onRetry?: () => void;
  details?: string;
}> = ({ message, onRetry, details }) => (
  <div className="bg-red-50 border border-red-200 rounded-sm p-4 flex items-start gap-3">
    <AlertCircle className="text-red-600 shrink-0 mt-0.5" size={18} />
    <div className="flex-1">
      <h4 className="text-sm font-semibold text-red-900 mb-1">加载失败</h4>
      <p className="text-sm text-red-700">{message}</p>
      {details && (
        <details className="mt-2">
          <summary className="text-xs text-red-600 cursor-pointer hover:text-red-800">
            查看详细错误
          </summary>
          <pre className="mt-2 text-xs text-red-600 bg-red-100 p-2 rounded overflow-auto max-h-32">
            {details}
          </pre>
        </details>
      )}
    </div>
    {onRetry && (
      <button
        onClick={onRetry}
        className="shrink-0 px-3 py-1.5 bg-red-600 text-white text-xs font-medium rounded hover:bg-red-700 transition-colors flex items-center gap-1.5"
      >
        <RefreshCw size={12} />
        重试
      </button>
    )}
  </div>
);

/**
 * 空状态组件
 */
export const EmptyState: React.FC<{
  icon?: React.ElementType;
  title: string;
  description?: string;
  action?: React.ReactNode;
}> = ({ icon: Icon, title, description, action }) => (
  <div className="flex flex-col items-center justify-center p-12 text-center border border-dashed border-notion-border rounded-sm bg-notion-gray_bg/30">
    {Icon && <Icon className="text-notion-muted mb-3" size={32} />}
    <h3 className="text-sm font-semibold text-notion-text mb-1">{title}</h3>
    {description && <p className="text-xs text-notion-muted mb-3">{description}</p>}
    {action}
  </div>
);

/**
 * API错误边界
 */
export class APIErrorBoundary extends Component<
  { children: React.ReactNode; fallback?: React.ReactNode },
  { hasError: boolean; error?: Error }
> {
  constructor(props: { children: React.ReactNode; fallback?: React.ReactNode }) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('API Error caught by boundary:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        this.props.fallback || (
          <ErrorAlert
            message="出现了一个错误"
            details={this.state.error?.message}
          />
        )
      );
    }

    return this.props.children;
  }
}
