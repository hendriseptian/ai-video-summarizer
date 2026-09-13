from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from workers import asgi, env

import httpx2 as httpx


# ============================================================
# APP
# ============================================================

app = FastAPI(
    title="AI Video Summarizer API",
    description="Backend API for AI Video Summarizer",
    version="1.1.0"
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# ROOT
# ============================================================

@app.get("/")
async def root():

    return {
        "status": "ok",
        "message": "AI Video Summarizer API is running on Cloudflare"
    }


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
async def health():

    return {
        "status": "healthy"
    }


# ============================================================
# ANALYZE
# ============================================================

@app.post("/analyze")
async def analyze(data: dict):

    try:

        # ====================================================
        # 1. GET YOUTUBE URL
        # ====================================================

        url = data.get("url")

        if not url:

            return {
                "status": "error",
                "message": "YouTube URL is required"
            }


        # ====================================================
        # 2. GET FREETRANSCRIPT API KEY
        # ====================================================

        api_key = getattr(
            env,
            "FREETRANSCRIPT_API_KEY",
            None
        )


        # ====================================================
        # 3. FREETRANSCRIPT API
        # ====================================================

        api_url = (
            "https://api.freetranscriptapi.com/v1/transcript"
        )


        headers = {
            "Accept": "application/json"
        }


        if api_key:

            headers["Authorization"] = (
                f"Bearer {api_key}"
            )


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


        # ====================================================
        # 4. CHECK TRANSCRIPT API ERROR
        # ====================================================

        if response.status_code >= 400:

            return {

                "status": "error",

                "message": (
                    "FreeTranscriptAPI request failed"
                ),

                "http_status": response.status_code,

                "details": response.text
            }


        # ====================================================
        # 5. PARSE TRANSCRIPT
        # ====================================================

        transcript_data = response.json()


        video_title = transcript_data.get(
            "title",
            "Unknown title"
        )


        language = transcript_data.get(
            "language",
            "unknown"
        )


        transcript_segments = transcript_data.get(
            "transcript",
            []
        )


        if not transcript_segments:

            return {

                "status": "error",

                "message": (
                    "Transcript is empty"
                )
            }


        # ====================================================
        # 6. COMBINE TRANSCRIPT
        # ====================================================

        transcript_text = "\n".join(

            segment.get("text", "")

            for segment in transcript_segments

            if segment.get("text")
        )


        # ====================================================
        # 7. LIMIT TRANSCRIPT
        # ====================================================
        #
        # V1:
        # Keep a reasonable size for the first AI test.
        #
        # Later we will build automatic chunking for
        # very long videos.
        #

        max_characters = 100000

        if len(transcript_text) > max_characters:

            transcript_text = transcript_text[
                :max_characters
            ]


        # ====================================================
        # 8. AI PROMPT
        # ====================================================

        system_prompt = """
You are an AI video summarization assistant.

Your task is to analyze a video transcript and produce
a useful, accurate summary.

Rules:

1. Use only information contained in the transcript.
2. Do not invent facts.
3. Keep the summary concise but informative.
4. Identify the most important ideas.
5. Write in the same language as the transcript when possible.

Return the result using exactly these sections:

SUMMARY:
A concise summary of the video.

KEY POINTS:
- Important point 1
- Important point 2
- Important point 3
- Important point 4
- Important point 5

TAKEAWAYS:
A concise conclusion explaining the main lesson or
important conclusion from the video.
"""


        user_prompt = f"""
Video title:
{video_title}

Transcript:

{transcript_text}
"""


        # ====================================================
        # 9. CALL WORKERS AI
        # ====================================================

        ai_response = await env.AI.run(

            "@cf/zai-org/glm-4.7-flash",

            {
                "messages": [

                    {
                        "role": "system",
                        "content": system_prompt
                    },

                    {
                        "role": "user",
                        "content": user_prompt
                    }

                ],

                "temperature": 0.3,

                "max_tokens": 1200
            }
        )


        # ====================================================
        # 10. GET AI RESPONSE
        # ====================================================

        ai_text = ai_response.get(
            "response",
            ""
        )


        # ====================================================
        # 11. RETURN RESULT
        # ====================================================

        return {

            "status": "success",

            "youtube_url": url,

            "title": video_title,

            "language": language,

            "summary": ai_text,

            "transcript": transcript_data
        }


    except Exception as error:

        return {

            "status": "error",

            "message": "Worker exception",

            "error_type": type(error).__name__,

            "error": str(error)
        }


# ============================================================
# WORKERS ENTRYPOINT
# ============================================================

Default = asgi.entrypoint(app)
