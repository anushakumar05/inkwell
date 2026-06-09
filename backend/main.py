"""
Entry point for the Inkwell FastAPI backend.

Run with: uvicorn main:app --reload
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from services.embeddings import ensure_collection
from beanie import init_beanie
from dotenv import load_dotenv

import os

# Load environment variables from .env BEFORE importing anything that uses them
load_dotenv()

from models.entry import Entry  # noqa: E402
from services.evaluation import EvalRun  # add to your imports near Entry
from api.entries import router as entries_router
from api.chat import router as chat_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    await init_beanie(
        database=client[os.environ["DB_NAME"]],
        document_models=[Entry, EvalRun],
    )
    print(f"✅ Connected to MongoDB: {os.environ['DB_NAME']}")

    await ensure_collection()
    print("✅ Qdrant collection ready")

    yield
    # --- Shutdown ---
    client.close()


app = FastAPI(
    title="Inkwell API",
    description="Journaling backend with semantic memory.",
    version="0.1.0",
    lifespan=lifespan,
)

allowed_origins = os.environ.get("ALLOWED_ORIGINS", "http://localhost:5173").split(",")

# Allow the React frontend (running on localhost:5173) to call this API.
# In production we'll lock this down to the real frontend domain.
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(entries_router)
app.include_router(chat_router)

@app.get("/")
async def root():
    return {"status": "ok", "service": "inkwell-api"}


@app.get("/health")
async def health():
    """Used by deployment platforms to check if the service is alive."""
    return {"status": "healthy"}