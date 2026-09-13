from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from workers import asgi
import json


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


    # Ambil API key dari Cloudflare Secret
    api_key = None

    try:
        from workers import env
        api_key = env.FREETRANSCRIPT_API_KEY
    except Exception:
        pass


    if not api_key:

        return {
            "status": "error",
            "message": "FreeTranscriptAPI key is not configured"
        }


    # Import fetch dari Workers runtime
    from js import fetch


    api_url = (
        "https://api.freetranscriptapi.com/v1/transcript"
        "?video_url="
        + url
    )


    response = await fetch(
        api_url,
        {
            "method": "GET",
            "headers": {
                "Authorization": f"Bearer {api_key}"
            }
        }
    )


    response_text = await response.text()


    if not response.ok:

        return {
            "status": "error",
            "message": "Transcript API request failed",
            "http_status": response.status,
            "details": response_text
        }


    transcript_data = json.loads(response_text)


    return {
        "status": "success",
        "url": url,
        "source": "YouTube",
        "backend": "Cloudflare",
        "transcript": transcript_data
    }


Default = asgi.entrypoint(app)
