# AGENTS.md

Guide for any AI coding agent working in the FastAPI AI service repo.

## Project Context

AI service for a mock investment battle platform. This repo owns AI decision-making: trading bot logic, recommendation generation, SHAP-based explainability, and model retraining. The Spring Boot backend calls this service over HTTP; trading domain logic (orders, balance, settlement) never belongs here.

- This is not a real trading service (education positioning). Do not propose or implement anything that optimizes for trade volume over user learning.

## Stack

FastAPI, Python 3.11+, LightGBM, SHAP, MLflow, pandas, OpenAI SDK (GPT-5.4 mini), PostgreSQL (dedicated schema, separate from the Spring Boot database).

## Directory Structure

Domain-based: `trading_ai`, `recommendation`, `feedback`, `observability`, `mlops`, `shared`. Before adding code, decide which domain it belongs to.

## Model Responsibilities (critical — do not mix these up)

- **LightGBM**: makes trading decisions and generates recommendations. This is the **only model retrained** in this system, on a periodic schedule using accumulated decision/reaction logs.
- **GPT-5.4 mini**: generates natural-language feedback and challenge reports. Inference-only — never fine-tuned. (OpenAI has been sunsetting the fine-tuning API since May 2026; attempting to fine-tune this model is a dead end, not just unnecessary.)

Never let GPT influence a trading decision. Never ask LightGBM to produce free text. These are separate concerns handled by separate models for a reason.

## Boundary with the Spring Boot Backend

- This service never implements order execution, balance updates, or challenge settlement — that's Spring Boot's job.
- Every decision-making endpoint (`/trading-ai/decide`, `/recommendation/generate`) must write a decision log in the same request cycle, not as a follow-up task.
- Keep the OpenAPI schema in sync with any request/response shape change — Spring Boot's client code depends on it.

## Database

- This service has its **own PostgreSQL schema/instance**, intentionally separate from the Spring Boot database, to avoid migration conflicts and isolate high-frequency decision log writes.
- `decision_log` references Spring Boot entities (`challenge_id`, `order_id`) by ID value only. There is no cross-database foreign key. Do not assume referential integrity is enforced by the database — validate or handle orphaned references at the application level.

## Market Handling

- Model markets as a 3-way enum: `KR`, `US`, `COIN`, even though only `US` and `COIN` are currently active.
- Feature engineering must be market-specific. Do not share volatility/momentum thresholds across markets with different characteristics (e.g., crypto's 24/7 trading vs. equity market hours).

## Decision Logging (non-negotiable)

Every call to a decision-making endpoint must persist: feature snapshot, model output probability, action taken, and model version. This is the foundation for SHAP explanations, the observability dashboard, and retraining — treat it as part of the endpoint's contract, not an optional addition.

## n8n Boundary

- n8n orchestrates the retraining pipeline and alerting (model degradation, data quality issues) by calling into this service's endpoints.
- This service should expose clean endpoints for n8n to trigger — it should not contain n8n-specific branching logic.
- SHAP computation and decision logging stay in this codebase; never delegate them to a workflow tool.

## Build & Run

```bash
pip install -r requirements.txt --break-system-packages
uvicorn app.main:app --reload
```

## Do Not (checklist)

- [ ] Do not implement order execution, balance, or settlement logic in this repo (Spring Boot's responsibility)
- [ ] Do not attempt to fine-tune GPT-5.4 mini — it isn't supported, and LightGBM is the only retraining target
- [ ] Do not let GPT output affect a trading decision, or let LightGBM generate free text
- [ ] Do not consider a decision-making endpoint complete without a decision log write
- [ ] Do not assume foreign key integrity between this service's DB and Spring Boot's DB
- [ ] Do not hardcode feature thresholds shared across markets with different volatility profiles
- [ ] Do not change an endpoint contract without updating the OpenAPI schema