import logging
from traceback import format_exc

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.config import Config
from starlette.requests import Request
from starlette.responses import JSONResponse
import uvicorn

from app.routers import (
    wiki_articles,
    comparison,
    structured_wiki,
    structural_analysis,
    models,
)

config = Config(".env")

LOG_LEVEL = config.get("LOG_LEVEL", default="INFO")
FASTAPI_DEBUG = config.get("FASTAPI_DEBUG", cast=bool, default=False)
SIMILARITY_THRESHOLD = config.get("SIMILARITY_THRESHOLD", cast=float, default=0.65)

comparison_models = [
    "sentence-transformers/LaBSE",
    "xlm-roberta-base",
    "multi-qa-distilbert-cos-v1",
    "multi-qa-MiniLM-L6-cos-v1",
    "multi-qa-mpnet-base-cos-v1",
]

logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s - %(levelname)s - %(message)s")

app = FastAPI(debug=FASTAPI_DEBUG, title="Symmetry Unified API", version="1.0.0")


async def http_exception_handler(request: Request, exc: HTTPException):
    response_content = {"detail": exc.detail}
    if getattr(request.app, "debug", False):
        response_content["stack_trace"] = format_exc()
    return JSONResponse(response_content, status_code=exc.status_code)


async def generic_exception_handler(request: Request, exc: Exception):
    logging.error(f"Unhandled exception: {exc}")
    response_content = {"detail": "Internal Server Error"}
    if getattr(request.app, "debug", False):
        response_content["stack_trace"] = format_exc()
    return JSONResponse(response_content, status_code=500)


app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(wiki_articles.router)
app.include_router(comparison.router)
app.include_router(structured_wiki.router)
app.include_router(structural_analysis.router)
app.include_router(models.router)


@app.get(
    "/",
    summary="API Root",
    description="Returns API information, version, and available endpoint categories. Use /docs for interactive documentation.",
)
async def root():
    return {
        "message": "Symmetry Unified API",
        "version": "1.0.0",
        "endpoints": {
            "wiki": "/symmetry/v1/wiki",
            "comparison": "/symmetry/v1/comparison",
            "structural_analysis": "/operations",
        },
    }


@app.get(
    "/health",
    summary="Health Check",
    description="Simple health check endpoint that returns the current service status. Can be used by load balancers and monitoring systems.",
)
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=FASTAPI_DEBUG)
