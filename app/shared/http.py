import logging
import os
import secrets
from http import HTTPStatus

from fastapi import FastAPI, Header, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


def verify_internal_api_key(x_internal_api_key: str | None = Header(default=None)) -> None:
    """Spring Boot -> AI 서비스 내부 호출 인증. JWT 아님, 라우터에 Depends로 붙인다."""
    expected = os.getenv("INTERNAL_API_KEY")
    if not expected:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "INTERNAL_API_KEY is not configured")
    if x_internal_api_key is None or not secrets.compare_digest(x_internal_api_key, expected):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid internal api key")


def error_response(status_code: int, message: str) -> JSONResponse:
    try:
        code = HTTPStatus(status_code).name
    except ValueError:
        code = "ERROR"
    return JSONResponse(status_code=status_code, content={"error": {"code": code, "message": message}})


def register_exception_handlers(app: FastAPI) -> None:
    # ponytail: 성공 응답은 감싸지 않는다 (명세가 bare object). 에러 응답만 포맷을 통일한다.
    @app.exception_handler(HTTPException)
    async def _http_exception(request: Request, exc: HTTPException) -> JSONResponse:
        return error_response(exc.status_code, str(exc.detail))

    @app.exception_handler(RequestValidationError)
    async def _validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        message = "; ".join(f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors())
        return error_response(status.HTTP_422_UNPROCESSABLE_CONTENT, message)

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        # 명세의 "500 - 모델 추론 실패"가 여기로 떨어진다. 스택트레이스는 로그로만, 응답에는 싣지 않는다.
        logger.exception("unhandled error on %s %s", request.method, request.url.path)
        return error_response(status.HTTP_500_INTERNAL_SERVER_ERROR, "internal server error")
