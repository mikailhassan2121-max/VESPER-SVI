import json
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from filelock import FileLock

from vesper.config import Settings
from vesper.runtime import Runtime


def create_app():
    settings = Settings()
    settings.prepare()

    @asynccontextmanager
    async def lifespan(app):
        lock = FileLock(settings.data_dir / "instance.lock", timeout=0)
        with lock:
            runtime = Runtime(settings)
            app.state.runtime = runtime
            await runtime.start()
            try:
                yield
            finally:
                await runtime.close()

    app = FastAPI(title="VESPER", lifespan=lifespan)

    @app.get("/", response_class=HTMLResponse)
    async def dashboard():
        return (Path(__file__).parent / "ui" / "index.html").read_text(encoding="utf-8")

    @app.get("/api/status")
    async def status():
        from vesper.calendar import NY, utcnow
        from vesper.validation import evaluate
        runtime = app.state.runtime
        result = runtime.status.copy()
        try:
            receipt = json.loads((settings.data_dir / "live-validation.json").read_text(encoding="utf-8"))
            same_model = receipt["evidence"]["runtime"].get("model") == result.get("model")
            checked = datetime.fromisoformat(receipt["evidence"]["checked_at"])
            same_session = checked.tzinfo is not None and checked.astimezone(NY).date() == utcnow().astimezone(NY).date()
            result["production_validated"] = (receipt["checks"]["LIVE PIPELINE"] == "PASS" and same_model and same_session and
                evaluate(result, runtime.store.recent(), utcnow(), settings)["LIVE PIPELINE"] == "PASS")
        except (OSError, ValueError, KeyError, TypeError):
            result["production_validated"] = False
        return result

    @app.get("/api/signals")
    async def signals():
        return app.state.runtime.store.recent()

    @app.get("/api/chart/{ticker}")
    async def chart(ticker: str):
        bars = app.state.runtime.bars.get(ticker, {})
        return [{"time": end.isoformat(), "price": max(versions, key=lambda row: row["available_at"])["close"]}
                for end, versions in sorted(bars.items())[-390:] if versions]

    return app
