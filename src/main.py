from fastapi import (
    FastAPI,
    HTTPException,
    Request
)

from fastapi.middleware.cors import (
    CORSMiddleware
)

from fastapi.responses import (
    JSONResponse
)

from workers import asgi, env

import httpx2 as httpx

import json
import re
import hashlib


# ============================================================
# APP
# ============================================================

app = FastAPI(
    title="AI Video Summarizer API",
    description="AI Video Summarizer Backend",
    version="3.0.0"
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"]
)


# ============================================================
# CONSTANTS
# ============================================================

TRANSCRIPT_API_URL = (
    "https://api.freetranscriptapi.com/v1/transcript"
)

YOUTUBE_OEMBED_URL = (
    "https://www.youtube.com/oembed"
)

# Current active Cloudflare model.
AI_MODEL = (
    "@cf/meta/llama-3.1-8b-instruct-fast"
)

# ------------------------------------------------------------
# Normal video:
# one AI call
# ------------------------------------------------------------

MAX_SINGLE_PASS_CHARS = 100000

# ------------------------------------------------------------
# Very long video:
# fallback chunking
# ------------------------------------------------------------

CHUNK_SIZE = 18000


# ============================================================
# ROOT
# ============================================================

@app.get("/")
async def root():

    return {
        "status": "ok",
        "message": (
            "AI Video Summarizer API "
            "V3 is running on Cloudflare"
        ),
        "version": "3.0.0"
    }


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
async def health():

    return {
        "status": "healthy",
        "version": "3.0.0",
        "model": AI_MODEL
    }


# ============================================================
# ERROR HANDLER
# ============================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(
    request: Request,
    exc: HTTPException
):

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "message": str(exc.detail),
            "error_type": "HTTPException",
            "error": str(exc.detail),
            "http_status": exc.status_code
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(
    request: Request,
    exc: Exception
):

    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "Worker exception",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "http_status": 500
        }
    )


# ============================================================
# TEXT UTILITY
# ============================================================

def clean_text(value):

    if value is None:
        return ""

    return str(value).strip()


# ============================================================
# YOUTUBE VIDEO ID
# ============================================================

def extract_video_id(url):

    url = clean_text(url)

    patterns = [

        r"(?:youtube\.com/watch\?v=)"
        r"([A-Za-z0-9_-]{11})",

        r"(?:youtu\.be/)"
        r"([A-Za-z0-9_-]{11})",

        r"(?:youtube\.com/embed/)"
        r"([A-Za-z0-9_-]{11})",

        r"(?:youtube\.com/shorts/)"
        r"([A-Za-z0-9_-]{11})"

    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            url
        )

        if match:

            return match.group(1)

    return None


# ============================================================
# NORMALIZE YOUTUBE URL
# ============================================================

def normalize_youtube_url(url):

    video_id = extract_video_id(
        url
    )

    if video_id:

        return (
            "https://www.youtube.com/watch?v="
            + video_id
        )

    return clean_text(url)


# ============================================================
# TRANSCRIPT HASH
# ============================================================

def create_transcript_hash(
    transcript
):

    raw = json.dumps(
        transcript,
        ensure_ascii=False,
        sort_keys=True
    )

    return hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()


# ============================================================
# SAFE JSON PARSER
# ============================================================

def parse_ai_json(text):

    text = clean_text(text)

    if not text:

        raise ValueError(
            "AI returned empty response"
        )

    # --------------------------------------------------------
    # Remove markdown code fence
    # --------------------------------------------------------

    text = re.sub(
        r"^```json\s*",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"^```\s*",
        "",
        text
    )

    text = re.sub(
        r"\s*```$",
        "",
        text
    )

    text = text.strip()

    # --------------------------------------------------------
    # Direct JSON
    # --------------------------------------------------------

    try:

        result = json.loads(text)

        if isinstance(
            result,
            dict
        ):

            return result

    except Exception:
        pass

    # --------------------------------------------------------
    # Extract JSON object
    # --------------------------------------------------------

    start = text.find("{")
    end = text.rfind("}")

    if (
        start >= 0
        and end > start
    ):

        candidate = (
            text[start:end + 1]
        )

        try:

            result = json.loads(
                candidate
            )

            if isinstance(
                result,
                dict
            ):

                return result

        except Exception:
            pass

    raise ValueError(
        "AI response is not valid JSON"
    )


# ============================================================
# NORMALIZE ANALYSIS
# ============================================================

def normalize_analysis(
    data
):

    if not isinstance(
        data,
        dict
    ):

        data = {}

    summary = clean_text(
        data.get(
            "summary",
            ""
        )
    )

    key_points = data.get(
        "key_points",
        []
    )

    critical_analysis = data.get(
        "critical_analysis",
        []
    )

    takeaways = data.get(
        "takeaways",
        []
    )

    if not isinstance(
        key_points,
        list
    ):

        key_points = []

    if not isinstance(
        critical_analysis,
        list
    ):

        critical_analysis = []

    if not isinstance(
        takeaways,
        list
    ):

        takeaways = []

    key_points = [
        clean_text(item)
        for item in key_points
        if clean_text(item)
    ]

    critical_analysis = [
        clean_text(item)
        for item in critical_analysis
        if clean_text(item)
    ]

    takeaways = [
        clean_text(item)
        for item in takeaways
        if clean_text(item)
    ]

    return {
        "summary": summary,

        "key_points":
            key_points[:5],

        "critical_analysis":
            critical_analysis[:5],

        "takeaways":
            takeaways[:3]
    }


# ============================================================
# NORMALIZE TRANSCRIPT
# ============================================================

def normalize_transcript(
    data
):

    if not isinstance(
        data,
        dict
    ):

        return []

    raw_segments = data.get(
        "transcript",
        []
    )

    if not isinstance(
        raw_segments,
        list
    ):

        return []

    normalized = []

    for item in raw_segments:

        if not isinstance(
            item,
            dict
        ):

            continue

        text = clean_text(
            item.get(
                "text",
                ""
            )
        )

        if not text:

            continue

        try:

            start = float(
                item.get(
                    "start",
                    0
                )
            )

        except Exception:

            start = 0.0

        try:

            duration = float(
                item.get(
                    "duration",
                    0
                )
            )

        except Exception:

            duration = 0.0

        normalized.append(
            {
                "text": text,
                "start": start,
                "duration": duration
            }
        )

    return normalized


# ============================================================
# TRANSCRIPT TO TEXT
# ============================================================

def transcript_to_text(
    transcript
):

    lines = []

    for item in transcript:

        start = item.get(
            "start",
            0
        )

        text = clean_text(
            item.get(
                "text",
                ""
            )
        )

        if not text:

            continue

        lines.append(
            f"[{start:.2f}s] {text}"
        )

    return "\n".join(
        lines
    )


# ============================================================
# BUILD CHUNKS
# ============================================================

def build_chunks(
    transcript,
    max_chars=CHUNK_SIZE
):

    chunks = []

    current_lines = []

    current_length = 0

    for item in transcript:

        start = item.get(
            "start",
            0
        )

        text = clean_text(
            item.get(
                "text",
                ""
            )
        )

        if not text:

            continue

        line = (
            f"[{start:.2f}s] "
            f"{text}"
        )

        line_length = (
            len(line) + 1
        )

        if (
            current_lines
            and
            current_length
            + line_length
            > max_chars
        ):

            chunks.append(
                "\n".join(
                    current_lines
                )
            )

            current_lines = []

            current_length = 0

        current_lines.append(
            line
        )

        current_length += (
            line_length
        )

    if current_lines:

        chunks.append(
            "\n".join(
                current_lines
            )
        )

    return chunks


# ============================================================
# YOUTUBE METADATA
# ============================================================

async def get_youtube_metadata(
    url
):

    normalized_url = (
        normalize_youtube_url(url)
    )

    params = {
        "url": normalized_url,
        "format": "json"
    }

    try:

        async with httpx.AsyncClient(
            timeout=20.0
        ) as client:

            response = await client.get(
                YOUTUBE_OEMBED_URL,
                params=params
            )

        if response.status_code != 200:

            return {
                "title": "",
                "author_name": "",
                "author_url": "",
                "thumbnail_url": "",
                "video_id":
                    extract_video_id(
                        normalized_url
                    )
            }

        data = response.json()

        return {
            "title": clean_text(
                data.get(
                    "title",
                    ""
                )
            ),

            "author_name":
                clean_text(
                    data.get(
                        "author_name",
                        ""
                    )
                ),

            "author_url":
                clean_text(
                    data.get(
                        "author_url",
                        ""
                    )
                ),

            "thumbnail_url":
                clean_text(
                    data.get(
                        "thumbnail_url",
                        ""
                    )
                ),

            "video_id":
                extract_video_id(
                    normalized_url
                )
        }

    except Exception:

        return {
            "title": "",
            "author_name": "",
            "author_url": "",
            "thumbnail_url": "",
            "video_id":
                extract_video_id(
                    normalized_url
                )
        }


# ============================================================
# GET TRANSCRIPT
# ============================================================

async def get_transcript(
    url
):

    normalized_url = (
        normalize_youtube_url(url)
    )

    if not extract_video_id(
        normalized_url
    ):

        return {
            "ok": False,
            "status_code": 400,
            "message":
                "Invalid YouTube URL.",
            "data": None
        }

    # --------------------------------------------------------
    # FreeTranscriptAPI accepts:
    #
    # video_url = YouTube URL
    # OR
    # video_url = 11-character video ID
    # --------------------------------------------------------

    params = {
        "video_url":
            normalized_url
    }

    try:

        async with httpx.AsyncClient(
            timeout=60.0
        ) as client:

            response = await client.get(
                TRANSCRIPT_API_URL,
                params=params
            )

    except Exception as exc:

        return {
            "ok": False,
            "status_code": 502,
            "message":
                "Transcript API connection failed.",
            "error_type":
                type(exc).__name__,
            "error":
                str(exc),
            "data": None
        }

    # --------------------------------------------------------
    # Read response
    # --------------------------------------------------------

    try:

        data = response.json()

    except Exception:

        data = {}

    # --------------------------------------------------------
    # API ERROR
    # --------------------------------------------------------

    if response.status_code >= 400:

        return {
            "ok": False,
            "status_code":
                response.status_code,

            "message":
                "FreeTranscriptAPI returned an error.",

            "error":
                response.text,

            "data":
                data
        }

    # --------------------------------------------------------
    # TRANSCRIPT
    # --------------------------------------------------------

    transcript = normalize_transcript(
        data
    )

    if not transcript:

        return {
            "ok": False,
            "status_code": 404,
            "message":
                "Transcript tidak ditemukan "
                "atau video tidak memiliki caption.",
            "error":
                data,
            "data":
                data
        }

    return {
        "ok": True,
        "status_code": 200,
        "message": "Transcript retrieved.",
        "data": data,
        "transcript": transcript
    }


# ============================================================
# AI SYSTEM PROMPT
# ============================================================

AI_SYSTEM_PROMPT = """
You are a professional video content analyst.

Your job is to analyze a YouTube transcript.

IMPORTANT:

- Analyze ONLY the transcript.
- Do NOT use outside knowledge.
- Do NOT invent facts.
- Do NOT identify speakers.
- Do NOT guess who said something.
- Do NOT assign statements to specific people.
- Do NOT assume missing context.
- Do NOT criticize simply for the sake of criticizing.

The analysis must be:
- sharp
- critical
- evidence-based
- neutral
- concise
- useful
- consistent

Separate:
- facts
- claims
- opinions
- assumptions
- interpretations

Look for meaningful issues such as:
- unsupported claims
- weak evidence
- logical gaps
- contradictions
- overgeneralization
- exaggeration
- unsupported cause-and-effect
- missing evidence
- one-sided framing
- misleading conclusions

Only mention a weakness when the transcript actually supports it.

If the transcript provides insufficient evidence,
say so instead of inventing an answer.

The same transcript should produce a stable,
consistent analysis.

Return ONLY valid JSON.

The JSON structure MUST be:

{
  "en": {
    "summary": "",
    "key_points": [],
    "critical_analysis": [],
    "takeaways": []
  },
  "id": {
    "summary": "",
    "key_points": [],
    "critical_analysis": [],
    "takeaways": []
  }
}

ENGLISH REQUIREMENTS:

summary:
- exactly 1 concise paragraph.

key_points:
- exactly 5 items.
- Important points only.
- No duplicated points.

critical_analysis:
- 3 to 5 items.
- Evidence-based.
- Sharp but fair.

takeaways:
- exactly 3 items.

INDONESIAN REQUIREMENTS:

summary:
- exactly 1 concise paragraph.

key_points:
- exactly 5 items.

critical_analysis:
- 3 to 5 items.

takeaways:
- exactly 3 items.

The Indonesian version must preserve
the meaning of the English analysis.

Do not add facts during translation.
"""


# ============================================================
# BUILD AI PROMPT
# ============================================================

def build_ai_prompt(
    transcript_text,
    title=""
):

    return f"""
Analyze the following YouTube video transcript.

VIDEO TITLE:
{title}

TRANSCRIPT:

{transcript_text}

Remember:

1. Do not identify speakers.
2. Do not guess speaker identity.
3. Use only the transcript.
4. Be critical when evidence supports criticism.
5. Do not invent facts.
6. Return ONLY valid JSON.
"""


# ============================================================
# CALL CLOUDFLARE AI
# ============================================================

async def call_ai(
    system_prompt,
    user_prompt
):

    try:

        response = await env.AI.run(
            AI_MODEL,
            {
                "messages": [
                    {
                        "role":
                            "system",
                        "content":
                            system_prompt
                    },
                    {
                        "role":
                            "user",
                        "content":
                            user_prompt
                    }
                ],

                "temperature": 0.0,

                "seed": 42,

                "max_tokens": 2500
            }
        )

    except Exception as exc:

        raise RuntimeError(
            "Cloudflare Workers AI failed: "
            f"{type(exc).__name__}: "
            f"{str(exc)}"
        )

    # --------------------------------------------------------
    # Cloudflare Workers AI current response:
    #
    # {
    #   "response": "..."
    # }
    #
    # But support alternative response shapes too.
    # --------------------------------------------------------

    if isinstance(
        response,
        dict
    ):

        # Standard Workers AI
        content = response.get(
            "response",
            ""
        )

        if content:

            return clean_text(
                content
            )

        # Alternative shape
        result = response.get(
            "result"
        )

        if isinstance(
            result,
            dict
        ):

            content = result.get(
                "response",
                ""
            )

            if content:

                return clean_text(
                    content
                )

        # OpenAI-style shape
        choices = response.get(
            "choices"
        )

        if isinstance(
            choices,
            list
        ) and choices:

            first = choices[0]

            if isinstance(
                first,
                dict
            ):

                message = first.get(
                    "message",
                    {}
                )

                if isinstance(
                    message,
                    dict
                ):

                    content = message.get(
                        "content",
                        ""
                    )

                    if content:

                        return clean_text(
                            content
                        )

    # --------------------------------------------------------
    # String response
    # --------------------------------------------------------

    if isinstance(
        response,
        str
    ):

        return clean_text(
            response
        )

    raise RuntimeError(
        "Cloudflare AI returned an "
        "unexpected response format: "
        + repr(response)
    )


# ============================================================
# ANALYZE SINGLE PASS
# ============================================================

async def analyze_single_pass(
    transcript_text,
    title
):

    prompt = build_ai_prompt(
        transcript_text,
        title
    )

    raw = await call_ai(
        AI_SYSTEM_PROMPT,
        prompt
    )

    try:

        parsed = parse_ai_json(
            raw
        )

    except Exception as exc:

        raise RuntimeError(
            "AI returned invalid JSON. "
            f"Raw response: {raw[:3000]}. "
            f"Parser error: {str(exc)}"
        )

    en_data = normalize_analysis(
        parsed.get(
            "en",
            {}
        )
    )

    id_data = normalize_analysis(
        parsed.get(
            "id",
            {}
        )
    )

    # --------------------------------------------------------
    # If Indonesian result is missing,
    # don't crash the whole analysis.
    # --------------------------------------------------------

    if not id_data["summary"]:

        id_data = {
            "summary":
                "Analisis Bahasa Indonesia "
                "tidak tersedia.",

            "key_points": [],

            "critical_analysis": [],

            "takeaways": []
        }

    return {
        "en": en_data,
        "id": id_data
    }


# ============================================================
# CHUNK SYSTEM PROMPT
# ============================================================

CHUNK_SYSTEM_PROMPT = """
You are analyzing one segment of a longer YouTube transcript.

Analyze ONLY this segment.

Do not identify speakers.

Do not invent facts.

Focus on:
- important information
- claims
- arguments
- evidence
- assumptions
- logical weaknesses
- contradictions
- unsupported claims

Return ONLY valid JSON:

{
  "summary": "",
  "key_points": [],
  "critical_analysis": [],
  "takeaways": []
}
"""


# ============================================================
# ANALYZE CHUNK
# ============================================================

async def analyze_chunk(
    chunk,
    chunk_index,
    total_chunks
):

    prompt = f"""
Analyze transcript segment
{chunk_index} of {total_chunks}.

TRANSCRIPT SEGMENT:

{chunk}

Return ONLY valid JSON.
"""

    raw = await call_ai(
        CHUNK_SYSTEM_PROMPT,
        prompt
    )

    try:

        parsed = parse_ai_json(
            raw
        )

    except Exception as exc:

        raise RuntimeError(
            "Chunk AI returned invalid JSON: "
            f"{str(exc)}"
        )

    return normalize_analysis(
        parsed
    )


# ============================================================
# LONG VIDEO SYNTHESIS
# ============================================================

async def synthesize_long_video(
    chunk_results,
    title
):

    material = json.dumps(
        chunk_results,
        ensure_ascii=False
    )

    system_prompt = """
You are a professional video analyst.

Create a final analysis from
multiple transcript segment analyses.

Do not identify speakers.

Do not invent facts.

Remove duplicated points.

Prioritize the most important information.

Return ONLY valid JSON:

{
  "en": {
    "summary": "",
    "key_points": [],
    "critical_analysis": [],
    "takeaways": []
  },
  "id": {
    "summary": "",
    "key_points": [],
    "critical_analysis": [],
    "takeaways": []
  }
}

Requirements:

EN:
- summary: 1 paragraph
- key_points: exactly 5
- critical_analysis: 3 to 5
- takeaways: exactly 3

ID:
- summary: 1 paragraph
- key_points: exactly 5
- critical_analysis: 3 to 5
- takeaways: exactly 3
"""

    user_prompt = f"""
VIDEO TITLE:

{title}

SEGMENT ANALYSES:

{material}

Create the final analysis.
"""

    raw = await call_ai(
        system_prompt,
        user_prompt
    )

    try:

        parsed = parse_ai_json(
            raw
        )

    except Exception as exc:

        raise RuntimeError(
            "Final synthesis returned "
            "invalid JSON: "
            f"{str(exc)}"
        )

    return {
        "en":
            normalize_analysis(
                parsed.get(
                    "en",
                    {}
                )
            ),

        "id":
            normalize_analysis(
                parsed.get(
                    "id",
                    {}
                )
            )
    }


# ============================================================
# ANALYZE LONG TRANSCRIPT
# ============================================================

async def analyze_long_transcript(
    transcript,
    title
):

    chunks = build_chunks(
        transcript,
        CHUNK_SIZE
    )

    if not chunks:

        raise RuntimeError(
            "Unable to create transcript chunks."
        )

    results = []

    for index, chunk in enumerate(
        chunks,
        start=1
    ):

        result = await analyze_chunk(
            chunk,
            index,
            len(chunks)
        )

        results.append(
            result
        )

    return await synthesize_long_video(
        results,
        title
    )


# ============================================================
# ANALYZE ENDPOINT
# ============================================================

@app.post("/analyze")
async def analyze_video(
    payload: dict
):

    try:

        # ====================================================
        # 1. VALIDATE URL
        # ====================================================

        if not isinstance(
            payload,
            dict
        ):

            return {
                "status": "error",
                "message":
                    "Invalid request body.",
                "error_type":
                    "ValidationError"
            }

        url = clean_text(
            payload.get(
                "url",
                ""
            )
        )

        if not url:

            return {
                "status": "error",
                "message":
                    "YouTube URL is required.",
                "error_type":
                    "ValidationError"
            }

        video_id = extract_video_id(
            url
        )

        if not video_id:

            return {
                "status": "error",
                "message":
                    "Invalid YouTube URL.",
                "error_type":
                    "ValidationError"
            }

        normalized_url = (
            normalize_youtube_url(
                url
            )
        )

        # ====================================================
        # 2. GET YOUTUBE METADATA
        # ====================================================

        metadata = (
            await get_youtube_metadata(
                normalized_url
            )
        )

        video_title = clean_text(
            metadata.get(
                "title",
                ""
            )
        )

        # ====================================================
        # 3. GET TRANSCRIPT
        # ====================================================

        transcript_result = (
            await get_transcript(
                normalized_url
            )
        )

        if not transcript_result.get(
            "ok",
            False
        ):

            return {
                "status": "error",

                "message":
                    transcript_result.get(
                        "message",
                        "Failed to retrieve transcript."
                    ),

                "error_type":
                    "TranscriptAPIError",

                "error":
                    transcript_result.get(
                        "error",
                        ""
                    ),

                "http_status":
                    transcript_result.get(
                        "status_code",
                        502
                    )
            }

        transcript = (
            transcript_result.get(
                "transcript",
                []
            )
        )

        transcript_source = (
            transcript_result.get(
                "data",
                {}
            )
        )

        # ====================================================
        # 4. VALIDATE TRANSCRIPT
        # ====================================================

        if not transcript:

            return {
                "status": "error",
                "message":
                    "Transcript is empty.",
                "error_type":
                    "TranscriptEmpty"
            }

        full_transcript = (
            transcript_to_text(
                transcript
            )
        )

        if not full_transcript:

            return {
                "status": "error",
                "message":
                    "Transcript text is empty.",
                "error_type":
                    "TranscriptEmpty"
            }

        # ====================================================
        # 5. HASH
        # ====================================================

        transcript_hash = (
            create_transcript_hash(
                transcript
            )
        )

        # ====================================================
        # 6. ANALYZE
        # ====================================================

        transcript_characters = len(
            full_transcript
        )

        if (
            transcript_characters
            <= MAX_SINGLE_PASS_CHARS
        ):

            # ------------------------------------------------
            # FAST PATH
            # ------------------------------------------------

            summary = (
                await analyze_single_pass(
                    full_transcript,
                    video_title
                )
            )

            analysis_mode = (
                "single_pass"
            )

            total_chunks = 1

        else:

            # ------------------------------------------------
            # LONG VIDEO PATH
            # ------------------------------------------------

            summary = (
                await analyze_long_transcript(
                    transcript,
                    video_title
                )
            )

            analysis_mode = (
                "chunked"
            )

            total_chunks = len(
                build_chunks(
                    transcript,
                    CHUNK_SIZE
                )
            )

        # ====================================================
        # 7. RETURN
        # ====================================================

        return {
            "status": "success",

            "version": "3.0.0",

            "youtube_url":
                normalized_url,

            "video_id":
                video_id,

            "title":
                video_title,

            "language":
                transcript_source.get(
                    "language",
                    ""
                )
                if isinstance(
                    transcript_source,
                    dict
                )
                else "",

            "metadata": {
                "youtube_title":
                    metadata.get(
                        "title",
                        ""
                    ),

                "channel":
                    metadata.get(
                        "author_name",
                        ""
                    ),

                "author_url":
                    metadata.get(
                        "author_url",
                        ""
                    ),

                "thumbnail_url":
                    metadata.get(
                        "thumbnail_url",
                        ""
                    )
            },

            "processing": {

                "mode":
                    analysis_mode,

                "total_segments":
                    len(transcript),

                "total_chunks":
                    total_chunks,

                "transcript_characters":
                    transcript_characters,

                "transcript_hash":
                    transcript_hash
            },

            "summary":
                summary,

            "transcript":
                transcript
        }

    except Exception as error:

        # ====================================================
        # IMPORTANT:
        # ALWAYS RETURN FRONTEND-FRIENDLY ERROR
        # ====================================================

        return {
            "status": "error",

            "message":
                "Worker exception",

            "error_type":
                type(error).__name__,

            "error":
                str(error),

            "http_status":
                500
        }


# ============================================================
# CLOUDFLARE WORKERS ENTRYPOINT
# ============================================================

Default = asgi.entrypoint(app)
