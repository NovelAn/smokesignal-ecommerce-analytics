import { useContext } from 'react';
import { TimeRangeContext } from '../contexts/TimeRangeContext';

export function useTimeRange() {
  const context = useContext(TimeRangeContext);
  if (!context) throw new Error('useTimeRange must be used within TimeRangeProvider');
  return context;
}
