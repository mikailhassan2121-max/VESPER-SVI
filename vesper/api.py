from contextlib import asynccontextmanager
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
        return app.state.runtime.status

    @app.get("/api/signals")
    async def signals():
        return app.state.runtime.store.recent()

    return app
