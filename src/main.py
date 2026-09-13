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
    version="1.2.0"
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

        max_characters = 100000

        if len(transcript_text) > max_characters:

            transcript_text = transcript_text[
                :max_characters
            ]


        # ====================================================
        # 8. AI SYSTEM PROMPT
        # ====================================================

        system_prompt = """
You are an AI video summarization assistant.

Your task is to analyze a video transcript and produce
an accurate and useful summary in TWO languages:

1. English
2. Indonesian

IMPORTANT RULES:

1. Use ONLY information contained in the transcript.
2. Do NOT invent facts.
3. Do NOT add information that is not supported by the transcript.
4. Keep the summary concise but informative.
5. Identify the most important ideas.
6. The English version must be written in natural English.
7. The Indonesian version must be written in natural Indonesian.
8. Both versions must have the same meaning.
9. Do not translate the transcript itself.
10. Summarize the content.

Return ONLY valid JSON.

Use EXACTLY this structure:

{
  "en": {
    "summary": "A concise summary in English.",
    "key_points": [
      "Important point 1",
      "Important point 2",
      "Important point 3",
      "Important point 4",
      "Important point 5"
    ],
    "takeaways": "A concise conclusion in English."
  },
  "id": {
    "summary": "Ringkasan singkat dalam Bahasa Indonesia.",
    "key_points": [
      "Poin penting 1",
      "Poin penting 2",
      "Poin penting 3",
      "Poin penting 4",
      "Poin penting 5"
    ],
    "takeaways": "Kesimpulan singkat dalam Bahasa Indonesia."
  }
}

Do not use Markdown.

Do not put ```json around the response.

Return only the JSON object.
"""


        # ====================================================
        # 9. AI USER PROMPT
        # ====================================================

        user_prompt = f"""
Video title:
{video_title}

Transcript language:
{language}

Transcript:

{transcript_text}
"""


        # ====================================================
        # 10. CALL WORKERS AI
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

                "temperature": 0.2,

                "chat_template_kwargs": {
                    "enable_thinking": False
                }
            }
        )


        # ====================================================
        # 11. GET AI CONTENT
        # ====================================================

        ai_text = (
            ai_response
            .get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )


        # ====================================================
        # 12. PARSE AI JSON
        # ====================================================

        try:

            import json

            ai_summary = json.loads(ai_text)

        except Exception:

            ai_summary = {

                "en": {

                    "summary": ai_text,

                    "key_points": [],

                    "takeaways": ""
                },

                "id": {

                    "summary": "",

                    "key_points": [],

                    "takeaways": ""
                }
            }


        # ====================================================
        # 13. RETURN RESULT
        # ====================================================

        return {

            "status": "success",

            "youtube_url": url,

            "title": video_title,

            "language": language,

            "summary": ai_summary,

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
