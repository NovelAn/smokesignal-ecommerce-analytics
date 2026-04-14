import React from 'react';

interface NotionCardProps {
  children: React.ReactNode;
  className?: string;
  title?: string;
  subtitle?: string;
  icon?: any;
  action?: React.ReactNode;
  onClick?: () => void;
}

export const NotionCard: React.FC<NotionCardProps> = ({
  children,
  className = '',
  title,
  subtitle,
  icon: Icon,
  action
}) => (
  <div className={`bg-notion-bg border border-notion-border rounded-sm shadow-card p-4 ${className}`}>
    {title && (
      <div className="flex items-center justify-between mb-4 border-b border-notion-border pb-2">
        <div className="flex flex-col gap-0.5">
          <div className="flex items-center gap-2">
            {Icon && <Icon size={16} className="text-notion-text opacity-80" />}
            <h3 className="text-notion-text font-semibold text-sm tracking-wide uppercase">{title}</h3>
          </div>
          {subtitle && (
            <span className="text-xs text-notion-muted ml-6">{subtitle}</span>
          )}
        </div>
        {action}
      </div>
    )}
    {children}
  </div>
);
