import type {
  CustomerTrends,
  InventoryInquiries,
  PeriodComparison,
  VicPersona,
} from '../types/insights';

const API_BASE = '/api/v2';
let inventoryInquiriesPromise: Promise<InventoryInquiries> | null = null;

async function fetchJson<T>(url: string, errorPrefix: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(url, { signal });
  if (!response.ok) {
    const detail = await response.json().catch(() => null);
    const message = typeof detail?.detail === 'string' ? detail.detail : response.statusText;
    throw new Error(`${errorPrefix}: ${message || response.status}`);
  }
  return response.json();
}

export function fetchVicPersona(
  buyerType: 'VIC' | 'SMOKER' = 'VIC',
  signal?: AbortSignal,
): Promise<VicPersona> {
  return fetchJson(
    `${API_BASE}/insights/vic-persona?buyer_type=${buyerType}`,
    '群体画像查询失败',
    signal,
  );
}

export function fetchPeriodComparison(
  startDate: string,
  endDate: string,
  comparisonStartDate?: string | null,
  comparisonEndDate?: string | null,
  signal?: AbortSignal,
): Promise<PeriodComparison> {
  const params = new URLSearchParams({ start_date: startDate, end_date: endDate });
  if (comparisonStartDate) params.set('comparison_start_date', comparisonStartDate);
  if (comparisonEndDate) params.set('comparison_end_date', comparisonEndDate);
  return fetchJson(
    `${API_BASE}/insights/period-comparison?${params}`,
    '时间对比查询失败',
    signal,
  );
}

export function fetchCustomerTrends(months = 6, signal?: AbortSignal): Promise<CustomerTrends> {
  return fetchJson(
    `${API_BASE}/insights/customer-trends?months=${months}`,
    '趋势数据查询失败',
    signal,
  );
}

export function fetchInventoryInquiries(signal?: AbortSignal): Promise<InventoryInquiries> {
  if (!inventoryInquiriesPromise) {
    inventoryInquiriesPromise = fetchJson<InventoryInquiries>(
      `${API_BASE}/action/inventory-inquiries`,
      '库存需求查询失败',
      signal,
    ).catch((error) => {
      inventoryInquiriesPromise = null;
      throw error;
    });
  }
  return inventoryInquiriesPromise;
}

export async function fetchDashboardOverview(startDate: string, endDate: string) {
  const [vicPersona, periodComparison, customerTrends, inventoryInquiries] =
    await Promise.all([
      fetchVicPersona(),
      fetchPeriodComparison(startDate, endDate),
      fetchCustomerTrends(),
      fetchInventoryInquiries(),
    ]);

  return { vicPersona, periodComparison, customerTrends, inventoryInquiries };
}
