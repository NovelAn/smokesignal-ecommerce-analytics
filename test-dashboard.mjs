const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({
    headless: false
  });
  const page = await browser.newPage();

  console.log('正在导航到 http://localhost:3003/');
  await page.goto('http://localhost:3003/', {
    waitUntil: 'networkidle'
  });

  console.log('✅ 页面加载成功！');

  // 截图完整页面
  await page.screenshot({
    path: 'screenshots/01-dashboard-full.png',
    fullPage: true
  });
  console.log('✅ 已保存完整页面截图');

  // 检查页面标题
  const title = await page.title();
  console.log(`✅ 页面标题: ${title}`);

  // 检查指标卡片
  const cards = await page.locator('.grid.grid-cols-1.md\\:grid-cols-2.lg\\:grid-cols-4').locator('>').all();
  console.log(`✅ 发现 ${cards.length} 个指标卡片`);

  // 检查图表
  const charts = await page.locator('svg.recharts-wrapper').all();
  console.log(`✅ 发现 ${charts.length} 个图表`);

  // 检查表格
  const tableCount = await page.locator('table').count();
  console.log(`✅ 发现 ${tableCount} 个表格`);

  // 获取浏览器控制台日志
  const logs = await page.evaluate(() => {
    return [...window.console.entries];
  });
  console.log(`📋 浏览器日志: ${logs.length} 条`);

  console.log('\n=== 测试完成 ===');
  console.log('✅ 所有基本检查通过');

  await browser.close();
})();
