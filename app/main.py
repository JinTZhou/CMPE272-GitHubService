# Author: Jin Ting Zhou

from fastapi import FastAPI
from .routes.issues import router as issues_router
from .routes.webhook import router as webhook_router



app = FastAPI(
    title="GitHub Issues Gateway",
    version="1.0.0",
)


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


app.include_router(issues_router)
app.include_router(webhook_router)