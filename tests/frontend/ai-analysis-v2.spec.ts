import { expect, test, type Page } from '@playwright/test';


async function mockApis(page: Page) {
  await page.route('**/api/v2/**', async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname;

    if (path.endsWith('/ai-analysis-v2/trends')) {
      return route.fulfill({ json: {
        items: [{
          issue_category: 'product',
          issue_code: 'material_expectation',
          event_count: 8,
          affected_buyers: 6,
          unresolved_count: 4,
          high_severity_count: 1,
          last_seen_at: '2026-07-21T10:00:00',
          current_period_count: 8,
          previous_period_count: 5,
          change_percent: 60,
        }],
      } });
    }
    if (path.endsWith('/ai-analysis-v2/reviews') && request.method() === 'GET') {
      return route.fulfill({ json: {
        count: 1,
        items: [{
          id: 1,
          event_id: 9,
          buyer_nick: '十八子李海旭',
          topic_summary: '客户询问商品是否为正品',
          review_stratum: 'ambiguity',
          review_status: 'pending',
          review_note: null,
          model_payload: {
            events: [{
              event_action: 'new_event', related_event_id: null,
              topic_summary: '客户询问商品是否为正品',
              event_started_at: '2026-07-20T10:00:00', event_ended_at: '2026-07-20T10:05:00',
              sentiment_label: 'Negative', sentiment_score: 0.3,
              sentiment_basis: 'strong_negative_evaluation', peak_emotion: 'concern',
              service_friction: 'none', resolution_status: 'explained_pending_acceptance',
              customer_accepted: true, suggested_action: '无需升级投诉', issues: [{
                issue_category: 'trust', issue_code: 'authenticity_concern',
                issue_detail: '客户怀疑是假货', severity: 'medium', owner: 'customer',
                status: 'explained_pending_acceptance', is_primary: true,
                evidence_text: '是假货吗', evidence_msg_time: '2026-07-20T10:00:00',
              }],
            }],
          },
          dialogue: [
            { role: 'buyer', content: '是假货吗', msg_time: '2026-07-20T10:00:00' },
            { role: 'service', content: '我们是官方旗舰店，商品保证正品', msg_time: '2026-07-20T10:01:00' },
          ],
        }],
      } });
    }
    if (path.endsWith('/ai-analysis-v2/reviews/9') && request.method() === 'PUT') {
      return route.fulfill({ json: { event_id: 9, review_status: 'corrected' } });
    }
    return route.abort();
  });
}


test.beforeEach(async ({ page }) => {
  await mockApis(page);
  await page.goto('/');
});


test('review workbench corrects a case and updates progress', async ({ page }) => {
  await page.getByRole('button', { name: 'AI 问题洞察' }).click();
  await page.getByRole('tab', { name: '人工审核' }).click();
  await page.getByRole('button', { name: /十八子李海旭/ }).click();
  await page.getByRole('button', { name: '修改结果' }).click();
  await page.getByLabel('最终情感').selectOption('Neutral');
  await page.getByLabel('情感依据').selectOption('authenticity_concern');
  await page.getByLabel('处理结果').selectOption('resolved');
  await page.getByLabel('问题详情 1').fill('客户询问正品保障，客服已解释清楚');
  await page.getByLabel('审核备注').fill('真伪求证，不是明确投诉');
  const requestPromise = page.waitForRequest(request => request.url().endsWith('/ai-analysis-v2/reviews/9') && request.method() === 'PUT');
  await page.getByRole('button', { name: '确认并加入金标准' }).click();
  const request = await requestPromise;
  const corrected = request.postDataJSON().gold_payload.events[0];

  expect(corrected.resolution_status).toBe('resolved');
  expect(corrected.sentiment_basis).toBe('authenticity_concern');
  expect(corrected.issues[0].issue_detail).toBe('客户询问正品保障，客服已解释清楚');
  await expect(page.getByText(/已审核\s*1\s*\/\s*50/)).toBeVisible();
});


test('issue trends expose period filters and business counts', async ({ page }) => {
  await page.getByRole('button', { name: 'AI 问题洞察' }).click();

  await expect(page.getByText('material_expectation')).toBeVisible();
  await expect(page.getByText('6 位客户')).toBeVisible();
  await page.getByRole('button', { name: '90 天' }).click();
  await expect(page.getByRole('button', { name: '90 天' })).toHaveAttribute('aria-pressed', 'true');
});
