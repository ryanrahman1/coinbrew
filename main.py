from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from auth.routes import router as auth_router
from coins.routes import router as coins_router

app = FastAPI(title="CoinBrew API", version="1.0.0")

origins = [
    "http://localhost:3000",
    #TODO Add production URL here
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(coins_router, prefix="/api/coins", tags=["coins"])


@app.get("/")
def root():
    return {"message": "Welcome to the CoinBrew API!"}
