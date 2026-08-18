from fastapi import FastAPI

from app.api.routes import router

app = FastAPI(title="PATHRIX API")
app.include_router(router)
