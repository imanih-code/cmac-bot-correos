from fastapi import FastAPI
from app.api.endpoints import email
import asyncio

from contextlib import asynccontextmanager

from app.services.email_service import cleanup_expired_sessions

@asynccontextmanager
async def lifespan(app: FastAPI):
    cleaner_task = asyncio.create_task(cleanup_expired_sessions())
    yield
    cleaner_task.cancel()

app = FastAPI(title="CMAC Bot Correos API", lifespan=lifespan)

app.include_router(email.router, prefix="/email", tags=["email"])

@app.get("/")
def read_root():
    return {"message": "Welcome to CMAC Bot Correos API"}
