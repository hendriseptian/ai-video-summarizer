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
import ast


# ============================================================
# APP
# ============================================================

app = FastAPI(
    title="AI Video Summarizer API",
    description="AI Video Summarizer Backend",
    version="4.0.0"
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

AI_MODEL = (
    "@cf/meta/llama-3.1-8b-instruct-fast"
)

MAX_SINGLE_PASS_CHARS = 100000

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
            "V4 is running on Cloudflare"
        ),
        "version": "4.0.0"
    }


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
async def health():

    return {
        "status": "healthy",
        "version": "4.0.0",
        "model": AI_MODEL
    }


# ============================================================
# ERROR HANDLER - HTTP EXCEPTION
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


# ============================================================
# ERROR HANDLER - GENERAL EXCEPTION
# ============================================================

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

    url = clean_text(
        url
    )

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

    return clean_text(
        url
    )


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

    # --------------------------------------------------------
    # Already a Python dictionary
    # --------------------------------------------------------

    if isinstance(
        text,
        dict
    ):

        return text

    # --------------------------------------------------------
    # Empty response
    # --------------------------------------------------------

    text = clean_text(
        text
    )

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
    # Try standard JSON
    # --------------------------------------------------------

    try:

        result = json.loads(
            text
        )

        if isinstance(
            result,
            dict
        ):

            return result

    except Exception:

        pass

    # --------------------------------------------------------
    # Find JSON object inside additional text
    # --------------------------------------------------------

    start = text.find(
        "{"
    )

    end = text.rfind(
        "}"
    )

    if (
        start >= 0
        and end > start
    ):

        candidate = (
            text[
                start:
                end + 1
            ]
        )

        # ----------------------------------------------------
        # Try standard JSON again
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # Try Python dictionary syntax
        # ----------------------------------------------------

        try:

            result = ast.literal_eval(
                candidate
            )

            if isinstance(
                result,
                dict
            ):

                return result

        except Exception:

            pass

    # --------------------------------------------------------
    # Try complete response as Python dictionary
    # --------------------------------------------------------

    try:

        result = ast.literal_eval(
            text
        )

        if isinstance(
            result,
            dict
        ):

            return result

    except Exception:

        pass

    # --------------------------------------------------------
    # FAIL
    # --------------------------------------------------------

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

        "summary":
            summary,

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
                "text":
                    text,

                "start":
                    start,

                "duration":
                    duration
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
        normalize_youtube_url(
            url
        )
    )

    params = {
        "url":
            normalized_url,

        "format":
            "json"
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

                "title":
                    "",

                "author_name":
                    "",

                "author_url":
                    "",

                "thumbnail_url":
                    "",

                "video_id":
                    extract_video_id(
                        normalized_url
                    )
            }

        data = response.json()

        return {

            "title":
                clean_text(
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

            "title":
                "",

            "author_name":
                "",

            "author_url":
                "",

            "thumbnail_url":
                "",

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
        normalize_youtube_url(
            url
        )
    )

    video_id = extract_video_id(
        normalized_url
    )

    if not video_id:

        return {

            "ok":
                False,

            "status_code":
                400,

            "message":
                "Invalid YouTube URL.",

            "data":
                None
        }

    # IMPORTANT:
    # FreeTranscriptAPI uses GET
    # and query parameter video_url

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

            "ok":
                False,

            "status_code":
                502,

            "message":
                "Transcript API connection failed.",

            "error_type":
                type(exc).__name__,

            "error":
                str(exc),

            "data":
                None
        }

    # --------------------------------------------------------
    # Parse API response
    # --------------------------------------------------------

    try:

        data = response.json()

    except Exception:

        data = {}

    # --------------------------------------------------------
    # API error
    # --------------------------------------------------------

    if response.status_code >= 400:

        return {

            "ok":
                False,

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
    # Normalize transcript
    # --------------------------------------------------------

    transcript = normalize_transcript(
        data
    )

    if not transcript:

        return {

            "ok":
                False,

            "status_code":
                404,

            "message":
                (
                    "Transcript tidak ditemukan "
                    "atau video tidak memiliki caption."
                ),

            "error":
                data,

            "data":
                data
        }

    return {

        "ok":
            True,

        "status_code":
            200,

        "message":
            "Transcript retrieved.",

        "data":
            data,

        "transcript":
            transcript
    }


# ============================================================
# AI SYSTEM PROMPT
# ============================================================

AI_SYSTEM_PROMPT = """
You are a professional video content analyst.

Analyze ONLY the provided YouTube transcript.

Do NOT use outside knowledge.

Do NOT invent facts.

Do NOT identify speakers.

Do NOT guess who said something.

Do NOT assign statements to specific people.

Do NOT assume missing context.

The analysis must be:

- sharp
- critical
- evidence-based
- neutral
- concise
- useful
- consistent

IMPORTANT:

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

Do not criticize simply for the sake of criticizing.

If the transcript does not provide enough evidence,
say so instead of inventing an answer.

The same transcript should produce a stable,
consistent analysis.

RETURN ONLY A VALID JSON OBJECT.

Do not use Markdown.

Do not use code fences.

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

ENGLISH:

summary:
- exactly 1 concise paragraph
- maximum 100 words

key_points:
- exactly 5 items
- each item maximum 20 words
- important points only
- no duplicated points

critical_analysis:
- exactly 3 items
- each item maximum 25 words
- evidence-based
- sharp but fair

takeaways:
- exactly 3 items
- each item maximum 18 words

INDONESIAN:

summary:
- exactly 1 concise paragraph
- maximum 100 words

key_points:
- exactly 5 items
- each item maximum 20 words

critical_analysis:
- exactly 3 items
- each item maximum 25 words

takeaways:
- exactly 3 items
- each item maximum 18 words

The Indonesian version must preserve
the meaning of the English analysis.

Do not add facts during translation.

Do not identify speakers in either language.
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

IMPORTANT:

1. Analyze ONLY the transcript.
2. Do not use outside knowledge.
3. Do not identify speakers.
4. Do not guess speaker identity.
5. Do not invent facts.
6. Distinguish facts from claims and opinions.
7. Be critical when the transcript supports criticism.
8. Do not criticize without evidence.
9. Keep the analysis concise.
10. Return ONLY valid JSON.
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

                # ====================================================
                # JSON MODE
                # ====================================================

                "response_format": {
                    "type":
                        "json_object"
                },

                # ====================================================
                # STABLE OUTPUT
                # ====================================================

                "temperature":
                    0.0,

                "seed":
                    42,

                # ====================================================
                # ENOUGH SPACE FOR EN + ID
                # ====================================================

                "max_tokens":
                    4000
            }
        )

    except Exception as exc:

        raise RuntimeError(
            "Cloudflare Workers AI failed: "
            f"{type(exc).__name__}: "
            f"{str(exc)}"
        )

    # ============================================================
    # RESPONSE DICTIONARY
    # ============================================================

    if isinstance(
        response,
        dict
    ):

        # --------------------------------------------------------
        # Standard response
        # --------------------------------------------------------

        content = response.get(
            "response"
        )

        if content is not None:

            if isinstance(
                content,
                dict
            ):

                return json.dumps(
                    content,
                    ensure_ascii=False
                )

            if isinstance(
                content,
                str
            ):

                return content.strip()

        # --------------------------------------------------------
        # Result fallback
        # --------------------------------------------------------

        result = response.get(
            "result"
        )

        if isinstance(
            result,
            dict
        ):

            content = result.get(
                "response"
            )

            if isinstance(
                content,
                dict
            ):

                return json.dumps(
                    content,
                    ensure_ascii=False
                )

            if isinstance(
                content,
                str
            ):

                return content.strip()

        # --------------------------------------------------------
        # OpenAI compatible fallback
        # --------------------------------------------------------

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

                    if isinstance(
                        content,
                        dict
                    ):

                        return json.dumps(
                            content,
                            ensure_ascii=False
                        )

                    if isinstance(
                        content,
                        str
                    ):

                        return content.strip()

    # ============================================================
    # STRING RESPONSE
    # ============================================================

    if isinstance(
        response,
        str
    ):

        return response.strip()

    # ============================================================
    # UNKNOWN RESPONSE
    # ============================================================

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

    # --------------------------------------------------------
    # Parse AI response
    # --------------------------------------------------------

    try:

        parsed = parse_ai_json(
            raw
        )

    except Exception as exc:

        preview = clean_text(
            raw
        )

        if len(preview) > 4000:

            preview = (
                preview[:4000]
                + "..."
            )

        raise RuntimeError(
            "AI returned invalid JSON. "
            f"Raw response: {preview}. "
            f"Parser error: {str(exc)}"
        )

    # --------------------------------------------------------
    # EN
    # --------------------------------------------------------

    en_data = normalize_analysis(
        parsed.get(
            "en",
            {}
        )
    )

    # --------------------------------------------------------
    # ID
    # --------------------------------------------------------

    id_data = normalize_analysis(
        parsed.get(
            "id",
            {}
        )
    )

    # --------------------------------------------------------
    # Fallback if Indonesian missing
    # --------------------------------------------------------

    if not id_data["summary"]:

        id_data = {

            "summary":
                (
                    "Analisis Bahasa Indonesia "
                    "tidak tersedia."
                ),

            "key_points":
                [],

            "critical_analysis":
                [],

            "takeaways":
                []
        }

    return {

        "en":
            en_data,

        "id":
            id_data
    }


# ============================================================
# CHUNK SYSTEM PROMPT
# ============================================================

CHUNK_SYSTEM_PROMPT = """
You are analyzing one segment of a longer YouTube transcript.

Analyze ONLY this segment.

Do not identify speakers.

Do not guess speaker identity.

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

Return ONLY valid JSON.

Do not use Markdown.

Do not use code fences.

Structure:

{
  "summary": "",
  "key_points": [],
  "critical_analysis": [],
  "takeaways": []
}

Requirements:

summary:
- concise
- maximum 80 words

key_points:
- maximum 5 items
- concise

critical_analysis:
- maximum 3 items
- concise
- evidence-based

takeaways:
- maximum 3 items
- concise
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
You are a professional video content analyst.

Create a final analysis from
multiple transcript segment analyses.

Do not identify speakers.

Do not invent facts.

Remove duplicated points.

Prioritize the most important information.

Be sharp, critical, neutral and evidence-based.

Return ONLY valid JSON.

Do not use Markdown.

Do not use code fences.

Structure:

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

EN:

summary:
- exactly 1 paragraph
- maximum 100 words

key_points:
- exactly 5 items

critical_analysis:
- exactly 3 items

takeaways:
- exactly 3 items

ID:

summary:
- exactly 1 paragraph
- maximum 100 words

key_points:
- exactly 5 items

critical_analysis:
- exactly 3 items

takeaways:
- exactly 3 items

Do not identify speakers.
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

        preview = clean_text(
            raw
        )

        if len(preview) > 4000:

            preview = (
                preview[:4000]
                + "..."
            )

        raise RuntimeError(
            "Final synthesis returned "
            "invalid JSON. "
            f"Raw response: {preview}. "
            f"Parser error: {str(exc)}"
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
        # VALIDATE BODY
        # ====================================================

        if not isinstance(
            payload,
            dict
        ):

            return {

                "status":
                    "error",

                "message":
                    "Invalid request body.",

                "error_type":
                    "ValidationError"
            }

        # ====================================================
        # URL
        # ====================================================

        url = clean_text(
            payload.get(
                "url",
                ""
            )
        )

        if not url:

            return {

                "status":
                    "error",

                "message":
                    "YouTube URL is required.",

                "error_type":
                    "ValidationError"
            }

        # ====================================================
        # VIDEO ID
        # ====================================================

        video_id = extract_video_id(
            url
        )

        if not video_id:

            return {

                "status":
                    "error",

                "message":
                    "Invalid YouTube URL.",

                "error_type":
                    "ValidationError"
            }

        # ====================================================
        # NORMALIZED URL
        # ====================================================

        normalized_url = (
            normalize_youtube_url(
                url
            )
        )

        # ====================================================
        # YOUTUBE METADATA
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
        # TRANSCRIPT
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

                "status":
                    "error",

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

        # ====================================================
        # TRANSCRIPT DATA
        # ====================================================

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

        if not transcript:

            return {

                "status":
                    "error",

                "message":
                    "Transcript is empty.",

                "error_type":
                    "TranscriptEmpty"
            }

        # ====================================================
        # TRANSCRIPT TEXT
        # ====================================================

        full_transcript = (
            transcript_to_text(
                transcript
            )
        )

        if not full_transcript:

            return {

                "status":
                    "error",

                "message":
                    "Transcript text is empty.",

                "error_type":
                    "TranscriptEmpty"
            }

        # ====================================================
        # HASH
        # ====================================================

        transcript_hash = (
            create_transcript_hash(
                transcript
            )
        )

        # ====================================================
        # TRANSCRIPT LENGTH
        # ====================================================

        transcript_characters = len(
            full_transcript
        )

        # ====================================================
        # AI ANALYSIS
        # ====================================================

        if (
            transcript_characters
            <= MAX_SINGLE_PASS_CHARS
        ):

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
        # SUCCESS RESPONSE
        # ====================================================

        return {

            "status":
                "success",

            "version":
                "4.0.0",

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

            # =================================================
            # METADATA
            # =================================================

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

            # =================================================
            # PROCESSING
            # =================================================

            "processing": {

                "mode":
                    analysis_mode,

                "total_segments":
                    len(
                        transcript
                    ),

                "total_chunks":
                    total_chunks,

                "transcript_characters":
                    transcript_characters,

                "transcript_hash":
                    transcript_hash
            },

            # =================================================
            # AI SUMMARY
            # =================================================

            "summary":
                summary,

            # =================================================
            # TRANSCRIPT
            # =================================================

            "transcript":
                transcript
        }

    except Exception as error:

        return {

            "status":
                "error",

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

Default = asgi.entrypoint(
    app
)
