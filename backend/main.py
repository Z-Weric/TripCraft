"""TripCraft 后端入口 — FastAPI"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database.models import init_db
from api import generate, verify, feedback, pois

app = FastAPI(title="TripCraft API", version="1.0.0")

# CORS — 允许前端本地开发访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(generate.router)
app.include_router(verify.router)
app.include_router(feedback.router)
app.include_router(pois.router)


@app.on_event("startup")
def startup():
    init_db()


@app.get("/")
def root():
    return {"name": "TripCraft API", "docs": "/docs"}