import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.database import engine, Base
from app.routers import auth, admin, hr, employee

# ── Create all tables ─────────────────────────────────────
try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"DB init warning: {e}")

# ── Create upload directory ───────────────────────────────
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

# ── App instance ──────────────────────────────────────────
app = FastAPI(
    title="IndustriaOS API",
    description="Role-Based Business Management System",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static files ──────────────────────────────────────────
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# ── Routers ───────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(hr.router)
app.include_router(employee.router)

# ── Health check ──────────────────────────────────────────
@app.get("/")
def root():
    return {
        "app": "IndustriaOS API",
        "version": "1.0.0",
        "status": "running 🚀",
        "docs": "/docs",
    }

@app.get("/health")
def health():
    return {"status": "healthy"}