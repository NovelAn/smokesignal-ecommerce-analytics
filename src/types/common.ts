import { ReactNode } from 'react';

export interface NotionCardProps {
  children: ReactNode;
  className?: string;
  title?: string;
  icon?: React.ComponentType<{ size?: number; className?: string }>;
  action?: ReactNode;
}

export type NotionTagColor = 'gray' | 'brown' | 'orange' | 'yellow' | 'green' | 'blue' | 'purple' | 'pink' | 'red';

export interface NotionTagProps {
  text: string;
  color?: NotionTagColor;
}
