import { type ReactNode, type ComponentType } from 'react';

export interface NotionCardProps {
  children: ReactNode;
  className?: string;
  title?: string;
  icon?: ComponentType<{ size?: number; className?: string }>;
  action?: ReactNode;
  onClick?: () => void;
}

export type NotionTagColor = 'gray' | 'brown' | 'orange' | 'yellow' | 'green' | 'blue' | 'purple' | 'pink' | 'red';

export interface NotionTagProps {
  text: string;
  color?: NotionTagColor;
  size?: 'xs' | 'sm' | 'md' | 'lg';
}
