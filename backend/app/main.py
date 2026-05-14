from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.api.agents import router as agents_router
from app.api.providers import router as providers_router
from app.api.conversations import router as conversations_router
from app.api.chat import router as chat_router
from app.api.mcp_servers import router as mcp_servers_router
from app.api.skills import router as skills_router
from app.api.memories import router as memories_router
from app.api.llm_interactions import router as llm_interactions_router


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
app.include_router(mcp_servers_router)
app.include_router(skills_router)
app.include_router(memories_router)
app.include_router(llm_interactions_router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}