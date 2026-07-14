import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from llmops_studio.api import router

def create_app() -> FastAPI:
    app = FastAPI(
        title="LLMOps Studio API",
        description="Backend engine for the LLMOps General Purpose Platform",
        version="1.0.0"
    )

    # FIX: this previously only allowed http://localhost:3000, but the UI
    # is served by nginx on port 5173 in docker-compose (studio-ui ->
    # "5173:80"), and via `npm run dev` (vite --port=3000) for native/local
    # development. Both are legitimate origins, so we allow both by default;
    # override with a comma-separated CORS_ALLOWED_ORIGINS env var if needed.
    default_origins = "http://localhost:5173,http://localhost:3000"
    allowed_origins = os.getenv("CORS_ALLOWED_ORIGINS", default_origins).split(",")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)

    @app.get("/health")
    def health_check():
        return {"status": "healthy", "service": "llmops-studio"}

    return app

app = create_app()