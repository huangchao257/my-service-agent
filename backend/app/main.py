from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.api.agents import router as agents_router
from app.api.providers import router as providers_router
from app.api.conversations import router as conversations_router
from app.api.chat import router as chat_router


@asynccontextmanager
async def lifespan(application: FastAPI):
    await init_db()
    yield


app = FastAPI(title="Agent Platform", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agents_router)
app.include_router(providers_router)
app.include_router(conversations_router)
app.include_router(chat_router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}