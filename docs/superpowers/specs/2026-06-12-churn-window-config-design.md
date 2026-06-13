# 流失预警对比周期可配置 (CRM Round 3) — 设计文档

> Round 2 已实现 30 天 segment/churn/l6m 3 条件判定 + 入选原因 UI 可读。
> 本轮把"对比周期"从硬编码 30 天改成 60/90/180 三档可切换，默认 90 (一个季度)。
> 同时更正 Round 2 总结里"churn_risk 主表 vs history 算法不一致"的错误判断（实际两边字节级一致）。

## 背景与业务动机

男装奢品客群的复购周期实测 3-6 个月，30 天对比窗口会**漏掉大量"季度性消费降级"客户**：
- 客单价 1-3 万的潜客，可能 4-5 个月才有一次购买
- 60/90/180 天窗口能更准确捕获"曾经好客户 → 半年没买"的流失信号
- 不同档位适用于不同业务场景：60D = 短期监控，90D = 季度复盘，180D = 半年大盘

## 业务澄清

### history vs 主表 churn_risk 算法 — 两边一致

| 项 | 主表 procedure | history procedure | 一致性 |
|---|---|---|---|
| **churn_risk 判定** | r_score + f_score CASE WHEN | **完全相同** | ✅ 字节级一致 |
| **r_score 阈值** | 60/180/365/730 天 | **完全相同** | ✅ |
| **f_score 阈值** | orders ≥ 5/3/2/1 | **完全相同** | ✅ |
| **m_score 阈值** | 5万/2万/1万/5千 | **完全相同** | ✅ |

**更正 Round 2 总结的错误**：之前判断的"history procedure 用 r_score、主表 procedure 用 DATEDIFF，30D 对比是苹果 vs 梨子" — 实际两边都是 r_score 算法，SQL 行为正确，那 39 行结果不应有"算法不一致"问题。

### 3 个判定条件中，本轮只调整购买力坍塌的基线

| 条件 | Round 2 逻辑 | Round 3 调整 |
|---|---|---|
| `_cond_a` 段位退化 | 任何好 segment → 任何差 segment | **不变**（统一 1 档） |
| `_cond_b` churn 升级 | 低/中 → 高 | **不变**（统一 1 档） |
| `_cond_c` 购买力坍塌 | drop ≥ 50% 且 30D 前 ≥ 1万 | **基线随档位变**（1万/1.5万/2万） |

理由：段位退化是离散名 → 离散名的判定，30D 还是 180D 同样适用；churn 升级是离散档位判定，60/90/180D 同样适用。购买力坍塌是连续值，**窗口越长，应只关注本来就高客单的"实质坍塌"，低客单波动不计入**。

### l6m 坍塌的窗口：保持"前后两个 6 月销售额差距"

不引入新窗口（避免又引入一个时间参数）。逻辑：
- 60D 对比：snapshot_now 的 l6m_netsales vs snapshot_60d_ago 的 l6m_netsales
- 90D 对比：snapshot_now 的 l6m_netsales vs snapshot_90d_ago 的 l6m_netsales
- 180D 对比：snapshot_now 的 l6m_netsales vs snapshot_180d_ago 的 l6m_netsales

每个 snapshot 点的 l6m_netsales 都是"截至该 snapshot 时刻往前 6 个月的累计净销售"，时间窗口随 snapshot 滑动 — 跟 60/90/180 周期解耦，行为清晰。

## 目标与验收标准

| ID | 验收 | 衡量 |
|---|---|---|
| AC1 | API 接受 `window=60/90/180`，默认 90 | `curl /api/v2/history/churn-warning` (无参) 用 90；显式 `window=60` 用 60 |
| AC2 | 3 档分别返回非空客户列表 | `curl ?window=60/90/180` 各 `data.length > 0` |
| AC3 | response 含 `applied_thresholds` 字段 | `{ l6m_drop_pct: 0.5, l6m_floor_yuan: 10000\|15000\|20000 }` |
| AC4 | SQL snapshot 窗口按 window 滑动 | `INTERVAL :window_days DAY` 替换原 30 |
| AC5 | h_prev fallback 保留 | 60/90/180D 前若无 snapshot，COALESCE 到 MIN(snapshot_date) |
| AC6 | 前端 Tab 2 头部右侧出现 60D/90D/180D 切换 | 切换后 1) URL 变 2) 表格重渲染 3) 当前阈值文字更新 |
| AC7 | 前端列名从 `segment_30d_ago` 改为 `segment_prev` | ChurnWarningRow 接口字段改名（API 字段名同步改） |
| AC8 | Round 2 已有功能不退化 | severity_tier / selection_reasons / 入选原因 tag 全部保留 |

## 不做（明确 out-of-scope）

- ❌ 修 churn_risk 计算逻辑（确认无 bug，不需要修）
- ❌ 把"对比周期"做成任意天数 slider（仅 3 档离散）
- ❌ 改 segment 退化/churn 升级的判定逻辑
- ❌ 改 history snapshot 调度频率（仍是 每天 13:30）
- ❌ 引入新字段标记"客户是 30/60/90/180D 哪一档命中"（selection_reasons 已涵盖）
- ❌ 修 `ChurnWarningRow → PriorityCustomer` 的 `as unknown as`（技术上不安全但不影响渲染）
- ❌ 把"对比周期"做成全局设置（其他 tab 不受影响）
- ❌ 修 include_total 返回 len(rows) 误导（前端没在用）

> 用户另发现"流失预警 table 字段名与记录错位"的 UI BUG（见任务 #63）— **不在本 spec 范围**，用户决定是否要单独修/合并到本 PR。

## 详细设计

### 1. API 层改动 — `backend/api/target_routes.py:177`

```python
@router.get("/history/churn-warning")
async def get_churn_warning_list(
    window: int = Query(90, description="对比周期（天），仅支持 60/90/180，默认 90"),
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
    include_total: bool = Query(False),
) -> Dict[str, Any]:
    """流失预警列表 — segment/churn_risk 退化 + 购买力坍塌 (Round 3)"""
    # 参数校验
    if window not in (60, 90, 180):
        raise HTTPException(
            status_code=400,
            detail=f"window 必须为 60/90/180 之一, 收到 {window}"
        )

    # 阈值表 (产品配置, 不放进 SQL)
    THRESHOLDS = {
        60:  {"l6m_drop_pct": 0.5, "l6m_floor_yuan": 10000},
        90:  {"l6m_drop_pct": 0.5, "l6m_floor_yuan": 15000},
        180: {"l6m_drop_pct": 0.5, "l6m_floor_yuan": 20000},
    }
    thresholds = THRESHOLDS[window]

    rows = await _run_blocking(
        analyzer.get_churn_warning,
        limit=limit, offset=offset,
        window_days=window,
        l6m_floor=thresholds["l6m_floor_yuan"],
    )

    return {
        "window_days": window,
        "applied_thresholds": thresholds,
        "limit": limit,
        "offset": offset,
        "data": rows,
    }
```

### 2. Analyzer 层改动 — `backend/analytics/target_buyer_analyzer.py:466`

```python
def get_churn_warning(
    self,
    limit: int = 100,
    offset: int = 0,
    window_days: int = 90,
    l6m_floor: int = 15000,
) -> List[Dict[str, Any]]:
    """流失预警列表 (Round 3: 可配置对比周期)"""
    return self.queries.get_churn_warning(
        limit=limit, offset=offset,
        window_days=window_days, l6m_floor=l6m_floor,
    )
```

### 3. Queries 层改动 — `backend/database/target_buyer_queries.py:705`

```python
def get_churn_warning(
    self,
    limit: int = 100,
    offset: int = 0,
    window_days: int = 90,
    l6m_floor: int = 15000,
) -> List[Dict[str, Any]]:
    """流失预警 — segment 退化 + churn 升级 + 购买力坍塌 (Round 3)"""
    sql = self._load_sql('get_churn_warning.sql')
    return self.db.execute_query(sql, {
        "limit": limit,
        "offset": offset,
        "window_days": window_days,
        "l6m_floor": l6m_floor,
    })
```

### 4. SQL 改动 — `backend/database/sql/target_buyers/get_churn_warning.sql`

3 处改动（保留 Round 2 全部优化：MAX(snapshot_date)、内层派生列、`_cond_a_severe`、severity_tier）：

```sql
-- (1) h_prev INTERVAL 30 DAY → INTERVAL :window_days DAY (行 80)
h_prev_inner.snapshot_date = (
    SELECT COALESCE(
        (SELECT MAX(snapshot_date) FROM target_buyers_precomputed_history
            WHERE snapshot_date <= DATE_SUB(
                (SELECT MAX(snapshot_date) FROM target_buyers_precomputed_history),
                INTERVAL :window_days DAY   -- 改这里
            )),
        (SELECT MIN(snapshot_date) FROM target_buyers_precomputed_history)
    )
)

-- (2) _cond_c 基线: 10000 → :l6m_floor (行 70-71)
(h_prev_inner.l6m_netsales >= :l6m_floor
 AND (h_now_inner.l6m_netsales - h_prev_inner.l6m_netsales) <= -0.5 * h_prev_inner.l6m_netsales) AS _cond_c

-- (3) ORDER BY 的窗口提示性 (l6m_netsales_change 本来就是 l6m 差, 不动)
-- 不需要改
```

### 5. 前端类型改动 — `src/api/client.ts:1085`

```typescript
export interface ChurnWarningResponse {
  window_days: number;
  applied_thresholds: {
    l6m_drop_pct: number;
    l6m_floor_yuan: number;
  };
  limit: number;
  offset: number;
  data: ChurnWarningRow[];
}

export interface ChurnWarningRow {
  buyer_nick: string;
  channel: string;
  buyer_type: string;
  vip_level: string;
  segment_prev: string;       // 原 segment_30d_ago
  segment_now: string;
  churn_risk_prev: string;    // 原 churn_risk_30d_ago
  churn_risk_now: string;
  l6m_netsales_change: number;
  l6m_change_pct: number | null;
  last_purchase_date: string | null;
  last_chat_date: string | null;
  selection_reasons: string;
  severity_tier: number;
}

// API client 方法签名
getChurnWarning(opts: { window?: 60|90|180; limit?: number; offset?: number })
  : Promise<ChurnWarningResponse>
```

### 6. 前端组件改动 — `src/components/dashboard/PriorityAttentionBoard.tsx`

#### 6a. 新增对比周期状态
```typescript
const [windowDays, setWindowDays] = useState<60|90|180>(90);
```

#### 6b. Tab 2 头部右侧加分段控件
放在 `<Tabs>` 区域，跟 "Priority / 流失预警" tab 同一行右侧：

```tsx
{churnTabActive && (
  <div className="flex bg-notion-gray_bg p-0.5 rounded-md border border-notion-border">
    {[60, 90, 180].map((d) => (
      <button
        key={d}
        onClick={() => setWindowDays(d as 60|90|180)}
        className={`px-2.5 py-1 text-xs font-medium rounded-sm transition-all ${
          windowDays === d
            ? 'bg-white text-blue-700 shadow-sm border border-blue-100'
            : 'text-notion-muted hover:text-notion-text'
        }`}
      >
        {d}D
      </button>
    ))}
  </div>
)}
```

#### 6c. 当前阈值提示文字
放在分段控件下方 / 表格上方：

```tsx
<p className="text-xs text-notion-muted">
  对比 {windowDays} 天前与现在，segment/churn 退化 或 购买力下降 ≥ 50% 且 {windowDays} 天前 l6m ≥ {floor / 10000}万
</p>
```

#### 6d. 字段重命名适配
`row.segment_30d_ago` → `row.segment_prev`（PriorityAttentionBoard.tsx:140）
`row.churn_risk_30d_ago` → `row.churn_risk_prev`（行 162）

#### 6e. API 调用
```typescript
const churnData = await apiClient.getChurnWarning({
  window: windowDays, limit: 100, offset: 0
});
// response.data 是 ChurnWarningRow[]
// response.applied_thresholds 显示在面板上方
```

## 关键文件清单

| 路径 | 改动 |
|---|---|
| `backend/database/sql/target_buyers/get_churn_warning.sql` | 3 处参数化 (window_days × 2, l6m_floor × 1) |
| `backend/database/target_buyer_queries.py:705` | `get_churn_warning(limit, offset, window_days, l6m_floor)` |
| `backend/analytics/target_buyer_analyzer.py:466` | 透传 window_days + l6m_floor |
| `backend/api/target_routes.py:177` | Query 参数 window + 阈值表 + 校验 |
| `src/api/client.ts:1085` | ChurnWarningRow 字段重命名 + ChurnWarningResponse 类型 + getChurnWarning 签名 |
| `src/components/dashboard/PriorityAttentionBoard.tsx` | 分段控件 + 阈值提示 + 字段名适配 |

**复用**：
- `_run_blocking` 已存在（target_routes.py:75-88）
- NotionTag 组件、NotionCard 组件已存在
- Round 2 全部优化保留：MAX(snapshot_date)、内层派生列、severity_tier、selection_reasons

## 验证

### 1. SQL 三个档位都有数据

```bash
# 重启后端
./scripts/start-backend.sh &

# 3 个档位分别验证
for w in 60 90 180; do
  echo "=== window=$w ==="
  curl -s "http://localhost:8000/api/v2/history/churn-warning?window=$w&limit=100" | \
    python3 -c "
import json, sys
d = json.load(sys.stdin)
print('window_days:', d['window_days'])
print('applied_thresholds:', d['applied_thresholds'])
print('data count:', len(d['data']))
reasons = set()
for r in d['data']:
    for x in r['selection_reasons'].split(','):
        reasons.add(x)
print('reasons:', reasons)
"
done
```

**期望**：
- 3 个档位 `data count` 都 > 0
- 3 个档位都至少含 `购买力坍塌` 入选原因
- `applied_thresholds.l6m_floor_yuan` 分别是 10000 / 15000 / 20000

### 2. SQL 参数校验

```bash
# 不合法 window 应返回 400
curl -s "http://localhost:8000/api/v2/history/churn-warning?window=45" | python3 -m json.tool
# 期望: {"detail": "window 必须为 60/90/180 之一, 收到 45"}
```

### 3. 字段重命名

```bash
# 验证 response 字段是 segment_prev / churn_risk_prev (不是 _30d_ago)
curl -s "http://localhost:8000/api/v2/history/churn-warning?window=90&limit=2" | \
  python3 -c "import json,sys; d=json.load(sys.stdin); print(list(d['data'][0].keys()))"
# 期望: 含 'segment_prev' 和 'churn_risk_prev'，不含 'segment_30d_ago'
```

### 4. 前端 UI 验证

- 浏览器 localhost:3000 → Overview → PriorityAttentionBoard → "流失预警" Tab
- 头部右侧出现 60D / 90D / 180D 三档分段控件，90D 高亮
- 控件下方文字显示当前阈值（"对比 90 天前与现在，segment/churn 退化 或 购买力下降 ≥ 50% 且 90 天前 l6m ≥ 1.5万"）
- 点击 60D → 控件高亮跳到 60D，文字变 "60 天前 l6m ≥ 1万"，表格数据刷新
- 点击 180D → 表格进一步刷新
- 表格列：客户 / VIP / Segment 变化 / 入选原因 / Churn 升级 / L6M 变化 / 最后购买 / 操作
- severity_tier 1-4 色条 / 入选原因 tag / segment 退化颜色 / churn 升级颜色 — 全部保留

### 5. TypeScript 检查

```bash
cd /Users/novel/Projects/smokesignal-ecommerce-analytics
npx tsc --noEmit --pretty false
# 期望: 0 错误
```

### 6. 回归

- PriorityAttentionBoard 的 Priority Tab 不受影响
- ChatAnalysis → CustomerProfile 不受影响
- MetricCards / KeywordAnalysisPanel / SentimentCharts / YoYCompareChart 不受影响
- 其他 history API (timeline/pool-summary/yoy) 不受影响

## 风险

1. **h_prev snapshot 缺失** — history 跨 ≥ 180 天有保证（用户确认），但 180D 前那天可能周末/节假日没 snapshot。fallback 保留（COALESCE 到 MIN），UI 上"对比 180 天"实际可能对比更早一点。**可接受**，因为前端显示的是"180D 档"而不是"180 天前那一天"。
2. **window=180 时 h_prev 太老** — 极端情况 h_prev fallback 到 2024 年某天，跟现在差 2 年，segment/churn 几乎肯定变，cond_a/b 命中率爆增。**可接受**，因为用户主动选 180D 是想看长期。
3. **l6m_netsales_prev=0 时 cond_c 不命中** — 与 Round 2 一致，0 不算"基线"，保护低客单噪音。
4. **selection_reasons 字符串里"购买力坍塌"** — 名字保持不变（用户已熟悉）。
5. **Severity tier 在长窗口下普遍 tier 1** — 180D 时 cond_a_severe 命中多，但这是用户主动选择更严苛窗口的结果，符合预期。

## 实施顺序

1. SQL 改造（`get_churn_warning.sql` + `queries.py` + `analyzer.py`）— 后端可独立测
2. API 加 window 参数 + 校验 + 阈值表（`target_routes.py`）
3. 前端类型 + API client（`client.ts`）
4. 前端组件：分段控件 + 阈值提示 + 字段名适配（`PriorityAttentionBoard.tsx`）
5. 端到端验证（curl + 浏览器）
6. commit（按 Round 2 同款 "feat(crm): 流失预警对比周期可配置"）
