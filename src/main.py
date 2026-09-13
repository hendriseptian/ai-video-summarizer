from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from workers import asgi, env

import httpx


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

    try:

        # ==============================
        # 1. GET YOUTUBE URL
        # ==============================

        url = data.get("url")

        if not url:
            return {
                "status": "error",
                "message": "YouTube URL is required"
            }


        # ==============================
        # 2. GET API KEY
        # ==============================

        api_key = getattr(
            env,
            "FREETRANSCRIPT_API_KEY",
            None
        )


        # ==============================
        # 3. CALL FREETRANSCRIPT API
        # ==============================

        api_url = (
            "https://api.freetranscriptapi.com/v1/transcript"
        )


        headers = {
            "Accept": "application/json"
        }


        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"


        params = {
            "video_url": url
        }


        async with httpx.AsyncClient() as client:

            response = await client.get(
                api_url,
                params=params,
                headers=headers,
                timeout=30.0
            )


        # ==============================
        # 4. READ RESPONSE
        # ==============================

        response_text = response.text


        # ==============================
        # 5. RETURN API ERROR
        # ==============================

        if response.status_code >= 400:

            return {
                "status": "error",
                "message": "FreeTranscriptAPI request failed",
                "http_status": response.status_code,
                "details": response_text
            }


        # ==============================
        # 6. PARSE JSON
        # ==============================

        transcript_data = response.json()


        # ==============================
        # 7. SUCCESS
        # ==============================

        return {
            "status": "success",
            "url": url,
            "source": "YouTube",
            "backend": "Cloudflare",
            "transcript": transcript_data
        }


    except Exception as error:

        return {
            "status": "error",
            "message": "Worker exception",
            "error_type": type(error).__name__,
            "error": str(error)
        }


Default = asgi.entrypoint(app)
