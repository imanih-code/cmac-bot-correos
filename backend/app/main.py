from fastapi import FastAPI
from app.api.endpoints import email
from app.core import config

app = FastAPI(title="CMAC Bot Correos API")

app.include_router(email.router, prefix="/email", tags=["email"])

@app.get("/")
def read_root():
    return {"message": "Welcome to CMAC Bot Correos API"}
