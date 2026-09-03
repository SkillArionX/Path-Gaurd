from fastapi import FastAPI

from ml_modules.memory_assistant.api.routes import router
from ml_modules.memory_assistant.config import settings

app = FastAPI(title=settings.app_name)
app.include_router(router, prefix=settings.api_prefix)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


