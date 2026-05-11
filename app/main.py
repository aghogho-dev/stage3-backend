import time
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

# Rate Limiting Imports
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from .utils import limiter
from .routers import auth, profiles
from .database import engine, Base, init_optimization


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_optimization()
    # Startup: Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Shutdown: Clean up resources
    await engine.dispose()

app = FastAPI(title="Insighta", lifespan=lifespan)


app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# --- MIDDLEWARE ---

# Logging Middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000
    
    # Format: Method | Endpoint | Status | Time
    print(f"{request.method} {request.url.path} | Status: {response.status_code} | {process_time:.2f}ms")
    return response

# CORS Middleware
# @app.middleware("http")
# async def add_cors_header(request: Request, call_next):
#     response = await call_next(request)
#     response.headers["Access-Control-Allow-Origin"] = "*"
#     response.headers["Access-Control-Allow-Methods"] = "*"
#     response.headers["Access-Control-Allow-Headers"] = "*"
#     return response

from fastapi import Response # Add this import at the top

@app.middleware("http")
async def add_cors_header(request: Request, call_next):
    # 1. Handle Preflight OPTIONS requests
    if request.method == "OPTIONS":
        response = Response()
        response.headers["Access-Control-Allow-Origin"] = "https://stage3-web-production-ea34.up.railway.app"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-API-Version"
        return response

    # 2. Process the actual request
    response = await call_next(request)
    
    # 3. Apply headers to the final response
    response.headers["Access-Control-Allow-Origin"] = "https://stage3-web-production-ea34.up.railway.app"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-API-Version"
    
    return response


# --- CUSTOM ERROR HANDLING ---

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"status": "error", "message": exc.detail},
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"status": "error", "message": "Invalid parameter type"},
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"status": "error", "message": "Server failure"},
    )

# --- ROUTERS ---
app.include_router(auth.router)
app.include_router(profiles.router)

# --- HEALTH CHECK --- 
@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}