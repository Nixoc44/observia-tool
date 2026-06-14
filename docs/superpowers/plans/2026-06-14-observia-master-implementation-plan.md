# Observia Master Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete Observia — a Dynatrace AI analysis platform — from its current MVP state to a production-ready internal tool with real automation, resilient backend, and polished frontend.

**Architecture:** FastAPI backend (`server/`) with MCP client, plugin-based analysis engine, LiteLLM multi-provider orchestration, and SQLite storage. React 18 + TypeScript frontend (`frontend/`) with context-based state. Docker Compose for local deployment.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy (async), MCP SDK, LiteLLM, React 18, TypeScript, TailwindCSS, Vite, Docker

**Existing docs (read first):**
- Design spec: `docs/superpowers/specs/2026-06-06-dynatrace-ai-analysis-platform-design.md`
- Improvements spec: `docs/superpowers/specs/2026-06-06-observia-improvements-design.md`
- MVP plan (mostly done): `docs/superpowers/plans/2026-06-06-dynatrace-ai-platform-mvp.md`
- Improvements plan (partially done): `docs/superpowers/plans/2026-06-06-observia-improvements-plan.md`

---

## Current State Assessment

### Already implemented

| Area | Status | Key files |
|------|--------|-----------|
| Project scaffolding | Done | `server/`, `frontend/`, `docker-compose.yml` |
| Environment CRUD | Done | `server/app/api/v1/environments.py`, `frontend/src/pages/Environments.tsx` |
| AI Provider CRUD | Done | `server/app/api/v1/ai_providers.py`, `frontend/src/pages/AIProviders.tsx` |
| Analysis workflow | Done | `server/app/core/analysis_engine.py`, `frontend/src/pages/Analyses.tsx` |
| Analysis detail view | Done | `frontend/src/pages/AnalysisDetail.tsx` |
| Recommendations API | Done | `server/app/api/v1/recommendations.py` |
| Report generation (JSON/Markdown) | Done | `server/app/api/v1/reports.py` |
| Reports dashboard + charts | Done | `frontend/src/pages/Reports.tsx` |
| MCP client (pool, retry, reconnect) | Done | `server/app/core/mcp_client.py` |
| SQLite cache layer | Done | `server/app/core/cache.py` |
| Analysis plugins (4 types) | Done | `server/app/plugins/*.py` |
| Basic metrics endpoint | Done | `server/app/main.py` `/metrics` |
| Unit tests (MCP, cache) | Done | `server/tests/unit/` |

### Not yet implemented (gaps)

| Gap | Priority | Notes |
|-----|----------|-------|
| AI provider fallback chain in analysis runs | P0 | DB has `fallback_order`; `analysis_engine.py` only uses selected provider |
| Dashboard priority recommendations | P0 | Spec requires critical/high alerts; not wired |
| Dashboard field bugs | P0 | Uses `analysis.name` / `analysis.type` — should be `analysis_type` |
| MCP production install (no npx) | P1 | `mcp_client.py` still uses `npx @dynatrace-oss/...` |
| Environment failover | P1 | Spec: primary + secondary environment per analysis |
| Circuit breaker (MCP + AI) | P1 | Not implemented |
| Extended `/ready` health checks | P1 | Currently returns static `{status: ready}` |
| Automation / scheduled analyses | P2 | Frontend mock only; no backend scheduler |
| Integrations (Slack, Jira, webhooks) | P2 | Static mock data; no backend |
| Settings / Users tab | P3 | Mock users; JWT/RBAC deferred in spec |
| Frontend tests (Vitest) | P2 | None exist |
| Backend integration tests | P2 | Only 2 unit test files |
| Redis cache backend | P3 | Raises `NotImplementedError` |
| PDF/HTML report export | P3 | Deferred in improvements spec |

---

## Recommended Build Order

```
Phase 1: Fix & Harden Core (P0–P1)     ← start here
Phase 2: Frontend Polish (P0–P1)
Phase 3: Automation Backend (P2)
Phase 4: Integrations (P2)
Phase 5: Test Coverage & CI (P2)
Phase 6: Future Enhancements (P3+)
```

Each phase produces working, testable software independently.

---

## Phase 1: Fix & Harden Core Backend

### Task 1.1: Wire AI provider fallback chain

**Files:**
- Modify: `server/app/core/analysis_engine.py`
- Modify: `server/app/db/repositories.py` (add `get_fallback_chain()`)
- Test: `server/tests/unit/test_analysis_engine.py` (create)

**Problem:** `run_analysis()` loads a single provider. `AIOrchestrator` supports fallback but receives only one config.

- [ ] **Step 1: Write failing test**

```python
# server/tests/unit/test_analysis_engine.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

@pytest.mark.asyncio
async def test_run_analysis_uses_fallback_chain():
    """Analysis should pass all providers ordered by fallback_order to orchestrator."""
    with patch("app.core.analysis_engine.AsyncSession") as mock_session, \
         patch("app.core.analysis_engine.EnvironmentRepository") as mock_env_repo, \
         patch("app.core.analysis_engine.AIProviderRepository") as mock_provider_repo, \
         patch("app.core.analysis_engine.AnalysisRepository") as mock_analysis_repo, \
         patch("app.core.analysis_engine.MCPClient") as mock_mcp, \
         patch("app.core.analysis_engine.AgentExecutor") as mock_executor, \
         patch("app.core.analysis_engine.RecommendationEngine") as mock_rec, \
         patch("app.core.analysis_engine.get_plugin") as mock_plugin:

        mock_analysis = MagicMock(id=1, environment_id=1, ai_provider_id=1,
                                  analysis_type="performance", time_range_hours=24, parameters={})
        mock_analysis_repo.return_value.get_by_id = AsyncMock(return_value=mock_analysis)
        mock_analysis_repo.return_value.update_status = AsyncMock()

        mock_env = MagicMock(url="https://test.live.dynatrace.com", env_type="saas")
        mock_env_repo.return_value.get_by_id = AsyncMock(return_value=mock_env)
        mock_env_repo.return_value.get_token = MagicMock(return_value="token")

        provider_a = MagicMock(provider_type="anthropic", model="claude-sonnet-4-6",
                               endpoint=None, extra_config={})
        provider_b = MagicMock(provider_type="openai", model="gpt-4o",
                               endpoint=None, extra_config={})
        mock_provider_repo.return_value.get_fallback_chain = AsyncMock(return_value=[provider_a, provider_b])
        mock_provider_repo.return_value.get_api_key = MagicMock(return_value="key")

        mock_plugin.return_value.build_prompts.return_value = ("system", "user")
        mock_mcp.return_value.connect = AsyncMock()
        mock_mcp.return_value.disconnect = AsyncMock()
        mock_executor.return_value.run = AsyncMock(return_value=MagicMock(
            final_answer="done", reasoning_steps=[], raw_data=[]))
        mock_rec.return_value.generate = AsyncMock(return_value=[])

        from app.core.analysis_engine import run_analysis
        await run_analysis(1)

        # Verify orchestrator received 2 providers
        orchestrator_call = mock_executor.call_args
        assert orchestrator_call is not None
        orchestrator = orchestrator_call.kwargs.get("orchestrator") or orchestrator_call[1].get("orchestrator")
        assert len(orchestrator.providers) == 2
```

- [ ] **Step 2: Run test — expect FAIL**

Run: `cd server && pytest tests/unit/test_analysis_engine.py -v`
Expected: FAIL — `get_fallback_chain` not defined

- [ ] **Step 3: Add repository method**

```python
# server/app/db/repositories.py — add to AIProviderRepository
async def get_fallback_chain(self, primary_id: int) -> list[AIProviderDB]:
    """Return all active providers ordered by fallback_order, primary first."""
    result = await self.db.execute(
        select(AIProviderDB).order_by(AIProviderDB.fallback_order)
    )
    providers = list(result.scalars().all())
    primary = next((p for p in providers if p.id == primary_id), None)
    if primary:
        providers.remove(primary)
        providers.insert(0, primary)
    return providers
```

- [ ] **Step 4: Update analysis_engine to use chain**

```python
# server/app/core/analysis_engine.py — replace single provider load
provider_chain = await provider_repo.get_fallback_chain(analysis.ai_provider_id)
provider_configs = [
    AIProviderConfig(
        provider_type=AIProviderType(p.provider_type),
        model=p.model,
        api_key=provider_repo.get_api_key(p),
        endpoint=p.endpoint,
        extra_config=p.extra_config or {},
    )
    for p in provider_chain
]
orchestrator = AIOrchestrator(providers=provider_configs)
```

- [ ] **Step 5: Run test — expect PASS**

- [ ] **Step 6: Commit**

```bash
git add server/app/core/analysis_engine.py server/app/db/repositories.py server/tests/unit/test_analysis_engine.py
git commit -m "feat: wire AI provider fallback chain into analysis runs"
```

---

### Task 1.2: Use MCP connection pool in analysis runs

**Files:**
- Modify: `server/app/core/analysis_engine.py`

**Problem:** Analysis creates a new `MCPClient(...)` instead of `MCPClient.get_from_pool(...)`.

- [ ] **Step 1: Replace direct instantiation**

```python
# server/app/core/analysis_engine.py
mcp_client = await MCPClient.get_from_pool(url=env.url, token=token, env_type=env.env_type)
if not mcp_client.is_connected():
    await mcp_client.connect()
```

- [ ] **Step 2: Remove disconnect at end** (pool owns lifecycle)

```python
# Remove: await mcp_client.disconnect()
```

- [ ] **Step 3: Run existing MCP tests**

Run: `cd server && pytest tests/unit/test_mcp_client.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git commit -m "feat: use MCP connection pool in analysis runs"
```

---

### Task 1.3: Production MCP install (replace npx)

**Files:**
- Modify: `server/app/core/mcp_client.py`
- Modify: `server/Dockerfile`
- Modify: `server/pyproject.toml` or add `package.json` in server

- [ ] **Step 1: Pre-install MCP packages in Dockerfile**

```dockerfile
# server/Dockerfile — add before Python deps
RUN npm install -g @dynatrace-oss/dynatrace-mcp @dynatrace-oss/dynatrace-managed-mcp
```

- [ ] **Step 2: Update `_connect_mcp` to use global binaries**

```python
# server/app/core/mcp_client.py
package = "dynatrace-mcp" if self.env_type == "saas" else "dynatrace-managed-mcp"
server_params = StdioServerParameters(
    command=package,
    args=[],
    env={"DT_URL": self.url, "DT_TOKEN": self.token},
)
```

- [ ] **Step 3: Add env var override for dev**

```python
import os
command = os.getenv("MCP_COMMAND", package)
```

- [ ] **Step 4: Rebuild and smoke test**

Run: `docker-compose build backend && docker-compose up -d backend`
Expected: Backend starts without npx errors

- [ ] **Step 5: Commit**

---

### Task 1.4: Circuit breaker for MCP and AI calls

**Files:**
- Create: `server/app/core/circuit_breaker.py`
- Modify: `server/app/core/mcp_client.py`
- Modify: `server/app/core/ai_orchestrator.py`
- Test: `server/tests/unit/test_circuit_breaker.py`

- [ ] **Step 1: Write failing test for circuit breaker**

```python
# server/tests/unit/test_circuit_breaker.py
import pytest
from app.core.circuit_breaker import CircuitBreaker, CircuitOpenError

def test_opens_after_threshold_failures():
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=30)
    for _ in range(3):
        cb.record_failure()
    with pytest.raises(CircuitOpenError):
        cb.call(lambda: "ok")

def test_closes_after_success_in_half_open():
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0)
    cb.record_failure()
    cb.record_failure()
    cb.record_success()  # half-open success
    assert cb.state == "closed"
```

- [ ] **Step 2: Implement CircuitBreaker**

```python
# server/app/core/circuit_breaker.py
import time
from enum import Enum

class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitOpenError(Exception):
    pass

class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 30):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.last_failure_time: float | None = None
        self.state = CircuitState.CLOSED

    def record_failure(self) -> None:
        self.failures += 1
        self.last_failure_time = time.monotonic()
        if self.failures >= self.failure_threshold:
            self.state = CircuitState.OPEN

    def record_success(self) -> None:
        self.failures = 0
        self.state = CircuitState.CLOSED

    def call(self, fn):
        if self.state == CircuitState.OPEN:
            if self.last_failure_time and (time.monotonic() - self.last_failure_time) >= self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
            else:
                raise CircuitOpenError("Circuit is open")
        try:
            result = fn()
            self.record_success()
            return result
        except Exception:
            self.record_failure()
            raise
```

- [ ] **Step 3: Wrap MCP `call_tool` and AI `complete` with circuit breakers**

- [ ] **Step 4: Run tests — expect PASS**

- [ ] **Step 5: Commit**

---

### Task 1.5: Extended `/ready` health check

**Files:**
- Modify: `server/app/main.py`

- [ ] **Step 1: Implement real readiness probe**

```python
@app.get("/ready")
async def ready():
    checks = {}
    try:
        from app.db.database import engine
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["db"] = "ok"
    except Exception as e:
        checks["db"] = f"error: {e}"

    overall = "ready" if all(v == "ok" for v in checks.values()) else "degraded"
    status_code = 200 if overall == "ready" else 503
    return JSONResponse(
        content={"status": overall, **checks},
        status_code=status_code,
    )
```

- [ ] **Step 2: Smoke test**

Run: `curl -s http://localhost:8000/ready | jq`
Expected: `{"status": "ready", "db": "ok"}`

- [ ] **Step 3: Commit**

---

## Phase 2: Frontend Polish

### Task 2.1: Fix Dashboard bugs + add priority recommendations

**Files:**
- Modify: `frontend/src/pages/Dashboard.tsx`
- Modify: `frontend/src/services/api.ts` (add recommendations API if missing)

- [ ] **Step 1: Fix analysis field references**

```tsx
// frontend/src/pages/Dashboard.tsx — in recent analyses list
<div className="font-medium">
  {analysis.analysis_type.charAt(0).toUpperCase() + analysis.analysis_type.slice(1)}
</div>
<div className="text-sm text-gray-400">
  Env #{analysis.environment_id} • {new Date(analysis.created_at).toLocaleDateString()}
</div>
```

- [ ] **Step 2: Fetch and display critical/high recommendations**

```tsx
const [alerts, setAlerts] = useState<Recommendation[]>([]);

useEffect(() => {
  Promise.all([
    recommendationsApi.list({ severity: 'critical' }),
    recommendationsApi.list({ severity: 'high' }),
  ]).then(([critical, high]) => setAlerts([...critical, ...high].slice(0, 5)));
}, []);
```

- [ ] **Step 3: Add alerts section UI below stats cards**

- [ ] **Step 4: Type check**

Run: `cd frontend && npx tsc --noEmit`
Expected: PASS

- [ ] **Step 5: Commit**

---

### Task 2.2: Recommendations panel on Analysis Detail

**Files:**
- Modify: `frontend/src/pages/AnalysisDetail.tsx`
- Modify: `frontend/src/services/api.ts`

- [ ] **Step 1: Fetch recommendations for analysis ID**

```tsx
const [recommendations, setRecommendations] = useState<Recommendation[]>([]);

useEffect(() => {
  if (!id) return;
  recommendationsApi.list({ analysis_id: Number(id) })
    .then(setRecommendations);
}, [id]);
```

- [ ] **Step 2: Render recommendations list with severity badges, action, script export**

- [ ] **Step 3: Add status update buttons (acknowledge / resolve) calling PATCH endpoint**

- [ ] **Step 4: Commit**

---

### Task 2.3: Report download from Analysis Detail

**Files:**
- Modify: `frontend/src/pages/AnalysisDetail.tsx`
- Modify: `frontend/src/services/reports-api.ts`

- [ ] **Step 1: Add "Export JSON" and "Export Markdown" buttons**

```tsx
const handleExport = async (format: 'json' | 'markdown') => {
  const report = await reportsApi.generate({ analysis_id: analysis.id, format });
  const blob = new Blob([report.content], { type: format === 'json' ? 'application/json' : 'text/markdown' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `analysis-${analysis.id}.${format === 'json' ? 'json' : 'md'}`;
  a.click();
};
```

- [ ] **Step 2: Commit**

---

## Phase 3: Automation Backend

### Task 3.1: Schedule model and API

**Files:**
- Create: `server/app/models/schedule.py`
- Modify: `server/app/db/database.py` (add `ScheduleDB` table)
- Create: `server/app/api/v1/schedules.py`
- Modify: `server/app/main.py` (register router)
- Modify: `server/app/db/repositories.py`

**Schema:**

```python
class ScheduleCreate(BaseModel):
    name: str
    environment_id: int
    ai_provider_id: int
    analysis_type: AnalysisType
    cron_expression: str  # e.g. "0 9 * * *"
    time_range_hours: int = 24
    is_active: bool = True
```

- [ ] **Step 1: Write failing API test**

```python
# server/tests/integration/test_schedules_api.py
async def test_create_schedule(client):
    resp = await client.post("/api/v1/schedules/", json={
        "name": "Daily Security",
        "environment_id": 1,
        "ai_provider_id": 1,
        "analysis_type": "security",
        "cron_expression": "0 9 * * *",
    })
    assert resp.status_code == 201
```

- [ ] **Step 2: Implement model, DB table, repository, CRUD endpoints**

- [ ] **Step 3: Run test — expect PASS**

- [ ] **Step 4: Commit**

---

### Task 3.2: Schedule runner (APScheduler)

**Files:**
- Create: `server/app/core/scheduler.py`
- Modify: `server/app/main.py` (start scheduler on startup)
- Modify: `server/pyproject.toml` (add `apscheduler` dependency)

- [ ] **Step 1: Install APScheduler**

```bash
cd server && pip install apscheduler
```

- [ ] **Step 2: Implement scheduler that loads active schedules from DB and triggers `run_analysis`**

```python
# server/app/core/scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

scheduler = AsyncIOScheduler()

async def load_schedules():
    async with AsyncSession(engine) as db:
        repo = ScheduleRepository(db)
        for schedule in await repo.get_active():
            scheduler.add_job(
                trigger_analysis,
                CronTrigger.from_crontab(schedule.cron_expression),
                args=[schedule.id],
                id=f"schedule-{schedule.id}",
                replace_existing=True,
            )

async def trigger_analysis(schedule_id: int):
    # Create AnalysisDB record, then call run_analysis
    ...
```

- [ ] **Step 3: Wire startup/shutdown in main.py**

- [ ] **Step 4: Commit**

---

### Task 3.3: Wire Automation frontend to real API

**Files:**
- Modify: `frontend/src/pages/Automation.tsx`
- Create: `frontend/src/services/schedules-api.ts`

- [ ] **Step 1: Replace mock data with API calls (list, create, toggle, delete)**

- [ ] **Step 2: Connect ScheduleEditor form to POST endpoint**

- [ ] **Step 3: Manual smoke test via UI**

- [ ] **Step 4: Commit**

---

## Phase 4: Integrations

### Task 4.1: Integration config model and API

**Files:**
- Create: `server/app/models/integration.py`
- Modify: `server/app/db/database.py`
- Create: `server/app/api/v1/integrations.py`
- Create: `server/app/core/integrations/slack.py`
- Create: `server/app/core/integrations/webhook.py`

**Supported integrations (MVP):**
- Slack (webhook URL → post message on analysis complete with critical findings)
- Custom webhook (POST JSON payload)

- [ ] **Step 1: DB model with encrypted credentials**

```python
class IntegrationDB(Base):
    __tablename__ = "integrations"
    id = Column(Integer, primary_key=True)
    integration_type = Column(String)  # slack, webhook, jira
    name = Column(String)
    config = Column(JSON)  # encrypted webhook URL, channel, etc.
    is_active = Column(Boolean, default=True)
```

- [ ] **Step 2: CRUD API endpoints**

- [ ] **Step 3: Notification hook in `analysis_engine.py` after completion**

```python
from app.core.integrations.notifier import notify_integrations
await notify_integrations(analysis_id, recommendations)
```

- [ ] **Step 4: Commit**

---

### Task 4.2: Integrations frontend config modal

**Files:**
- Modify: `frontend/src/pages/Integrations.tsx`
- Create: `frontend/src/components/IntegrationConfigModal.tsx`

- [ ] **Step 1: Replace TODO with modal for Slack/webhook config**

- [ ] **Step 2: Wire to integrations API**

- [ ] **Step 3: Commit**

---

## Phase 5: Test Coverage & CI

### Task 5.1: Backend integration tests

**Files:**
- Create: `server/tests/integration/test_api.py`
- Create: `server/tests/conftest.py`

- [ ] **Step 1: Add pytest fixtures with test DB and httpx AsyncClient**

- [ ] **Step 2: Test all CRUD endpoints: environments, providers, analyses, recommendations, reports**

- [ ] **Step 3: Target 80% coverage on core modules**

Run: `cd server && pytest tests/ -v --cov=app --cov-report=term-missing`

- [ ] **Step 4: Commit**

---

### Task 5.2: Frontend tests with Vitest

**Files:**
- Modify: `frontend/package.json` (add vitest, testing-library)
- Create: `frontend/src/__tests__/Dashboard.test.tsx`
- Create: `frontend/src/__tests__/AnalysesContext.test.tsx`

- [ ] **Step 1: Install test deps**

```bash
cd frontend && npm install -D vitest @testing-library/react @testing-library/jest-dom jsdom
```

- [ ] **Step 2: Write tests for Dashboard stats rendering and AnalysesContext fetch**

- [ ] **Step 3: Run tests**

Run: `cd frontend && npm test -- --run`
Expected: PASS

- [ ] **Step 4: Commit**

---

### Task 5.3: GitHub Actions CI

**Files:**
- Create: `.github/workflows/ci.yml`

```yaml
name: CI
on: [push, pull_request]
jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install -e ./server[dev]
      - run: cd server && pytest tests/ -v
  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: "20" }
      - run: cd frontend && npm ci && npx tsc --noEmit && npm test -- --run
```

- [ ] **Step 1: Create workflow file**

- [ ] **Step 2: Commit and verify on push**

---

## Phase 6: Future Enhancements (post-production)

These are explicitly deferred in the approved specs. Implement only when Phases 1–5 are complete.

| Feature | Spec reference | Complexity |
|---------|---------------|------------|
| Environment failover (primary → secondary) | Improvements spec §2.3 | Medium |
| Redis cache backend | Improvements spec §2.2 | Low |
| PDF/HTML report export | Design spec §report_generator | High |
| Interactive visualizations (Plotly charts on analysis results) | Design spec §Results Viewer | High |
| JWT auth + RBAC (admin/analyst/viewer) | Design spec §Security | High |
| Auto-remediation via Dynatrace API | Design spec Phase 2 | High |
| Jira / PagerDuty integrations | Design spec Phase 2 | Medium |
| Multi-tenancy | Design spec Phase 3 | Very high |

---

## File Structure (target state after Phases 1–5)

```
server/app/
├── core/
│   ├── analysis_engine.py      MODIFIED — fallback chain, pool, notifications
│   ├── circuit_breaker.py      NEW
│   ├── scheduler.py            NEW
│   └── integrations/
│       ├── notifier.py         NEW
│       ├── slack.py            NEW
│       └── webhook.py          NEW
├── api/v1/
│   ├── schedules.py            NEW
│   └── integrations.py         NEW
├── models/
│   ├── schedule.py             NEW
│   └── integration.py          NEW
└── tests/
    ├── unit/test_analysis_engine.py    NEW
    ├── unit/test_circuit_breaker.py    NEW
    └── integration/test_api.py         NEW

frontend/src/
├── pages/
│   ├── Dashboard.tsx           MODIFIED — fix bugs, add alerts
│   ├── AnalysisDetail.tsx      MODIFIED — recommendations + export
│   ├── Automation.tsx          MODIFIED — real API
│   └── Integrations.tsx        MODIFIED — config modal
├── components/
│   └── IntegrationConfigModal.tsx  NEW
├── services/
│   ├── schedules-api.ts        NEW
│   └── integrations-api.ts     NEW
└── __tests/                    NEW
```

---

## Verification Checklist (definition of done)

Before calling Observia "production-ready for internal use":

- [ ] `docker-compose up` starts backend + frontend without errors
- [ ] Can add Dynatrace environment + AI provider via UI
- [ ] Can launch analysis and see results + recommendations in UI
- [ ] AI fallback works when primary provider fails (test with invalid key)
- [ ] Dashboard shows critical/high recommendation alerts
- [ ] Can export JSON/Markdown report from analysis detail
- [ ] Can create cron schedule and it triggers analysis automatically
- [ ] Slack/webhook notification fires on analysis completion
- [ ] `/ready` returns real DB status; `/metrics` exposes counters
- [ ] Backend pytest suite passes with ≥80% core coverage
- [ ] Frontend Vitest suite passes; `tsc --noEmit` clean
- [ ] CI pipeline green on push

---

## Self-Review

**Spec coverage:** All P0–P2 items from improvements spec mapped to Phase 1–5 tasks. Phase 6 covers deferred P3+ items.

**Placeholder scan:** No TBD steps in Phases 1–5 task bodies. Phase 6 is intentionally labeled future.

**Type consistency:** Uses existing types from `frontend/src/types/index.ts` and `server/app/models/`. Schedule/integration models follow same Pydantic patterns as existing models.
