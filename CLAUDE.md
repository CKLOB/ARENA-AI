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
- Anthropic SDK — Claude (`claude-opus-5` by default, `ANTHROPIC_MODEL` to override), feedback text generation only
- PostgreSQL (dedicated schema/instance for this service, separate from the Spring Boot DB)

## Directory Structure

Domain-based, not layer-first:

```
app/
  trading_ai/       # LightGBM trading decision logic
  recommendation/   # Recommendation card generation (reuses trading_ai model)
  feedback/         # Claude feedback generation
  observability/    # SHAP computation, decision log writes
  mlops/            # Retraining, backtesting, MLflow integration
  shared/           # Common schemas, market enum, config
```

## Model Responsibilities — Do Not Mix These Up

| Function | Model | Retrained? |
|---|---|---|
| Trading bot decisions | LightGBM | **Yes** — the only retraining target |
| Recommendation cards | LightGBM | Same model, reused |
| Challenge feedback text | Claude | **No** — inference call only |
| Challenge result report | Claude | Same as above |

Claude is an inference-only dependency here — never attempt to fine-tune it. Never let Claude influence a trading decision, and never let LightGBM generate free text.

## Boundary with the Spring Boot Backend

- This service does not own trading domain logic (order execution, balance, challenge settlement). Spring Boot calls this service's endpoints and handles the transactional side itself.
- Every decision-making endpoint (`/internal/ai/trading-decisions`, `/internal/ai/recommendations`) must write a decision log as part of the same request — not as an afterthought.
- If an endpoint's request/response shape changes, update the OpenAPI schema so Spring Boot's client code stays in sync.

## Database

- This service uses its **own PostgreSQL schema/instance**, separate from the Spring Boot database (agreed to avoid migration conflicts and isolate high-frequency decision log writes).
- `decision_log` rows reference Spring Boot entities (`challenge_id`, `order_id`) by ID only — there is no foreign key constraint across databases. Referential integrity for these fields must be handled at the application level, not assumed at the DB level.

## Market Handling

- Market type: `KR | US | COIN` enum, always modeled as three even though only two are active.
- Currently active: `US`, `COIN`. `KR` is disabled pending a brokerage account.
- Feature engineering (moving averages, RSI, volume, MACD, volatility) is computed by the Spring Boot backend and sent in the request — both `/internal/ai/trading-decisions` and `/internal/ai/recommendations` receive `features` rather than deriving them.
- Decision thresholds, however, must stay separated per market — do not assume shared thresholds across markets with different volatility profiles (see `THRESHOLDS` in `app/trading_ai/predictor.py`).

### Feature Contract — must match the Spring Boot side exactly

`app/mlops/features.py` is the executable source of these definitions; training and inference both read `FEATURE_NAMES` from it. Names and count matching is not enough — if Spring computes a value differently, the model returns a wrong prediction with no error.

| Feature | Definition | Typical range |
|---|---|---|
| `rsi` | 14-day RSI divided by 100 | 0 ~ 1 |
| `ma5` | 5-day SMA / current close | 0.9 ~ 1.1 |
| `ma20` | 20-day SMA / current close | 0.8 ~ 1.2 |
| `volumeChange` | (volume / 20-day mean volume) − 1 | −1 ~ 3 |
| `macd` | (EMA12 − EMA26) / current close | −0.1 ~ 0.1 |
| `volatility` | 20-day stdev of daily returns | 0 ~ 0.1 |

`ma5`, `ma20`, and `macd` are **ratios to close**, not absolute values. Absolute values put AAPL (~300) and BTC (~70,000) in incomparable feature spaces — a single model cannot learn both.

`market` is appended as a categorical feature by this service (`KR=0, US=1, COIN=2`); Spring sends it as a separate request field, not inside `features`.

**LightGBM matches features by column order, not by name.** `predict()` reorders the incoming dict to `booster.feature_name()` and raises on missing names — do not bypass that, or a reordered JSON payload will silently produce a different decision.

## Decision Logging Requirements (non-negotiable)

Every time `/internal/ai/trading-decisions` or `/internal/ai/recommendations` is called, persist:
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
- [ ] Are Claude calls limited to feedback/report generation, with no fine-tuning attempted?
- [ ] Are market-specific feature thresholds separated, not shared?
- [ ] Does `decision_log` treat cross-DB references as ID-only, with no assumed FK integrity?
- [ ] Was the OpenAPI schema updated if any endpoint contract changed?
