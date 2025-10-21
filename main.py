from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from routes import admin, auth, coins, market, public, trade, user
from utils.api_metrics import record_request, flush_metrics
import time


app = FastAPI(title="Coinbrew API", version="2.0.0")

templates = Jinja2Templates(directory="templates")

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    #TODO: Add production URL here
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class APIMetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration = (time.perf_counter() - start) * 1000
        record_request(request.url.path, request.method, duration)
        flush_metrics()
        return response
    
app.add_middleware(APIMetricsMiddleware)


app.include_router(admin.router, prefix="/api/v2/admin", tags=["admin"])
app.include_router(auth.router, prefix="/api/v2/auth", tags=["auth"])
app.include_router(coins.router, prefix="/api/v2/coins", tags=["coins"])
app.include_router(market.router, prefix="/api/v2/market", tags=["market"])
app.include_router(public.router, prefix="/api/v2/public", tags=["public"])
app.include_router(trade.router, prefix="/api/v2/trade", tags=["trade"])
app.include_router(user.router, prefix="/api/v2/user", tags=["user"])

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
