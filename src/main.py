from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from workers import asgi


app = FastAPI(
    title="AI Video Summarizer API",
    description="Backend API for AI Video Summarizer",
    version="1.0.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "status": "ok",
        "message": "AI Video Summarizer API is running on Cloudflare"
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy"
    }


@app.post("/analyze")
async def analyze(data: dict):
    url = data.get("url")

    if not url:
        return {
            "status": "error",
            "message": "YouTube URL is required"
        }

    return {
        "status": "success",
        "message": "Video URL received",
        "url": url
    }


Default = asgi.entrypoint(app)
