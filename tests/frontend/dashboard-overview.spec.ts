import { expect, test, type Page } from '@playwright/test';

async function mockDashboardApis(page: Page) {
  await page.route('**/api/v2/**', async (route) => {
    const url = new URL(route.request().url());
    const path = url.pathname;

    if (path.endsWith('/dashboard/metrics')) {
      return route.fulfill({ json: {
        total_target_buyers: 530,
        total_smokers: 373,
        total_vics: 93,
        both_smoker_vic: 23,
        positive_sentiment_count: 2,
        neutral_sentiment_count: 120,
        negative_sentiment_count: 5,
        urgent_priority_count: 3,
        high_priority_count: 160,
        medium_priority_count: 200,
        low_priority_count: 167,
        repurchase_potential_count: 209,
        high_churn_count: 67,
        medium_churn_count: 80,
        low_churn_count: 383,
        last_updated: '2026-06-14 20:59:55',
      } });
    }
    if (path.endsWith('/keyword-analysis')) {
      return route.fulfill({ json: {
        category_distribution: [
          { name: '库存查询', value: 21 },
          { name: '产品推荐咨询', value: 16 },
        ],
        keywords: [{ text: '有货', value: 10, percentage: 27, category: '库存查询' }],
        total_messages: 37,
        data_source: 'chat_history_live',
        last_message_at: '2026-06-12T14:18:07',
      } });
    }
    if (path.endsWith('/insights/vic-persona')) {
      return route.fulfill({ json: {
        total_vic_count: 116,
        key_interests: [
          { keyword: '成衣偏好', count: 56, percentage: 50.5, examples: ['成衣主导', '梭织外套'] },
          { keyword: '促销敏感', count: 49, percentage: 44.1, examples: ['大促心智', '折扣驱动'] },
          { keyword: '其他偏好', count: 58, percentage: 52.3, examples: ['待归类'] },
        ],
        key_pain_points: [{ keyword: '留存与流失风险', count: 78, percentage: 70.3, examples: ['流失风险'] }],
        purchase_motivations: [{ pattern: '品质追求者', count: 48 }],
        summary: {
          headline: 'VIC 群体以成衣偏好为主要偏好，当前最需关注留存与流失风险',
          bullets: ['最普遍兴趣为成衣偏好，覆盖 50.5% 的 VIC 样本。'],
        },
        raw_label_count: 719,
        aggregated_theme_count: 19,
      } });
    }
    if (path.endsWith('/insights/period-comparison')) {
      return route.fulfill({ json: {
        current_period: { start_date: '2026-05-15', end_date: '2026-06-14' },
        comparison_period: { start_date: '2026-04-14', end_date: '2026-05-14' },
        metrics: {
          new_vic: { current: 0, previous: 0, change: 0, change_pct: 0 },
          churn_warning: { current: 0, previous: 0, change: 0, change_pct: 0 },
          vip_upgrades: { current: 0, previous: 0, change: 0, change_pct: 0 },
          sentiment_negative: { current: 0, previous: 0, change: 0, change_pct: 0 },
        },
      } });
    }
    if (path.endsWith('/insights/customer-trends')) {
      return route.fulfill({ json: {
        vic_pool_trend: [{ month: '2026-05', SMOKER: 80, VIC: 30, BOTH: 12 }],
        vic_active_rate_trend: [{ month: '2026-05', total_vic: 116, active_vic: 42, active_rate: 36.2 }],
        high_risk_trend: [{ month: '2026-05', high_risk_count: 19 }],
        sentiment_trend: [],
      } });
    }
    if (path.endsWith('/action/inventory-inquiries')) {
      return route.fulfill({ json: {
        total_count: 21,
        inquiries: [{
          buyer_nick: '库存客户A',
          vip_level: 'V1',
          inventory_questions: ['你好，我想要的 41 码之前没货，现在可以预留吗？'],
          question_count: 3,
          last_inventory_msg_time: '2026-05-19 21:24:38',
          last_chat_date: '2026-06-01 18:40:26',
          dominant_intent: 'Post-sale Support',
          intent_distribution: { 'Post-sale Support': 4, 'Inventory Inquiry': 1 },
          sentiment_label: 'Neutral',
          detected_by: 'both',
          service_status: 'pending',
          service_notes: '',
          service_updated_at: null,
        }],
      } });
    }
    if (path.endsWith('/service/mark')) {
      return route.fulfill({ json: {
        success: true,
        affected_rows: 1,
        buyer_nick: '库存客户A',
        previous_status: 'pending',
        new_status: 'contacted',
        workstream: 'inventory',
      } });
    }
    if (path.endsWith('/priority-customers')) {
      return route.fulfill({ json: { customers: [], total: 0, limit: 20, offset: 0 } });
    }
    if (path.endsWith('/history/churn-warning')) {
      const windowDays = Number(url.searchParams.get('window') || 90);
      return route.fulfill({ json: {
        window_days: windowDays,
        applied_thresholds: { l6m_drop_pct: 0.5, l6m_floor_yuan: 15000 },
        limit: 15,
        offset: 0,
        total: 31,
        data: [{
          buyer_nick: '风险客户A',
          channel: 'PFS',
          buyer_type: 'VIC',
          vip_level: 'V2',
          segment_prev: '重要价值客户',
          segment_now: '潜力客户',
          churn_risk_prev: '中',
          churn_risk_now: '高',
          l6m_netsales_change: -22000,
          l6m_change_pct: -55,
          last_purchase_date: '2026-05-01',
          last_chat_date: '2026-06-01',
          service_status: null,
          selection_reasons: 'segment退化,情感转负',
          severity_tier: 1,
        }],
      } });
    }
    if (path.endsWith('/buyers/count')) {
      return route.fulfill({ json: { total: 0 } });
    }
    if (path.endsWith('/buyers')) {
      return route.fulfill({ json: { buyers: [], total: 0, limit: 100, offset: 0 } });
    }

    return route.fulfill({ json: {} });
  });
}

test.beforeEach(async ({ page }) => {
  await mockDashboardApis(page);
  await page.goto('/');
});

test('renders redesigned Overview and switches action tabs', async ({ page }) => {
  await expect(page.getByRole('heading', { name: 'VIC 群体画像' })).toBeVisible();
  await expect(page.getByText('时间对比摘要')).toBeVisible();
  await expect(page.getByText('情感趋势暂无可用数据')).toBeVisible();
  await expect(page.getByRole('button', { name: '库存查询' })).toBeVisible();

  await page.getByRole('tab', { name: '行动看板' }).click();
  await expect(page.getByText('异常客户预警')).toHaveCount(0);
  await expect(page.getByText('库存客户A')).toBeVisible();
  await expect(page.getByText('41 码之前没货')).toBeVisible();
  await expect(page.getByText('AI + 关键词')).toBeVisible();
  await expect(page.getByRole('heading', { name: '需优先跟进的客户' })).toBeVisible();
  await expect(page.getByRole('button', { name: '已触达' }).first()).toBeVisible();
});

test('action lists stay bounded with larger API responses', async ({ page }) => {
  await page.getByRole('tab', { name: '行动看板' }).click();
  await expect(page.getByTestId('inventory-inquiry-list')).toHaveCSS('overflow-y', 'auto');
});

test('churn window switch refetches and keeps accurate pagination total', async ({ page }) => {
  const churnRequests: string[] = [];
  page.on('request', (request) => {
    if (request.url().includes('/history/churn-warning')) churnRequests.push(request.url());
  });

  await page.getByRole('tab', { name: '行动看板' }).click();
  await page.getByRole('button', { name: '流失预警', exact: true }).click();
  await expect(page.getByText('风险客户A')).toBeVisible();
  await expect(page.getByText('1 / 3')).toBeVisible();
  await page.getByRole('button', { name: '60D', exact: true }).click();

  await expect.poll(() => churnRequests.some((url) => url.includes('window=60'))).toBeTruthy();
});

test('time presets and custom range update the comparison request', async ({ page }) => {
  const comparisonRequests: string[] = [];
  page.on('request', (request) => {
    if (request.url().includes('/insights/period-comparison')) comparisonRequests.push(request.url());
  });

  await page.getByRole('button', { name: '7D', exact: true }).click();
  await expect.poll(() => comparisonRequests.some((url) => url.includes('start_date='))).toBeTruthy();

  await page.getByRole('button', { name: '自定义' }).click();
  await page.getByLabel('开始日期').fill('2026-05-01');
  await page.getByLabel('结束日期').fill('2026-05-31');
  await page.getByRole('button', { name: '应用日期' }).click();

  await expect(page.getByText('2026-05-01 至 2026-05-31', { exact: true })).toBeVisible();
  await expect.poll(() => comparisonRequests.some((url) =>
    url.includes('start_date=2026-05-01') && url.includes('end_date=2026-05-31'),
  )).toBeTruthy();
});

test('VIC persona presents semantic summary instead of raw label expansion', async ({ page }) => {
  await expect(page.getByText('VIC 群体以成衣偏好为主要偏好，当前最需关注留存与流失风险')).toBeVisible();
  await expect(page.getByText('成衣主导 · 梭织外套')).toBeVisible();
  await expect(page.getByText('其他偏好', { exact: true })).toHaveCount(0);
  await expect(page.getByRole('button', { name: /展开全部/ })).toHaveCount(0);
});

test('keyword analysis follows the shared Overview date range', async ({ page }) => {
  const keywordRequests: string[] = [];
  page.on('request', (request) => {
    if (request.url().includes('/keyword-analysis')) keywordRequests.push(request.url());
  });

  await page.getByRole('button', { name: '7D', exact: true }).click();

  await expect.poll(() => keywordRequests.some((url) =>
    url.includes('start_date=') && url.includes('end_date='),
  )).toBeTruthy();
  await expect(page.getByText('实时聊天数据')).toBeVisible();
});

test('inventory service action uses the inventory workstream', async ({ page }) => {
  let serviceBody: Record<string, unknown> | null = null;
  page.on('request', (request) => {
    if (request.url().endsWith('/service/mark') && request.method() === 'POST') {
      serviceBody = request.postDataJSON();
    }
  });

  await page.getByRole('tab', { name: '行动看板' }).click();
  await page.getByRole('button', { name: '已触达' }).first().click();

  await expect.poll(() => serviceBody).toMatchObject({
    buyer_nick: '库存客户A',
    status: 'contacted',
    workstream: 'inventory',
  });
});

test('mobile layout keeps filters usable and charts in one column', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 667 });
  await page.reload();
  await expect(page.getByRole('button', { name: '1M', exact: true })).toBeVisible();
  const grid = page.getByTestId('customer-trends-grid');
  await expect(grid).toHaveCSS('grid-template-columns', /\d+(\.\d+)?px/);
});

test('launches all four active Overview requests in parallel', async ({ page }) => {
  const endpointTimes = new Map<string, number>();
  const endpoints = [
    '/insights/vic-persona',
    '/insights/period-comparison',
    '/insights/customer-trends',
    '/action/inventory-inquiries',
  ];
  page.on('request', (request) => {
    const endpoint = endpoints.find((item) => request.url().includes(item));
    if (endpoint && !endpointTimes.has(endpoint)) endpointTimes.set(endpoint, Date.now());
  });

  await page.reload();
  await expect.poll(() => endpointTimes.size).toBe(4);
  const times = [...endpointTimes.values()];
  expect(Math.max(...times) - Math.min(...times)).toBeLessThan(500);
});
