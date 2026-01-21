import React from 'react';
import { NotionTagProps } from '../../types/common';

export function NotionTag({ text, color = 'gray' }: NotionTagProps) {
  const colors = {
    gray: 'bg-notion-gray_bg text-gray-700',
    brown: 'bg-notion-brown_bg text-yellow-900',
    orange: 'bg-notion-orange_bg text-orange-900',
    yellow: 'bg-notion-yellow_bg text-yellow-800',
    green: 'bg-notion-green_bg text-green-900',
    blue: 'bg-notion-blue_bg text-blue-900',
    purple: 'bg-notion-purple_bg text-purple-900',
    pink: 'bg-notion-pink_bg text-pink-900',
    red: 'bg-notion-red_bg text-red-900',
  };

  return (
    <span className={`px-1.5 py-0.5 rounded text-xs font-medium mr-1 ${colors[color]}`}>
      {text}
    </span>
  );
}
