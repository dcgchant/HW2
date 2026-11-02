from contextlib import asynccontextmanager
import logging
from pathlib import Path
import threading
import time

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool
from starlette.formparsers import MultiPartParser

from classifier import Classifier, InvalidImage

ROOT = Path(__file__).resolve().parent
MAX_BYTES = 10 * 1024 * 1024
# The bounded request fits in memory; prevent multipart files spilling to disk.
MultiPartParser.spool_max_size = MAX_BYTES + 64 * 1024
logger = logging.getLogger("uvicorn.error")
inference_lock = threading.Lock()


@asynccontextmanager
async def lifespan(app):
    app.state.classifier = None
    try:
        app.state.classifier = await run_in_threadpool(Classifier)
        logger.info("47-class INT8 ViT loaded with CPUExecutionProvider")
    except Exception:
        logger.exception("Model not ready. Run python prepare_model.py to prepare/repair local files.")
    yield


app = FastAPI(title="초록도감 · 로컬 식물 분류", lifespan=lifespan)


class UploadLimit:
    """Bound the entire streamed request before multipart parsing and disk spooling."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = dict(scope["headers"])
        if scope["method"] == "POST" and scope["path"] == "/api/analyze":
            limit = MAX_BYTES + 64 * 1024  # multipart boundary/header allowance
            try:
                length = int(headers.get(b"content-length", b"0"))
            except ValueError:
                return await JSONResponse({"detail": "올바르지 않은 요청 크기입니다."}, status_code=400)(scope, receive, send)
            total, messages = 0, []
            oversized = length > limit
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    return
                total += len(message.get("body", b""))
                if total > limit:
                    oversized = True
                    messages.clear()
                if not oversized:
                    messages.append(message)
                if not message.get("more_body", False):
                    break
            # Drain rejected uploads without retaining their bodies so clients
            # receive the JSON 413 rather than a reset during their send.
            if oversized:
                return await JSONResponse({"detail": "파일은 10MB 이하여야 합니다."}, status_code=413)(scope, receive, send)
            iterator = iter(messages)
            async def replay():
                return next(iterator, {"type": "http.request", "body": b"", "more_body": False})
            receive = replay
        async def secured_send(message):
            if message["type"] == "http.response.start":
                message["headers"] = list(message.get("headers", [])) + [
                    (b"x-content-type-options", b"nosniff"),
                    (b"referrer-policy", b"no-referrer"),
                    (b"content-security-policy", b"default-src 'self'; img-src 'self' blob:; style-src 'self'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"),
                    (b"cache-control", b"no-store")]
            await send(message)
        await self.app(scope, receive, secured_send)


app.add_middleware(UploadLimit)
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")


@app.get("/")
async def index():
    return FileResponse(ROOT / "static" / "index.html")


@app.get("/api/health")
async def health():
    ready = app.state.classifier is not None
    return JSONResponse({"ready": ready, "model": "ViT INT8 · 실내 식물 47개 범주", "provider": "CPUExecutionProvider"},
                        status_code=200 if ready else 503)


@app.post("/api/analyze")
async def analyze(file: UploadFile = File(...)):
    try:
        data = await file.read(MAX_BYTES + 1)
    finally:
        await file.close()
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "파일은 10MB 이하여야 합니다.")
    if not data:
        raise HTTPException(400, "비어 있는 파일입니다. 이미지를 다시 선택해 주세요.")
    if app.state.classifier is None:
        raise HTTPException(503, "모델이 준비되지 않았습니다. 서버 로그를 확인하고 python prepare_model.py를 실행한 뒤 서버를 다시 시작해 주세요.")
    if not inference_lock.acquire(blocking=False):
        raise HTTPException(429, "다른 이미지를 분석 중입니다. 잠시 후 다시 시도해 주세요.")
    started = time.perf_counter()
    try:
        result = await run_in_threadpool(app.state.classifier.classify, data)
        result["elapsed_ms"] = round((time.perf_counter() - started) * 1000)
        result["model"] = "ViT INT8 / CPU / 47 classes"
        return result
    except InvalidImage as error:
        raise HTTPException(400, str(error)) from error
    except Exception as error:
        logger.exception("Inference failed")
        raise HTTPException(500, "분석 중 오류가 발생했습니다. 다시 시도하거나 서버 로그를 확인해 주세요.") from error
    finally:
        inference_lock.release()
