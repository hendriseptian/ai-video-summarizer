from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from workers import asgi, env
from js import fetch

from urllib.parse import quote
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

    try:

        # =====================================
        # 1. GET YOUTUBE URL
        # =====================================

        url = data.get("url")

        if not url:

            return {
                "status": "error",
                "message": "YouTube URL is required"
            }


        # =====================================
        # 2. GET API KEY FROM CLOUDFLARE SECRET
        # =====================================

        api_key = getattr(
            env,
            "FREETRANSCRIPT_API_KEY",
            None
        )


        if not api_key:

            return {
                "status": "error",
                "message": "FREETRANSCRIPT_API_KEY is not configured"
            }


        # =====================================
        # 3. BUILD FREETRANSCRIPT API URL
        # =====================================

        encoded_url = quote(
            url,
            safe=""
        )


        api_url = (
            "https://api.freetranscriptapi.com/v1/transcript"
            f"?video_url={encoded_url}"
        )


        # =====================================
        # 4. CALL FREETRANSCRIPT API
        # =====================================

        response = await fetch(
            api_url,
            {
                "method": "GET",
                "headers": {
                    "Authorization": f"Bearer {api_key}",
                    "Accept": "application/json"
                }
            }
        )


        # =====================================
        # 5. READ RESPONSE
        # =====================================

        response_text = await response.text()


        # =====================================
        # 6. API ERROR
        # =====================================

        if not response.ok:

            return {
                "status": "error",
                "message": "FreeTranscriptAPI request failed",
                "http_status": int(response.status),
                "details": response_text
            }


        # =====================================
        # 7. PARSE JSON
        # =====================================

        transcript_data = json.loads(
            response_text
        )


        # =====================================
        # 8. SUCCESS
        # =====================================

        return {
            "status": "success",
            "url": url,
            "source": "YouTube",
            "backend": "Cloudflare",
            "transcript": transcript_data
        }


    except Exception as error:

        # =====================================
        # DEBUG ERROR
        # =====================================

        return {
            "status": "error",
            "message": "Worker exception",
            "error": str(error)
        }


Default = asgi.entrypoint(app)
