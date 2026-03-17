import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.benchmark import load_data, router as benchmark_router
from routers.ai_parse import router as ai_parse_router
from routers.eob_parse import router as eob_parse_router
from routers.coding_intelligence import load_coding_data
from routers.employer import router as employer_router
from routers.employer_shared import load_employer_benchmarks
from routers.provider import router as provider_router
from routers.signal_events import router as signal_events_router
from routers.signal_stripe import router as signal_stripe_router
from routers.signal_metrics import router as signal_metrics_router
from routers.signal_qa import router as signal_qa_router
from routers.signal_topic_request import router as signal_topic_request_router
from routers.signal_notify_deliver import router as signal_notify_deliver_router
from routers.signal_profiles import router as signal_profiles_router
from routers.health_analyze import router as health_analyze_router
from routers.health_auth import router as health_auth_router
from routers.benchmark_observations import router as benchmark_observations_router
from routers.broker import router as broker_router
from routers.employer_shared_report import router as employer_shared_report_router
from routers.auth import router as auth_router
from routers.signal_intelligence import router as signal_intelligence_router
from routers.platform_cases import router as platform_cases_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_data()
    try:
        load_coding_data()
    except Exception as exc:
        print(f"WARNING: Coding intelligence startup failed — {exc}")
        print("The server will continue without coding intelligence checks.")
    try:
        load_employer_benchmarks()
    except Exception as exc:
        print(f"WARNING: Employer benchmark startup failed — {exc}")
        print("The server will continue without employer benchmarks.")
    yield


app = FastAPI(title="Parity API", version="0.1.0", lifespan=lifespan)

# CORS: allow localhost dev + production Vercel domain
allowed_origins = [
    "http://localhost:5173",
    "https://civicscale.ai",
    "https://www.civicscale.ai",
    "https://health.civicscale.ai",
    "https://provider.civicscale.ai",
    "https://broker.civicscale.ai",
    "https://employer.civicscale.ai",
    "https://signal.civicscale.ai",
    "https://staging.civicscale.ai",
    "https://staging-health.civicscale.ai",
    "https://staging-provider.civicscale.ai",
    "https://staging-broker.civicscale.ai",
    "https://staging-employer.civicscale.ai",
    "https://staging-signal.civicscale.ai",
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
app.include_router(ai_parse_router)
app.include_router(eob_parse_router)
app.include_router(employer_router)
app.include_router(provider_router)
app.include_router(signal_events_router)
app.include_router(signal_stripe_router)
app.include_router(signal_metrics_router)
app.include_router(signal_qa_router)
app.include_router(signal_topic_request_router)
app.include_router(signal_notify_deliver_router)
app.include_router(signal_profiles_router)
app.include_router(health_analyze_router)
app.include_router(health_auth_router)
app.include_router(benchmark_observations_router)
app.include_router(broker_router)
app.include_router(employer_shared_report_router)
app.include_router(auth_router)
app.include_router(signal_intelligence_router)
app.include_router(platform_cases_router)


@app.get("/")
def root():
    return {"status": "ok"}
