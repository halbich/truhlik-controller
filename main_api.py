from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from src.helpers.project_config import ProjectConfig
from src.routers import analysis, healthcheck, kondor, recording
from src.services.cron.process_doc_cron import get_statistics
from src.services.cron.process_worker import start_background_task, stop_background_task
from src.services.project_version import get_project_version

from services.relay import get_relays_status


@asynccontextmanager
async def lifespan(_app: FastAPI):
    healthcheck.initial_clean()
    healthcheck.mark_app_started()

    start_background_task()

    healthcheck.mark_app_ready()

    yield
    print("Shutting down...")
    stop_background_task()
    print("Shutting down done.")


_, version = get_project_version()
app = FastAPI(
    title="Truhlik API",
    lifespan=lifespan,
    root_path="/api",
)

app.include_router(healthcheck.router)
app.include_router(analysis.router)
app.include_router(recording.router)
app.include_router(kondor.router)


@app.get("/")
async def root():

    return {
        "relays": get_relays_status(),
    }


if __name__ == "__main__":
    uvicorn.run("main_api:app", host="0.0.0.0", port=8081)
