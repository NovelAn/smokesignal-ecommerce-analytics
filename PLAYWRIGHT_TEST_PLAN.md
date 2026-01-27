# Playwright 自动化测试计划

**测试目标**: 验证 Phase 3.1 Dashboard 组件拆分功能

## 测试环境
- URL: http://localhost:3003/
- 浏览器: Chromium (Playwright)
- 分支: feature/sql-field-names-update

## 测试场景

### 1. 页面加载测试
```javascript
// 导航到页面
await page.goto('http://localhost:3003/');

// 等待页面完全加载
await page.waitForLoadState('networkidle');

// 截图
await page.screenshot({ path: 'screenshots/01-dashboard-loaded.png' });
```

### 2. Dashboard 视图验证
```javascript
// 检查标题
const title = await page.title();
expect(title).toContain('SmokeSignal');

// 截图 Dashboard
await page.screenshot({ path: 'screenshots/02-dashboard-view.png' });
```

### 3. 指标卡片验证
```javascript
// 检查 4 个指标卡片是否存在
const metricCards = await page.locator('.grid.grid-cols-1.md\\:grid-cols-2.lg\\:grid-cols-4').locator('>').all();
expect(metricCards.length).toBe(4);

// 检查卡片内容
const cardTitles = await page.locator('.text-3xl').allTextContents();
console.log('指标卡片:', cardTitles);
```

### 4. 图表渲染验证
```javascript
// 检查 Recharts 图表是否渲染
const charts = await page.locator('svg.recharts-wrapper').all();
console.log('图表数量:', charts.length);

// 截图图表区域
await page.locator('.grid.lg\\:grid-cols-3').screenshot({ path: 'screenshots/03-charts.png' });
```

### 5. 表格验证
```javascript
// 检查优先关注客户表格
const table = await page.locator('table').first();
const isVisible = await table.isVisible();
console.log('表格可见:', isVisible);

// 截图表格
await page.screenshot({ path: 'screenshots/04-priority-table.png' });
```

### 6. 时间筛选器测试
```javascript
// 点击不同的时间范围
await page.click('button:has-text("7 Days")');
await page.waitForTimeout(1000);
await page.screenshot({ path: 'screenshots/05-time-range-7d.png' });

await page.click('button:has-text("1 Mo")');
await page.waitForTimeout(1000);
await page.screenshot({ path: 'screenshots/06-time-range-1m.png' });
```

### 7. 控制台错误检查
```javascript
// 获取浏览器日志
const logs = await page.evaluate(() => {
    return [...window.console.entries];
});
console.log('控制台日志:', logs);
```

## 预期结果

### ✅ 应该看到的
- Dashboard 标签页默认选中
- 4 个指标卡片正常显示
- 关键词分析面板显示（占位数据）
- 优先关注客户表格显示
- 3 个图表正常渲染

### ⚠️ 可能的问题
- 如果后端未运行：指标卡片显示加载错误
- 如果 API 配置错误：控制台有 404 错误
- 如果导入错误：页面空白

## 测试命令（等下载完成后）

```bash
# 创建截图目录
mkdir -p screenshots

# 使用 Playwright MCP 测试
```
