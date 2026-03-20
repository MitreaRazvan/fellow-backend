from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.database import init_db
from app.routers import ingest, report, chat
from app.routers.chat_router import router as chat_direct_router

app = FastAPI(
    title="LUMA API",
    description="Intelligence research agent backend",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

@app.on_event("startup")
async def startup():
    init_db()
    print("✓ LUMA database initialized")

app.include_router(ingest.router)
app.include_router(report.router)
app.include_router(chat.router)
app.include_router(chat_direct_router)

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "LUMA API",
        "version": "1.0.0"
    }