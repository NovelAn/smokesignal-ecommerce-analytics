import React from 'react';
import { Search } from 'lucide-react';
import { useDebounce } from '../../hooks/useDebounce';

interface SearchBarProps {
  placeholder?: string;
  value: string;
  onChange: (value: string) => void;
  debounceMs?: number;
  className?: string;
}

export const SearchBar: React.FC<SearchBarProps> = ({
  placeholder = 'Search...',
  value,
  onChange,
  debounceMs = 300,
  className = ''
}) => {
  const debouncedValue = useDebounce(value, debounceMs);

  React.useEffect(() => {
    onChange(debouncedValue);
  }, [debouncedValue, onChange]);

  return (
    <div className={`relative ${className}`}>
      <Search className="absolute left-2.5 top-2.5 text-notion-muted" size={14} />
      <input
        type="text"
        placeholder={placeholder}
        className="w-full bg-notion-gray_bg border-0 text-notion-text pl-9 pr-3 py-1.5 rounded text-sm focus:ring-1 focus:ring-blue-400 placeholder-notion-muted/70 transition-all"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  );
};
