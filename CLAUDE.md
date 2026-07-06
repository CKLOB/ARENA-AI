# CLAUDE.md

Guide for working in the FastAPI AI service repo.

## Project Context

AI service for a mock investment battle platform. This repo owns everything related to AI decision-making: trading bot logic, recommendation generation, SHAP-based explainability, and model retraining. The Spring Boot backend calls this service over HTTP and never implements decision logic itself — that boundary must be respected in both directions.

- This is not a real trading service (education positioning). Decisions here exist to teach users, not to maximize trade volume.

## Stack

- FastAPI, Python 3.11+
- LightGBM — trading decisions and recommendations. **The only model that gets retrained.**
- SHAP — decision explainability (feeds the observability dashboard)
- MLflow — model version management
- pandas — backtesting, feature engineering
- OpenAI SDK — GPT-5.4 mini, feedback text generation only
- PostgreSQL (dedicated schema/instance for this service, separate from the Spring Boot DB)

## Directory Structure

Domain-based, not layer-first:

```
app/
  trading_ai/       # LightGBM trading decision logic
  recommendation/   # Recommendation card generation (reuses trading_ai model)
  feedback/         # GPT-5.4 mini feedback generation
  observability/    # SHAP computation, decision log writes
  mlops/            # Retraining, backtesting, MLflow integration
  shared/           # Common schemas, market enum, config
```

## Model Responsibilities — Do Not Mix These Up

| Function | Model | Retrained? |
|---|---|---|
| Trading bot decisions | LightGBM | **Yes** — the only retraining target |
| Recommendation cards | LightGBM | Same model, reused |
| Challenge feedback text | GPT-5.4 mini | **No** — inference call only |
| Challenge result report | GPT-5.4 mini | Same as above |

GPT-5.4 mini does not support fine-tuning (OpenAI has been sunsetting the fine-tuning API since May 2026). Never attempt to fine-tune it. Never let GPT influence a trading decision, and never let LightGBM generate free text.

## Boundary with the Spring Boot Backend

- This service does not own trading domain logic (order execution, balance, challenge settlement). Spring Boot calls this service's endpoints and handles the transactional side itself.
- Every decision-making endpoint (`/trading-ai/decide`, `/recommendation/generate`) must write a decision log as part of the same request — not as an afterthought.
- If an endpoint's request/response shape changes, update the OpenAPI schema so Spring Boot's client code stays in sync.

## Database

- This service uses its **own PostgreSQL schema/instance**, separate from the Spring Boot database (agreed to avoid migration conflicts and isolate high-frequency decision log writes).
- `decision_log` rows reference Spring Boot entities (`challenge_id`, `order_id`) by ID only — there is no foreign key constraint across databases. Referential integrity for these fields must be handled at the application level, not assumed at the DB level.

## Market Handling

- Market type: `KR | US | COIN` enum, always modeled as three even though only two are active.
- Currently active: `US`, `COIN`. `KR` is disabled pending a brokerage account.
- Feature engineering (moving averages, RSI, volume, MACD, volatility) must be computed per market — do not assume shared thresholds across markets with different volatility profiles.

## Decision Logging Requirements (non-negotiable)

Every time `/trading-ai/decide` or `/recommendation/generate` is called, persist:
- Feature snapshot at decision time
- Model output (probability)
- Action taken
- Model version

Without this, SHAP explanations, the observability dashboard, and retraining are all impossible. Treat logging as part of the endpoint, not an optional addition.

## n8n Boundary

- n8n orchestrates the retraining pipeline (trigger → retrain → backtest → MLflow registration → Discord notification) and alerting (model degradation, data quality issues).
- This service should expose clean, callable endpoints for n8n to hit (e.g., a retrain-trigger endpoint) — it should not embed n8n-specific logic internally.
- SHAP computation and decision logging must never be delegated to n8n; they belong in this codebase.

## Build / Run

```bash
pip install -r requirements.txt --break-system-packages
uvicorn app.main:app --reload
```

## Checklist (before considering work done)

- [ ] Does every decision-making endpoint write a decision log?
- [ ] Is LightGBM the only model being retrained?
- [ ] Are GPT calls limited to feedback/report generation, with no fine-tuning attempted?
- [ ] Are market-specific feature thresholds separated, not shared?
- [ ] Does `decision_log` treat cross-DB references as ID-only, with no assumed FK integrity?
- [ ] Was the OpenAPI schema updated if any endpoint contract changed?