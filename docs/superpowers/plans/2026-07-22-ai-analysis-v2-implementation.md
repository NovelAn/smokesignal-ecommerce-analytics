# AI Analysis V2 Implementation Plan

> **For implementation:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` in this session and implement the tasks sequentially. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and verify the complete AI Analysis V2 loop: incremental event analysis, multiple structured issues, current customer state, cross-customer trends, a 50-case review workflow, and gated Priority List integration.

**Architecture:** Keep V1 untouched while V2 runs in five normalized shadow tables. Deterministic Python prepares and persists data; MiniMax performs semantic analysis, with one schema retry and narrowly gated DeepSeek fallback. A separate FastAPI router and React view expose customer state, trends, and human review; V2 becomes Priority List input only after the 50-case acceptance gate.

**Tech Stack:** Python 3.13, FastAPI, Pydantic 2, PyMySQL/MySQL 8, React 19, TypeScript 5.8, Vite 6, Recharts 3.6, pytest, Playwright.

## Global Constraints

- Preserve all existing V1 tables and APIs; V2 uses shadow tables until the acceptance gate passes.
- Put every new SQL statement in `backend/database/sql/ai_analysis_v2/`; do not embed business SQL in Python.
- MiniMax M3 performs semantic analysis; Python performs only deterministic preparation, validation, persistence, rollup, and aggregation.
- Do not use keyword rules or a rule-based fallback to generate sentiment, issue, issue detail, resolution, or evidence.
- A failed or invalid model run may write only run failure metadata; it must not write events, issues, customer state, reviews, or advance the checkpoint.
- Use one MiniMax schema retry. Use DeepSeek only after that retry and only for V3/V2, urgent/high-priority, or recently Negative customers.
- Do not add dependencies unless an existing dependency cannot perform the required behavior.
- Do not modify credentials or apply database migrations to Aliyun production without explicit user approval.
- Validate DDL against an accessible non-production MySQL 8 database before requesting production migration approval.
- The release gate requires 50/50 reviewed cases and the exact acceptance thresholds in `docs/superpowers/specs/2026-07-22-ai-analysis-v2-design.md`.

## File Map

### Backend domain and engine

- `backend/ai/v2/__init__.py`: public V2 exports.
- `backend/ai/v2/schemas.py`: Pydantic contracts, enums, taxonomy, payload validation.
- `backend/ai/v2/preprocessing.py`: message ordering, masking, filtering, windows, fingerprints.
- `backend/ai/v2/prompt.py`: MiniMax/DeepSeek V2 prompt builder.
- `backend/ai/v2/analyzer.py`: provider routing, retries, idempotency, full/incremental orchestration.
- `backend/ai/v2/rollup.py`: issue decay and customer-state calculation.
- `backend/ai/v2/repository.py`: SQL loading, reads, transactional writes, trends, reviews.
- `backend/ai/v2/cohort.py`: deterministic 50-case stratified sampling and acceptance metrics.

### Database

- `backend/database/sql/ai_analysis_v2/create_tables.sql`: five V2 tables and indexes.
- `backend/database/sql/ai_analysis_v2/*.sql`: run, event, issue, state, trend, review, and Priority queries.
- `backend/database/sql/ai_analysis_v2/drop_tables.sql`: non-production rollback in reverse FK order.

### API and frontend

- `backend/api/ai_analysis_v2_routes.py`: V2 endpoints and batch task state.
- `backend/api/__init__.py`, `backend/main.py`: router registration.
- `src/types/aiAnalysisV2.ts`: V2 frontend contracts.
- `src/api/client.ts`: V2 API methods.
- `src/views/AIAnalysisV2View.tsx`: trends/review top-level view.
- `src/components/ai-analysis-v2/IssueTrendsPanel.tsx`: trends and filters.
- `src/components/ai-analysis-v2/ReviewWorkbench.tsx`: 50-case review workflow.
- `src/components/ai-analysis-v2/CustomerV2StateCard.tsx`: customer detail state and history.
- `src/App.tsx`, `src/views/ChatAnalysis.tsx`, `src/components/dashboard/PriorityAttentionBoard.tsx`: navigation and integrations.

### Tests and operational artifacts

- `tests/ai/test_ai_analysis_v2_*.py`: schema, preprocessing, prompt, analyzer, rollup.
- `tests/database/test_ai_analysis_v2_repository.py`: transaction/idempotency tests.
- `tests/api/test_ai_analysis_v2_routes.py`: API contracts.
- `tests/playwright/test_ai_analysis_v2.py`: browser closed-loop test.
- `scripts/prepare_ai_v2_review_cohort.py`: create or preview the 50-case queue.
- `scripts/evaluate_ai_v2_gold.py`: produce acceptance metrics.
- `docs/testing/ai-analysis-v2-acceptance-report.md`: generated and reviewed acceptance evidence.
- `docs/部署运维/AI_Analysis_V2_部署与回滚.md`: migration, cutover, rollback, and monitoring commands.

---

### Task 1: Define strict V2 domain contracts

**Files:**
- Create: `backend/ai/v2/__init__.py`
- Create: `backend/ai/v2/schemas.py`
- Create: `tests/ai/test_ai_analysis_v2_schemas.py`

**Interfaces:**
- Consumes: `pydantic.BaseModel`, existing strict sentiment labels from `backend/ai/analysis_errors.py`.
- Produces: `AnalysisPayload`, `EventAnalysis`, `IssueAnalysis`, `CustomerState`, `ReviewDecision`, `ISSUE_TAXONOMY`, `validate_model_payload(text: str) -> AnalysisPayload`.

- [x] **Step 1: Write failing schema tests**

```python
def test_analysis_payload_accepts_multiple_issues():
    payload = valid_payload()
    payload["events"][0]["issues"].append(second_issue())
    result = AnalysisPayload.model_validate(payload)
    assert len(result.events[0].issues) == 2

def test_analysis_payload_rejects_unknown_issue_code():
    payload = valid_payload()
    payload["events"][0]["issues"][0]["issue_code"] = "invented_code"
    with pytest.raises(ValidationError):
        AnalysisPayload.model_validate(payload)

def test_negative_requires_negative_basis():
    payload = valid_payload()
    payload["events"][0].update(
        sentiment_label="Negative",
        sentiment_basis="authenticity_concern",
    )
    with pytest.raises(ValidationError):
        AnalysisPayload.model_validate(payload)
```

- [x] **Step 2: Verify RED**

Run: `./.venv/bin/python -m pytest -q tests/ai/test_ai_analysis_v2_schemas.py`
Expected: collection fails because `backend.ai.v2.schemas` does not exist.

- [x] **Step 3: Implement the contracts**

```python
SentimentLabel = Literal["Positive", "Neutral", "Negative"]
EventAction = Literal["new_event", "continue_event"]
IssueSeverity = Literal["low", "medium", "high", "critical"]
IssueStatus = Literal["open", "explained_pending_acceptance", "resolved", "unknown"]

ISSUE_TAXONOMY = {
    "product": {"material_expectation", "color_appearance_mismatch", "size_fit", "quality_damage", "packaging"},
    "logistics": {"shipping_delay", "delivery_failure", "return_pickup", "address_contact"},
    "after_sales": {"return_request", "exchange_request", "refund_delay", "repair_warranty"},
    "pricing_promotion": {"price_change", "discount_eligibility", "price_difference"},
    "inventory": {"out_of_stock", "replenishment_wait"},
    "service": {"response_slow", "explanation_unclear", "repeated_communication", "service_attitude"},
    "trust": {"authenticity_concern", "advertising_mismatch"},
    "usage_care": {"usage_instruction", "care_maintenance"},
    "other": {"other"},
}

class IssueAnalysis(BaseModel):
    issue_category: str
    issue_code: str
    issue_detail: str = Field(min_length=1, max_length=500)
    severity: IssueSeverity
    owner: Literal["product", "logistics", "service", "customer", "mixed", "unknown"]
    status: IssueStatus
    is_primary: bool
    evidence_text: str = Field(max_length=500)
    evidence_msg_time: datetime | None = None

    @model_validator(mode="after")
    def code_matches_category(self):
        if self.issue_code not in ISSUE_TAXONOMY.get(self.issue_category, set()):
            raise ValueError("issue_code does not belong to issue_category")
        return self

class EventAnalysis(BaseModel):
    event_action: EventAction
    related_event_id: int | None
    topic_summary: str = Field(min_length=1, max_length=500)
    event_started_at: datetime
    event_ended_at: datetime
    sentiment_label: SentimentLabel
    sentiment_score: float = Field(ge=0, le=1)
    sentiment_basis: str
    peak_emotion: Literal["calm", "concern", "anxiety", "dissatisfaction", "anger", "gratitude"]
    service_friction: Literal["none", "low", "medium", "high"]
    resolution_status: Literal["unresolved", "explained_pending_acceptance", "resolved", "unknown"]
    customer_accepted: bool | None
    suggested_action: str = Field(max_length=500)
    issues: list[IssueAnalysis]

    @model_validator(mode="after")
    def enforce_sentiment_boundary(self):
        negative_bases = {"explicit_complaint", "abuse_or_threat", "strong_negative_evaluation"}
        if self.sentiment_label == "Negative" and self.sentiment_basis not in negative_bases:
            raise ValueError("Negative requires explicit strong-negative basis")
        if self.event_action == "continue_event" and self.related_event_id is None:
            raise ValueError("continue_event requires related_event_id")
        return self

class AnalysisPayload(BaseModel):
    events: list[EventAnalysis] = Field(min_length=1)
```

- [x] **Step 4: Verify GREEN**

Run: `./.venv/bin/python -m pytest -q tests/ai/test_ai_analysis_v2_schemas.py`
Expected: all tests pass.

- [x] **Step 5: Commit**

```bash
git add backend/ai/v2 tests/ai/test_ai_analysis_v2_schemas.py
git commit -m "feat(ai-v2): add strict analysis contracts"
```

### Task 2: Add V2 shadow schema and transactional repository

**Files:**
- Create: `backend/database/sql/ai_analysis_v2/create_tables.sql`
- Create: `backend/database/sql/ai_analysis_v2/drop_tables.sql`
- Create: `backend/database/sql/ai_analysis_v2/start_run.sql`
- Create: `backend/database/sql/ai_analysis_v2/complete_run.sql`
- Create: `backend/database/sql/ai_analysis_v2/fail_run.sql`
- Create: `backend/database/sql/ai_analysis_v2/insert_event.sql`
- Create: `backend/database/sql/ai_analysis_v2/insert_issue.sql`
- Create: `backend/database/sql/ai_analysis_v2/update_event.sql`
- Create: `backend/database/sql/ai_analysis_v2/upsert_customer_state.sql`
- Create: `backend/database/sql/ai_analysis_v2/get_buyer_analysis.sql`
- Create: `backend/database/sql/ai_analysis_v2/get_completed_run.sql`
- Create: `backend/ai/v2/repository.py`
- Create: `tests/database/test_ai_analysis_v2_repository.py`

**Interfaces:**
- Consumes: Task 1 Pydantic models and `backend.database.Database`.
- Produces: `AIAnalysisV2Repository.load_source()`, `start_run()`, `find_completed_run() -> CompletedRun | None`, `merge_existing()`, `persist_success()`, `persist_failure()`, `get_buyer_analysis()`.

- [x] **Step 1: Write failing transaction and idempotency tests**

```python
def test_failed_run_does_not_write_results_or_checkpoint():
    db = RecordingDatabase()
    repo = AIAnalysisV2Repository(db=db, sql_dir=TEST_SQL_DIR)
    repo.persist_failure(run_id=7, code="invalid_schema", message="bad payload")
    assert db.statement_names == ["fail_run.sql"]

def test_success_is_one_transaction():
    db = RecordingDatabase()
    repo = AIAnalysisV2Repository(db=db, sql_dir=TEST_SQL_DIR)
    repo.persist_success(run_id=7, buyer_nick="buyer", window=window(), payload=payload(), state=state())
    assert db.begin_count == 1
    assert db.commit_count == 1
    assert db.rollback_count == 0
    assert db.statement_names[-2:] == ["upsert_customer_state.sql", "complete_run.sql"]

def test_completed_fingerprint_short_circuits_duplicate_analysis():
    db = CompletedRunDatabase(run_id=7)
    repo = AIAnalysisV2Repository(db=db, sql_dir=TEST_SQL_DIR)
    completed = repo.find_completed_run("buyer", "abc", "v2.0")
    assert completed is not None
    assert completed.run_id == 7
    assert completed.payload == payload()
```

- [x] **Step 2: Verify RED**

Run: `./.venv/bin/python -m pytest -q tests/database/test_ai_analysis_v2_repository.py`
Expected: import failure for `AIAnalysisV2Repository`.

- [x] **Step 3: Create the five-table DDL**

```sql
CREATE TABLE IF NOT EXISTS ai_analysis_v2_runs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    buyer_nick VARCHAR(255) NOT NULL,
    analysis_mode ENUM('full','incremental') NOT NULL,
    status ENUM('running','completed','failed') NOT NULL DEFAULT 'running',
    provider VARCHAR(32), model VARCHAR(64), prompt_version VARCHAR(32) NOT NULL,
    source_fingerprint CHAR(64) NOT NULL,
    completed_fingerprint CHAR(64) NULL,
    source_from_msg_time DATETIME NULL, source_to_msg_time DATETIME NULL,
    source_message_count INT NOT NULL,
    result_payload JSON NULL,
    failure_code VARCHAR(64) NULL, failure_message VARCHAR(500) NULL,
    started_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME NULL,
    UNIQUE KEY uq_v2_completed (buyer_nick, completed_fingerprint, prompt_version),
    KEY idx_v2_runs_buyer_time (buyer_nick, started_at),
    KEY idx_v2_runs_status_time (status, started_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

In the same file create `ai_analysis_v2_events`, `ai_analysis_v2_issues`, `ai_analysis_v2_customer_state`, and `ai_analysis_v2_reviews` with every field and index enumerated in design sections 9.2-9.5. Add foreign keys only between V2 tables and use `ON DELETE RESTRICT`. Before running the DDL test, mechanically compare all five `CREATE TABLE` column lists against those design sections; a missing column fails this step.

- [x] **Step 4: Implement the SQL loader and transaction boundary**

```python
class AIAnalysisV2Repository:
    def __init__(self, db: Database | None = None, sql_dir: Path | None = None):
        self.db = db or Database(db_name=settings.db_name_to_use or "aliyunDB")
        self.sql_dir = sql_dir or Path(__file__).parents[2] / "database/sql/ai_analysis_v2"

    def _sql(self, name: str) -> str:
        return (self.sql_dir / name).read_text(encoding="utf-8")

    def persist_success(self, run_id: int, buyer_nick: str, payload: AnalysisPayload, state: CustomerState) -> None:
        with self.db.get_connection() as conn:
            try:
                conn.begin()
                with conn.cursor() as cursor:
                    self._write_events(cursor, run_id, buyer_nick, payload)
                    cursor.execute(self._sql("upsert_customer_state.sql"), state.to_sql_params(run_id))
                    cursor.execute(self._sql("complete_run.sql"), (payload.model_dump_json(), run_id))
                conn.commit()
            except Exception:
                conn.rollback()
                raise
```

- [x] **Step 5: Verify GREEN and DDL contract**

Run: `./.venv/bin/python -m pytest -q tests/database/test_ai_analysis_v2_repository.py`
Run: `rg -n "CREATE TABLE IF NOT EXISTS ai_analysis_v2_" backend/database/sql/ai_analysis_v2/create_tables.sql`
Expected: repository tests pass and exactly five CREATE TABLE matches appear.

- [x] **Step 6: Commit**

```bash
git add backend/ai/v2/repository.py backend/database/sql/ai_analysis_v2 tests/database/test_ai_analysis_v2_repository.py
git commit -m "feat(ai-v2): add shadow schema and repository"
```

### Task 3: Build deterministic message windows and semantic prompt

**Files:**
- Create: `backend/ai/v2/preprocessing.py`
- Create: `backend/ai/v2/prompt.py`
- Create: `tests/ai/test_ai_analysis_v2_preprocessing.py`
- Create: `tests/ai/test_ai_analysis_v2_prompt.py`

**Interfaces:**
- Consumes: raw `chat_history` rows and Task 1 taxonomy.
- Produces: `PreparedMessage`, `MessageWindow`, `prepare_windows()`, `build_analysis_prompt()`.

- [x] **Step 1: Write failing preparation tests**

```python
def test_prepare_windows_masks_identifiers_and_splits_after_24_hours():
    rows = chats_at("2026-07-01 09:00", "2026-07-02 10:01")
    rows[0]["content"] = "电话18812345678，订单3327506460762954752"
    windows = prepare_windows("buyer", rows)
    assert len(windows) == 2
    assert "18812345678" not in windows[0].messages[0].content
    assert "3327506460762954752" not in windows[0].messages[0].content

def test_incremental_window_includes_only_new_messages_plus_20_context_turns():
    windows = prepare_windows("buyer", rows, checkpoint=checkpoint, context_limit=20)
    assert all(m.msg_time > checkpoint for m in windows[0].new_messages)
    assert len(windows[0].context_messages) <= 20
```

- [x] **Step 2: Verify preprocessing RED**

Run: `./.venv/bin/python -m pytest -q tests/ai/test_ai_analysis_v2_preprocessing.py`
Expected: import failure for `prepare_windows`.

- [x] **Step 3: Implement deterministic preprocessing**

```python
PHONE_RE = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")
LONG_ID_RE = re.compile(r"(?<!\d)\d{12,}(?!\d)")
URL_RE = re.compile(r"https?://\S+")

def mask_content(content: str) -> str:
    content = URL_RE.sub("[链接]", content)
    content = PHONE_RE.sub("[手机号]", content)
    return LONG_ID_RE.sub("[长编号]", content).strip()

def fingerprint(messages: Sequence[PreparedMessage], prompt_version: str) -> str:
    source = "\n".join(f"{m.msg_time.isoformat()}|{m.role}|{m.content}" for m in messages)
    return hashlib.sha256(f"{prompt_version}\n{source}".encode()).hexdigest()
```

- [x] **Step 4: Write failing prompt tests**

```python
def test_prompt_requires_multiple_issues_and_controlled_codes():
    prompt = build_analysis_prompt(window(), open_events=[])
    assert '"events"' in prompt
    assert '"issues"' in prompt
    assert "不得创造新的 issue_code" in prompt
    assert "多个轻度不满不能累加升级为 Negative" in prompt
    assert "客服消息只提供语境" in prompt
```

- [x] **Step 5: Implement the prompt and verify GREEN**

The prompt must serialize the complete Task 1 JSON shape, list every taxonomy code, include the strict sentiment rules from `sentiment_intent_prompt.py`, explain `new_event` versus `continue_event`, and include only supplied open event IDs as legal `related_event_id` values.

Run: `./.venv/bin/python -m pytest -q tests/ai/test_ai_analysis_v2_preprocessing.py tests/ai/test_ai_analysis_v2_prompt.py`
Expected: all tests pass.

- [x] **Step 6: Commit**

```bash
git add backend/ai/v2/preprocessing.py backend/ai/v2/prompt.py tests/ai/test_ai_analysis_v2_preprocessing.py tests/ai/test_ai_analysis_v2_prompt.py
git commit -m "feat(ai-v2): prepare incremental windows and prompt"
```

### Task 4: Implement MiniMax-first V2 analysis orchestration

**Files:**
- Create: `backend/ai/v2/analyzer.py`
- Modify: `backend/ai/minimax_client.py`
- Modify: `backend/ai/deepseek_client.py`
- Create: `tests/ai/test_ai_analysis_v2_analyzer.py`

**Interfaces:**
- Consumes: Tasks 1-3 and existing OpenAI-compatible clients.
- Produces: `AIAnalysisV2Analyzer.analyze_buyer(buyer_nick: str, mode: Literal['full','incremental']) -> AnalysisRunResult`.

- [ ] **Step 1: Write failing provider-routing tests**

```python
def test_invalid_minimax_schema_retries_once_before_deepseek():
    minimax = SequenceClient([ValueError("schema"), valid_payload_json()])
    deepseek = RecordingClient()
    result = analyzer(minimax=minimax, deepseek=deepseek).analyze_buyer("buyer", "full")
    assert minimax.calls == 2
    assert deepseek.calls == 0
    assert result.provider == "minimax"

def test_all_provider_failures_only_record_failure():
    repo = RecordingRepository()
    with pytest.raises(AIAnalysisUnavailableError):
        analyzer(repo=repo, minimax=AlwaysFail(), deepseek=AlwaysFail()).analyze_buyer("buyer", "full")
    assert repo.successes == []
    assert len(repo.failures) == 1
    assert repo.checkpoint_updates == []

def test_low_value_customer_does_not_use_deepseek_after_minimax_failure():
    deepseek = RecordingClient(valid_payload_json())
    with pytest.raises(AIAnalysisUnavailableError):
        analyzer(minimax=AlwaysFail(), deepseek=deepseek, profile=low_value()).analyze_buyer("buyer", "full")
    assert deepseek.calls == 0
```

- [ ] **Step 2: Verify RED**

Run: `./.venv/bin/python -m pytest -q tests/ai/test_ai_analysis_v2_analyzer.py`
Expected: import failure for `AIAnalysisV2Analyzer`.

- [ ] **Step 3: Add raw V2 calls to existing clients**

```python
def analyze_v2(self, prompt: str) -> str:
    response = self.client.chat.completions.create(
        model=self.model,
        messages=[
            {"role": "system", "content": "你是电商客服事件与问题分析专家。只返回符合给定schema的JSON。"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )
    return response.choices[0].message.content or ""
```

MiniMax must not receive `max_tokens`. DeepSeek may use the existing shared maximum.

- [ ] **Step 4: Implement orchestration**

```python
class AIAnalysisV2Analyzer:
    PROMPT_VERSION = "ai-analysis-v2.0"

    def analyze_buyer(self, buyer_nick: str, mode: str = "incremental") -> AnalysisRunResult:
        source = self.repository.load_source(buyer_nick, mode)
        windows = prepare_windows(buyer_nick, source.chats, source.checkpoint, prompt_version=self.PROMPT_VERSION)
        if not windows:
            return AnalysisRunResult.skipped(buyer_nick, "no_new_messages")
        payloads = []
        last_provider = "cache"
        for window in windows:
            completed = self.repository.find_completed_run(buyer_nick, window.fingerprint, self.PROMPT_VERSION)
            if completed:
                payloads.append(completed.payload)
                last_provider = completed.provider or last_provider
                continue
            run_id = self.repository.start_run(buyer_nick, mode, window, self.PROMPT_VERSION)
            try:
                analyzed = self._analyze_window(window, source.open_events, source.profile)
                payload = analyzed.payload
                last_provider = analyzed.provider
                payloads.append(payload)
                state = build_customer_state(
                    self.repository.merge_existing(buyer_nick, payloads),
                    now=self.clock(),
                )
                self.repository.persist_success(
                    run_id=run_id,
                    buyer_nick=buyer_nick,
                    window=window,
                    payload=payload,
                    state=state,
                )
            except Exception as error:
                self.repository.persist_failure(run_id, type(error).__name__, str(error))
                raise AIAnalysisUnavailableError("AI Analysis V2 failed; retry later") from error
        state = self.repository.get_buyer_analysis(buyer_nick).customer_state
        return AnalysisRunResult.completed(buyer_nick, payloads, state, provider=last_provider)
```

`merge_existing()` deduplicates completed payloads by `source_fingerprint` and event/issue identity. `persist_success()` owns one database transaction for one window: insert/update events and issues, upsert the rolled-up state and checkpoint, then mark that run completed. A failed later window therefore leaves the last successful checkpoint retryable and does not erase earlier successful work. Cached windows carry their original provider; an all-cache run returns `cache` only if legacy data lacks provider metadata.

- [ ] **Step 5: Verify GREEN and existing failure contract**

Run: `./.venv/bin/python -m pytest -q tests/ai/test_ai_analysis_v2_analyzer.py tests/test_failed_analysis_not_cached.py`
Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/ai/v2/analyzer.py backend/ai/minimax_client.py backend/ai/deepseek_client.py tests/ai/test_ai_analysis_v2_analyzer.py
git commit -m "feat(ai-v2): analyze events with retryable provider routing"
```

### Task 5: Calculate current customer state and issue trends

**Files:**
- Create: `backend/ai/v2/rollup.py`
- Create: `tests/ai/test_ai_analysis_v2_rollup.py`
- Create: `backend/database/sql/ai_analysis_v2/get_issue_trends.sql`
- Create: `backend/database/sql/ai_analysis_v2/get_affected_buyers.sql`
- Modify: `backend/ai/v2/repository.py`
- Modify: `tests/database/test_ai_analysis_v2_repository.py`

**Interfaces:**
- Consumes: persisted events/issues.
- Produces: `issue_weight()`, `build_customer_state()`, `repository.get_issue_trends(filters)`.

- [x] **Step 1: Write failing decay tests**

```python
def test_new_open_medium_issue_outweighs_old_resolved_critical_issue():
    old = issue(severity="critical", status="resolved", age_days=200)
    new = issue(severity="medium", status="open", age_days=5)
    state = build_customer_state(events=[event_for(old), event_for(new)], now=NOW)
    assert state.primary_issue_code == new.issue_code

def test_recent_negative_sets_high_attention_priority():
    state = build_customer_state(events=[negative_event(age_days=2)], now=NOW)
    assert state.attention_priority == "high"

def test_stale_sentiment_becomes_unknown_after_90_days():
    state = build_customer_state(events=[neutral_event(age_days=91)], now=NOW)
    assert state.current_sentiment_label == "Unknown"
```

- [x] **Step 2: Verify RED**

Run: `./.venv/bin/python -m pytest -q tests/ai/test_ai_analysis_v2_rollup.py`
Expected: import failure for `build_customer_state`.

- [x] **Step 3: Implement exact decay and priority rules**

```python
SEVERITY_FACTOR = {"low": 1, "medium": 2, "high": 3, "critical": 4}
STATUS_FACTOR = {"open": 1.0, "explained_pending_acceptance": 0.7, "unknown": 0.5, "resolved": 0.15}

def recency_factor(age_days: int) -> float:
    if age_days <= 30: return 1.0
    if age_days <= 90: return 0.6
    if age_days <= 180: return 0.3
    return 0.1

def issue_weight(issue: PersistedIssue, now: datetime) -> float:
    age = max(0, (now - issue.last_seen_at).days)
    return SEVERITY_FACTOR[issue.severity] * STATUS_FACTOR[issue.status] * recency_factor(age)
```

Implement `urgent/high/medium/low` exactly as design section 8.

- [x] **Step 4: Add and verify trend SQL**

The query must return `issue_category`, `issue_code`, `event_count`, `affected_buyers`, `unresolved_count`, `high_severity_count`, `last_seen_at`, `current_period_count`, `previous_period_count`, and `change_percent`. It must use bound date parameters and optional `[[OPTIONAL_CONDITION]]` markers supported by the query loader.

Run: `./.venv/bin/python -m pytest -q tests/ai/test_ai_analysis_v2_rollup.py tests/database/test_ai_analysis_v2_repository.py`
Expected: all tests pass.

- [x] **Step 5: Commit**

```bash
git add backend/ai/v2/rollup.py backend/ai/v2/repository.py backend/database/sql/ai_analysis_v2 tests/ai/test_ai_analysis_v2_rollup.py tests/database/test_ai_analysis_v2_repository.py
git commit -m "feat(ai-v2): roll up customer state and issue trends"
```

### Task 6: Expose V2 analysis, trends, batch, and review APIs

**Files:**
- Create: `backend/api/ai_analysis_v2_routes.py`
- Modify: `backend/api/__init__.py`
- Modify: `backend/main.py`
- Create: `tests/api/test_ai_analysis_v2_routes.py`

**Interfaces:**
- Consumes: analyzer and repository from Tasks 2-5.
- Produces: all `/api/v2/ai-analysis-v2/*` endpoints from design section 11.

- [ ] **Step 1: Write failing API contract tests**

```python
def test_single_buyer_analysis_returns_events_issues_and_state(client, fake_analyzer):
    response = client.post("/api/v2/ai-analysis-v2/buyers/buyer/analyze?mode=full")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert len(body["events"][0]["issues"]) == 2
    assert body["customer_state"]["attention_priority"] == "high"

def test_failed_analysis_returns_503_and_remains_retryable(client, failing_analyzer):
    response = client.post("/api/v2/ai-analysis-v2/buyers/buyer/analyze?mode=incremental")
    assert response.status_code == 503
    assert response.json()["detail"]["retryable"] is True

def test_review_correction_requires_note(client):
    response = client.put("/api/v2/ai-analysis-v2/reviews/9", json={"action": "correct", "gold_payload": valid_payload(), "note": ""})
    assert response.status_code == 422
```

- [ ] **Step 2: Verify RED**

Run: `./.venv/bin/python -m pytest -q tests/api/test_ai_analysis_v2_routes.py`
Expected: 404 or import failure because the router is not registered.

- [ ] **Step 3: Implement request/response models and endpoints**

```python
router = APIRouter(prefix="/api/v2/ai-analysis-v2", tags=["ai_analysis_v2"])

class ReviewRequest(BaseModel):
    action: Literal["approve", "correct", "reject"]
    gold_payload: dict | None = None
    note: str = ""

    @model_validator(mode="after")
    def require_correction_data(self):
        if self.action in {"correct", "reject"} and not self.note.strip():
            raise ValueError("correction and rejection require a note")
        if self.action == "correct" and self.gold_payload is None:
            raise ValueError("correction requires gold_payload")
        return self

@router.post("/buyers/{buyer_nick}/analyze")
async def analyze_buyer_v2(buyer_nick: str, mode: Literal["full", "incremental"] = "incremental"):
    try:
        return await asyncio.to_thread(get_v2_analyzer().analyze_buyer, buyer_nick, mode)
    except AIAnalysisUnavailableError as error:
        raise HTTPException(503, detail={"message": str(error), "retryable": True})
```

Use existing `BatchTaskStatus` response fields and thread-safe cancellation semantics for the batch endpoints.

- [ ] **Step 4: Verify GREEN and route registration**

Run: `./.venv/bin/python -m pytest -q tests/api/test_ai_analysis_v2_routes.py`
Run: `./.venv/bin/python -c "from backend.main import app; assert any(r.path.startswith('/api/v2/ai-analysis-v2') for r in app.routes)"`
Expected: tests pass and the route assertion exits 0.

- [ ] **Step 5: Commit**

```bash
git add backend/api/ai_analysis_v2_routes.py backend/api/__init__.py backend/main.py tests/api/test_ai_analysis_v2_routes.py
git commit -m "feat(ai-v2): expose analysis and review APIs"
```

### Task 7: Integrate V2 customer state into the React application

**Files:**
- Create: `src/types/aiAnalysisV2.ts`
- Create: `src/components/ai-analysis-v2/CustomerV2StateCard.tsx`
- Modify: `src/api/client.ts`
- Modify: `src/views/ChatAnalysis.tsx`
- Modify: `src/App.tsx`

**Interfaces:**
- Consumes: Task 6 API payloads.
- Produces: typed client methods and customer state/history UI.

- [ ] **Step 1: Add exact TypeScript contracts**

```typescript
export type V2Sentiment = 'Positive' | 'Neutral' | 'Negative' | 'Unknown';
export type AttentionPriority = 'urgent' | 'high' | 'medium' | 'low';

export interface V2Issue {
  id: number;
  issue_category: string;
  issue_code: string;
  issue_detail: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  status: 'open' | 'explained_pending_acceptance' | 'resolved' | 'unknown';
  evidence_text: string;
}

export interface V2BuyerAnalysis {
  customer_state: V2CustomerState | null;
  events: V2Event[];
  issues: V2Issue[];
}
```

- [ ] **Step 2: Add API methods and build to expose type errors**

```typescript
async getAIAnalysisV2(buyerNick: string): Promise<V2BuyerAnalysis> {
  return this.request(`/api/v2/ai-analysis-v2/buyers/${encodeURIComponent(buyerNick)}`);
}

async analyzeBuyerV2(buyerNick: string, mode: 'full' | 'incremental'): Promise<V2AnalysisRunResult> {
  return this.request(`/api/v2/ai-analysis-v2/buyers/${encodeURIComponent(buyerNick)}/analyze?mode=${mode}`, { method: 'POST' });
}
```

Run: `PATH=/Users/novel/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin:$PATH npm run build`
Expected: build fails until `V2CustomerState`, `V2Event`, and the card props are fully defined.

- [ ] **Step 3: Implement the customer state card**

The card must render current sentiment, attention priority, primary issue, all unresolved issues, resolution status, recommended action, and an expandable event timeline. It must show an empty state when V2 has never run and a retryable error without replacing the previous successful result.

```tsx
export function CustomerV2StateCard({ analysis, onAnalyze, loading }: Props) {
  if (!analysis?.customer_state) {
    return (
      <NotionCard title="AI Analysis V2">
        <EmptyState
          title="尚未分析"
          action={<button disabled={loading} onClick={() => onAnalyze('full')}>生成分析</button>}
        />
      </NotionCard>
    );
  }
  const state = analysis.customer_state;
  const unresolved = analysis.issues.filter(issue => issue.status !== 'resolved');
  return (
    <NotionCard title="AI Analysis V2">
      <div className="flex gap-2 text-sm text-notion-text">
        <span>{state.current_sentiment_label}</span>
        <span>{state.attention_priority}</span>
      </div>
      <p className="mt-3 text-sm text-notion-text">{state.primary_issue_detail || '暂无主要问题'}</p>
      <ul className="mt-3 space-y-2">
        {unresolved.map(issue => (
          <li key={issue.id} className="border border-notion-border p-2 text-sm text-notion-text">
            <strong>{issue.issue_detail}</strong>
            <span className="ml-2 text-notion-muted">{issue.status}</span>
          </li>
        ))}
      </ul>
      <p className="mt-3 text-sm text-notion-text">{state.recommended_action || '暂无后续动作'}</p>
      <details className="mt-3 text-sm text-notion-text">
        <summary>历史事件（{analysis.events.length}）</summary>
        <ol className="mt-2 space-y-2">
          {analysis.events.map(event => <li key={event.id}>{event.summary}</li>)}
        </ol>
      </details>
    </NotionCard>
  );
}
```

- [ ] **Step 4: Verify build**

Run: `PATH=/Users/novel/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin:$PATH npm run build`
Expected: Vite build passes.

- [ ] **Step 5: Commit**

```bash
git add src/types/aiAnalysisV2.ts src/api/client.ts src/components/ai-analysis-v2/CustomerV2StateCard.tsx src/views/ChatAnalysis.tsx src/App.tsx
git commit -m "feat(ai-v2): show customer state and issue history"
```

### Task 8: Build issue trends and the 50-case review workbench

**Files:**
- Create: `src/views/AIAnalysisV2View.tsx`
- Create: `src/components/ai-analysis-v2/IssueTrendsPanel.tsx`
- Create: `src/components/ai-analysis-v2/ReviewWorkbench.tsx`
- Modify: `src/api/client.ts`
- Modify: `src/App.tsx`
- Create: `tests/playwright/test_ai_analysis_v2.py`

**Interfaces:**
- Consumes: trends and reviews endpoints.
- Produces: top-level “AI 问题洞察” navigation, trend drill-down, approve/correct/reject workflow.

- [ ] **Step 1: Write the failing Playwright happy path**

```python
def test_review_workbench_corrects_case_and_updates_progress(page, app_url):
    page.goto(app_url)
    page.get_by_role("button", name="AI 问题洞察").click()
    page.get_by_role("tab", name="人工审核").click()
    page.get_by_text("十八子李海旭").click()
    page.get_by_role("button", name="修改结果").click()
    page.get_by_label("最终情感").select_option("Neutral")
    page.get_by_label("审核备注").fill("真伪求证，不是明确投诉")
    page.get_by_role("button", name="确认并加入金标准").click()
    expect(page.get_by_text(re.compile(r"已审核\s+1\s*/\s*50"))).to_be_visible()
```

- [ ] **Step 2: Verify RED**

Run: `./.venv/bin/python -m pytest -q tests/playwright/test_ai_analysis_v2.py -k review_workbench`
Expected: navigation element “AI 问题洞察” is not found.

- [ ] **Step 3: Implement trends and review UI**

`IssueTrendsPanel` must expose 30/90/180-day controls and category, code, status, severity, and buyer-type filters. It must show issue count, affected buyers, unresolved count, high-severity count, period change, and affected-customer drill-down.

`ReviewWorkbench` must preserve the approved three-column layout: queue, complete dialogue, editable analysis. Use explicit high-contrast classes (`bg-slate-100`, `bg-white`, `text-slate-900`, `text-slate-600`) rather than inherited theme variables.

- [ ] **Step 4: Verify build and Playwright**

Run: `PATH=/Users/novel/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin:$PATH npm run build`
Run: `./.venv/bin/python -m pytest -q tests/playwright/test_ai_analysis_v2.py -k 'review_workbench or issue_trends'`
Expected: build and tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/views/AIAnalysisV2View.tsx src/components/ai-analysis-v2 src/api/client.ts src/App.tsx tests/playwright/test_ai_analysis_v2.py
git commit -m "feat(ai-v2): add issue trends and review workbench"
```

### Task 9: Generate, review, and score the 50-case gold cohort

**Files:**
- Create: `backend/ai/v2/cohort.py`
- Create: `backend/database/sql/ai_analysis_v2/select_review_candidates.sql`
- Create: `backend/database/sql/ai_analysis_v2/upsert_review.sql`
- Create: `scripts/prepare_ai_v2_review_cohort.py`
- Create: `scripts/evaluate_ai_v2_gold.py`
- Create: `tests/ai/test_ai_analysis_v2_cohort.py`
- Create: `docs/testing/ai-analysis-v2-acceptance-report.md`

**Interfaces:**
- Consumes: successful V2 events and reviews.
- Produces: exactly 50 distinct buyers across five 10-case strata and acceptance metrics.

- [ ] **Step 1: Write failing cohort tests**

```python
def test_cohort_has_five_strata_and_50_distinct_buyers():
    cohort = select_review_cohort(candidate_rows())
    assert len(cohort) == 50
    assert len({case.buyer_nick for case in cohort}) == 50
    assert Counter(case.stratum for case in cohort) == {
        "negative": 10,
        "ambiguity": 10,
        "product_after_sales": 10,
        "operations_friction": 10,
        "baseline": 10,
    }

def test_acceptance_metrics_use_reviewed_gold_only():
    metrics = calculate_acceptance_metrics(review_rows())
    assert metrics.reviewed_count == 50
    assert metrics.failed_result_count == 0
```

- [ ] **Step 2: Verify RED**

Run: `./.venv/bin/python -m pytest -q tests/ai/test_ai_analysis_v2_cohort.py`
Expected: import failure for `select_review_cohort`.

- [ ] **Step 3: Implement deterministic sampling and CLI**

```python
STRATA = ("negative", "ambiguity", "product_after_sales", "operations_friction", "baseline")

def select_review_cohort(rows: Sequence[Candidate], per_stratum: int = 10) -> list[Candidate]:
    selected, seen = [], set()
    for stratum in STRATA:
        candidates = sorted((row for row in rows if row.stratum == stratum), key=lambda row: (-row.risk_score, row.buyer_nick))
        for candidate in candidates:
            if candidate.buyer_nick in seen:
                continue
            selected.append(candidate)
            seen.add(candidate.buyer_nick)
            if sum(row.stratum == stratum for row in selected) == per_stratum:
                break
    if len(selected) != per_stratum * len(STRATA):
        raise ValueError("insufficient distinct candidates for review cohort")
    return selected
```

The preparation script defaults to `--dry-run`. `--write` inserts pending review rows only after the V2 schema exists. It must never alter V1 cache rows.

- [ ] **Step 4: Implement acceptance metrics and report generation**

The evaluator must compute reviewed count, Negative precision/recall, issue-presence agreement, issue-code agreement, resolution-status agreement, failed-result count, and duplicate-event count. It exits non-zero if any design threshold fails and writes the exact numerator/denominator for each metric.

- [ ] **Step 5: Verify unit tests**

Run: `./.venv/bin/python -m pytest -q tests/ai/test_ai_analysis_v2_cohort.py`
Expected: all tests pass.

- [ ] **Step 6: Execute the real review gate**

Run after non-production DDL is verified and production migration is explicitly approved:

```bash
./.venv/bin/python scripts/prepare_ai_v2_review_cohort.py --write --limit 50
./.venv/bin/python scripts/evaluate_ai_v2_gold.py --output docs/testing/ai-analysis-v2-acceptance-report.md
```

Expected: the first command reports five strata with 10 distinct buyers each. The evaluator remains red until all 50 cases have an `approved`, `corrected`, or `rejected` review decision; after review, all section 14.2 thresholds pass.

- [ ] **Step 7: Commit**

```bash
git add backend/ai/v2/cohort.py backend/database/sql/ai_analysis_v2 scripts/prepare_ai_v2_review_cohort.py scripts/evaluate_ai_v2_gold.py tests/ai/test_ai_analysis_v2_cohort.py docs/testing/ai-analysis-v2-acceptance-report.md
git commit -m "test(ai-v2): add 50-case gold review gate"
```

### Task 10: Gate Priority List cutover and complete deployment verification

**Files:**
- Create: `backend/database/sql/ai_analysis_v2/get_priority_customers.sql`
- Create: `backend/database/sql/ai_analysis_v2/get_priority_customers_count.sql`
- Modify: `backend/analytics/target_buyer_analyzer.py`
- Modify: `backend/api/target_routes.py`
- Modify: `src/api/client.ts`
- Modify: `src/components/dashboard/PriorityAttentionBoard.tsx`
- Create: `tests/integration/test_ai_analysis_v2_priority.py`
- Modify: `tests/playwright/test_ai_analysis_v2.py`
- Create: `docs/部署运维/AI_Analysis_V2_部署与回滚.md`

**Interfaces:**
- Consumes: passing Task 9 acceptance report.
- Produces: V2-first/V1-fallback Priority List, deployment and rollback evidence, full closed-loop verification.

- [ ] **Step 1: Write failing Priority integration tests**

```python
def test_recent_v2_negative_enters_priority_even_when_sales_priority_is_low(api_client, seeded_db):
    seeded_db.add_v2_state("buyer", sentiment="Negative", attention_priority="high")
    response = api_client.get("/api/v2/priority-customers?use_default_filter=true")
    assert "buyer" in {row["buyer_nick"] for row in response.json()["customers"]}

def test_neutral_customer_issue_contributes_to_trends_but_not_negative_priority(api_client, seeded_db):
    seeded_db.add_v2_issue("buyer", sentiment="Neutral", issue_code="material_expectation")
    trends = api_client.get("/api/v2/ai-analysis-v2/trends?days=30").json()
    assert any(row["issue_code"] == "material_expectation" for row in trends["items"])
    priority = api_client.get("/api/v2/priority-customers?use_default_filter=true").json()
    assert "buyer" not in {row["buyer_nick"] for row in priority["customers"]}
```

- [ ] **Step 2: Verify RED**

Run: `./.venv/bin/python -m pytest -q tests/integration/test_ai_analysis_v2_priority.py`
Expected: V2 state is ignored by existing Priority SQL.

- [ ] **Step 3: Implement V2-first, V1-fallback SQL**

The list and count SQL must remain structurally identical. Add `LEFT JOIN ai_analysis_v2_customer_state v2 ON v2.buyer_nick = tb.buyer_nick` and use:

```sql
COALESCE(v2.current_sentiment_label, ai.sentiment_label, tb.sentiment_label) AS sentiment_label,
v2.attention_priority,
v2.primary_issue_code,
v2.primary_issue_detail,
v2.highest_severity,
v2.active_issue_count
```

Default inclusion becomes existing sales conditions OR `v2.attention_priority IN ('urgent','high')`. Reactivation requires `v2.last_event_at > csl.updated_at`; old V1 incremental Negative logic remains fallback when no V2 state exists.

- [ ] **Step 4: Add deployment and rollback commands**

The deployment document must include:

```bash
mysql --database smokesignal_v2_test < backend/database/sql/ai_analysis_v2/create_tables.sql
./.venv/bin/python -m pytest -q tests/ai/test_ai_analysis_v2_*.py tests/database/test_ai_analysis_v2_repository.py tests/api/test_ai_analysis_v2_routes.py tests/integration/test_ai_analysis_v2_priority.py
PATH=/Users/novel/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin:$PATH npm run build
./.venv/bin/python -m pytest -q tests/playwright/test_ai_analysis_v2.py
```

Production DDL and Priority cutover commands must be separated into explicit approval steps. Rollback switches Priority queries back to V1 before `drop_tables.sql`; it does not delete V2 tables automatically.

- [ ] **Step 5: Run the full completion audit**

Run fresh and record exact outputs:

```bash
./.venv/bin/python -m pytest -q tests/ai/test_ai_analysis_v2_*.py
./.venv/bin/python -m pytest -q tests/database/test_ai_analysis_v2_repository.py tests/api/test_ai_analysis_v2_routes.py tests/integration/test_ai_analysis_v2_priority.py
./.venv/bin/python -m pytest -q tests/test_failed_analysis_not_cached.py
PATH=/Users/novel/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin:$PATH npm run build
./.venv/bin/python -m pytest -q tests/playwright/test_ai_analysis_v2.py
./.venv/bin/python scripts/evaluate_ai_v2_gold.py --output docs/testing/ai-analysis-v2-acceptance-report.md
git diff --check
```

Expected: zero test failures, frontend build exit 0, `git diff --check` exit 0, 50 reviewed cases, and every acceptance threshold green.

- [ ] **Step 6: Commit**

```bash
git add backend/database/sql/ai_analysis_v2 backend/analytics/target_buyer_analyzer.py backend/api/target_routes.py src/api/client.ts src/components/dashboard/PriorityAttentionBoard.tsx tests/integration/test_ai_analysis_v2_priority.py tests/playwright/test_ai_analysis_v2.py docs/部署运维/AI_Analysis_V2_部署与回滚.md docs/testing/ai-analysis-v2-acceptance-report.md
git commit -m "feat(ai-v2): complete priority cutover and acceptance gate"
```

## Execution Checkpoints

1. After Task 4: review real MiniMax output for the five already validated customers without persisting V2 data.
2. After Task 6: review API contracts and failure behavior.
3. After Task 8: visually inspect the trends and review pages in the in-app browser.
4. Before Task 9 writes data: obtain explicit approval for the V2 schema migration target.
5. Before Task 10 cutover: confirm the 50-case report passes and obtain explicit production approval.
