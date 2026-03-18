import React from 'react';

interface NotionCardProps {
  children: React.ReactNode;
  className?: string;
  title?: string;
  icon?: any;
  action?: React.ReactNode;
}

export const NotionCard: React.FC<NotionCardProps> = ({
  children,
  className = '',
  title,
  icon: Icon,
  action
}) => (
  <div className={`bg-notion-bg border border-notion-border rounded-sm shadow-card p-4 ${className}`}>
    {title && (
      <div className="flex items-center justify-between mb-4 border-b border-notion-border pb-2">
        <div className="flex items-center gap-2">
            {Icon && <Icon size={16} className="text-notion-text opacity-80" />}
            <h3 className="text-notion-text font-semibold text-sm tracking-wide uppercase">{title}</h3>
        </div>
        {action}
      </div>
    )}
    {children}
  </div>
);
