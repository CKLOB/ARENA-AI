from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.feedback.router import router as feedback_router
from app.recommendation.router import router as recommendation_router
from app.shared.http import register_exception_handlers
from app.trading_ai import predictor
from app.trading_ai.router import router as trading_ai_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    predictor.load_model()
    yield


# ponytail: title은 건드리지 않는다. CI가 app.title == 'FastAPI'를 검사한다.
app = FastAPI(lifespan=lifespan)
register_exception_handlers(app)
app.include_router(trading_ai_router)
app.include_router(recommendation_router)
app.include_router(feedback_router)


@app.get("/health")
def health():
    return {"status": "ok"}
