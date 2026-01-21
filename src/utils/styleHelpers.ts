/**
 * Get CSS classes for issue type badges
 */
export function getIssueTypeStyles(issueType: string): string {
  const styles: Record<string, string> = {
    'Churn Risk': 'bg-red-50 text-red-700 border-red-100',
    'Negative Review': 'bg-orange-50 text-orange-700 border-orange-100',
    'Stockout Request': 'bg-yellow-50 text-yellow-700 border-yellow-100',
  };
  return styles[issueType] ?? 'bg-blue-50 text-blue-700 border-blue-100';
}

/**
 * Get CSS classes for priority badges
 */
export function getPriorityStyles(priority: string): string {
  const styles: Record<string, string> = {
    'High': 'text-red-600',
    'Medium': 'text-yellow-600',
    'Low': 'text-green-600',
  };
  return styles[priority] ?? 'text-gray-600';
}

/**
 * Get CSS classes for order status badges
 */
export function getOrderStatusStyles(status: string): string {
  const styles: Record<string, string> = {
    'Completed': 'bg-green-50 text-green-700 border-green-100',
    'Shipped': 'bg-blue-50 text-blue-700 border-blue-100',
  };
  return styles[status] ?? 'bg-gray-100 text-gray-700 border-gray-200';
}
