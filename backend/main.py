import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.benchmark import load_data, router as benchmark_router
from routers.coding_intelligence import load_coding_data


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_data()
    try:
        load_coding_data()
    except Exception as exc:
        print(f"WARNING: Coding intelligence startup failed — {exc}")
        print("The server will continue without coding intelligence checks.")
    yield


app = FastAPI(title="Parity API", version="0.1.0", lifespan=lifespan)

# CORS: allow localhost dev + production Vercel domain
allowed_origins = [
    "http://localhost:5173",
]

# Add production Vercel URL from env if set
vercel_url = os.environ.get("VERCEL_FRONTEND_URL")
if vercel_url:
    allowed_origins.append(vercel_url)

# Also allow any *.vercel.app preview deploys
allowed_origin_regex = r"https://.*\.vercel\.app"

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=allowed_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(benchmark_router)


@app.get("/")
def root():
    return {"status": "ok"}
