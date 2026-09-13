from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from workers import asgi, fetch

from urllib.parse import quote


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
        # 2. ENCODE URL
        # ==============================

        encoded_url = quote(
            url,
            safe=""
        )


        # ==============================
        # 3. FREETRANSCRIPT API
        # ==============================

        api_url = (
            "https://api.freetranscriptapi.com/v1/transcript"
            f"?video_url={encoded_url}"
        )


        # ==============================
        # 4. CALL API
        # ==============================

        response = await fetch(
            api_url
        )


        # ==============================
        # 5. READ RESPONSE
        # ==============================

        response_text = await response.text()


        # ==============================
        # 6. RETURN RAW RESULT
        # ==============================

        return {
            "status": "success",
            "youtube_url": url,
            "api_status": int(response.status),
            "transcript_api_response": response_text
        }


    except Exception as error:

        return {
            "status": "error",
            "message": "Worker exception",
            "error_type": type(error).__name__,
            "error": str(error)
        }


Default = asgi.entrypoint(app)
