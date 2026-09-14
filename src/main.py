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
    description="Professional AI Video Analysis API",
    version="5.0.0"
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
            "V5 is running on Cloudflare"
        ),
        "version": "5.0.0"
    }


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
async def health():

    return {
        "status": "healthy",
        "version": "5.0.0",
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


# ============================================================
# GENERAL ERROR HANDLER
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
    # Already dictionary
    # --------------------------------------------------------

    if isinstance(
        text,
        dict
    ):

        return text

    text = clean_text(
        text
    )

    if not text:

        raise ValueError(
            "AI returned empty response"
        )

    # --------------------------------------------------------
    # Remove markdown fence
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
    # Standard JSON
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
    # JSON inside other text
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
        # Python dictionary fallback
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
    # Complete Python dictionary
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

    raise ValueError(
        "AI response is not valid JSON"
    )


# ============================================================
# NORMALIZE LIST
# ============================================================

def normalize_list(
    value,
    maximum
):

    if not isinstance(
        value,
        list
    ):

        return []

    result = []

    for item in value:

        text = clean_text(
            item
        )

        if text:

            result.append(
                text
            )

    return result[:maximum]


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

    key_points = normalize_list(
        data.get(
            "key_points",
            []
        ),
        5
    )

    critical_analysis = normalize_list(
        data.get(
            "critical_analysis",
            []
        ),
        5
    )

    implications = normalize_list(
        data.get(
            "implications",
            []
        ),
        4
    )

    takeaways = normalize_list(
        data.get(
            "takeaways",
            []
        ),
        3
    )

    return {

        "summary":
            summary,

        "key_points":
            key_points,

        "critical_analysis":
            critical_analysis,

        "implications":
            implications,

        "takeaways":
            takeaways
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

    try:

        data = response.json()

    except Exception:

        data = {}

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
# PROFESSIONAL AI SYSTEM PROMPT
# ============================================================

AI_SYSTEM_PROMPT = """
You are a professional media and content analyst.

Your task is to analyze a YouTube transcript for a
professional office-quality report.

The analysis must be substantially more rigorous than
a casual summary.

============================================================
SOURCE DISCIPLINE
============================================================

Use ONLY the transcript provided.

Do NOT use outside knowledge.

Do NOT search the internet.

Do NOT invent facts.

Do NOT assume facts that are not explicitly supported.

Do NOT identify speakers.

Do NOT guess speaker identities.

Do NOT attribute statements to specific people.

Do NOT create quotations that do not exist.

Do NOT add information merely because it is common knowledge.

============================================================
ANALYTICAL APPROACH
============================================================

First determine:

1. What is the central subject?
2. What are the major arguments or themes?
3. What claims are actually made?
4. What evidence or examples are provided?
5. Which statements are factual?
6. Which statements are opinions?
7. Which statements are assumptions?
8. Which conclusions are interpretations?
9. What important context is missing?
10. Are there contradictions or logical gaps?

The analysis must prioritize substance over surface-level
description.

Do NOT simply repeat the transcript.

============================================================
CRITICAL ANALYSIS
============================================================

Critical analysis must be evidence-based.

Look for:

- unsupported claims
- weak evidence
- logical gaps
- contradictions
- overgeneralization
- exaggeration
- causal claims without sufficient evidence
- selective presentation
- missing context
- assumptions presented as facts
- conclusions that are stronger than the evidence
- ambiguity
- internal inconsistency

However:

Do NOT manufacture criticism.

If the transcript does not support a criticism,
do not create one.

If an argument is reasonable and well supported,
say so.

The objective is professional analysis,
not negativity.

============================================================
PROFESSIONAL STANDARD
============================================================

Write as if the output will be read by:

- management
- analysts
- researchers
- consultants
- corporate staff

Use precise and neutral language.

Avoid:

- sensational language
- emotional language
- slang
- excessive repetition
- vague statements
- unnecessary adjectives

============================================================
SUMMARY
============================================================

The summary must answer:

- What is this content about?
- What is the central message?
- What are the most important issues?
- What conclusion can reasonably be drawn?

The summary must NOT simply list topics.

It should explain the overall substance.

Maximum approximately 150 words.

============================================================
KEY POINTS
============================================================

Provide exactly 5 important points.

Each point should contain substantive information.

Do not repeat the summary.

Do not create trivial points.

============================================================
CRITICAL ANALYSIS
============================================================

Provide exactly 3 meaningful analytical observations.

Each observation must explain:

- what the issue is
- why it matters

Only use evidence available in the transcript.

============================================================
IMPLICATIONS
============================================================

Provide exactly 4 implications when the transcript supports them.

Implications may include:

- practical consequences
- risks
- opportunities
- lessons
- considerations for decision makers

Do not invent implications unrelated to the transcript.

If fewer implications are genuinely supported,
provide fewer.

============================================================
TAKEAWAYS
============================================================

Provide exactly 3 concise takeaways.

They should represent the most useful conclusions
a professional reader should remember.

============================================================
LANGUAGES
============================================================

Produce both:

ENGLISH

and

INDONESIAN

The Indonesian version must preserve the meaning
of the English version.

Do not add new facts during translation.

============================================================
OUTPUT FORMAT
============================================================

Return ONLY a valid JSON object.

Do NOT use Markdown.

Do NOT use code fences.

Do NOT add explanations before or after the JSON.

The structure MUST be:

{
  "en": {
    "summary": "",
    "key_points": [],
    "critical_analysis": [],
    "implications": [],
    "takeaways": []
  },
  "id": {
    "summary": "",
    "key_points": [],
    "critical_analysis": [],
    "implications": [],
    "takeaways": []
  }
}
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

============================================================
VIDEO TITLE
============================================================

{title}

============================================================
TRANSCRIPT
============================================================

{transcript_text}

============================================================
FINAL INSTRUCTION
============================================================

Produce a professional, evidence-based analysis.

Do not identify speakers.

Do not use outside knowledge.

Do not invent information.

Prioritize the central themes and substantive claims.

Distinguish facts, opinions, assumptions and interpretations.

Identify weaknesses only when supported by the transcript.

Return ONLY the required JSON object.
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

                "response_format": {
                    "type":
                        "json_object"
                },

                "temperature":
                    0.0,

                "seed":
                    42,

                "max_tokens":
                    5000
            }
        )

    except Exception as exc:

        raise RuntimeError(
            "Cloudflare Workers AI failed: "
            f"{type(exc).__name__}: "
            f"{str(exc)}"
        )

    # ========================================================
    # STANDARD RESPONSE
    # ========================================================

    if isinstance(
        response,
        dict
    ):

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

        # ====================================================
        # RESULT FALLBACK
        # ====================================================

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

        # ====================================================
        # OPENAI COMPATIBLE FALLBACK
        # ====================================================

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

    # ========================================================
    # STRING RESPONSE
    # ========================================================

    if isinstance(
        response,
        str
    ):

        return response.strip()

    raise RuntimeError(
        "Cloudflare AI returned an "
        "unexpected response format: "
        + repr(response)
    )


# ============================================================
# SINGLE PASS ANALYSIS
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

        preview = clean_text(
            raw
        )

        if len(preview) > 5000:

            preview = (
                preview[:5000]
                + "..."
            )

        raise RuntimeError(
            "AI returned invalid JSON. "
            f"Raw response: {preview}. "
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

    return {

        "en":
            en_data,

        "id":
            id_data
    }


# ============================================================
# LONG TRANSCRIPT CHUNK PROMPT
# ============================================================

CHUNK_SYSTEM_PROMPT = """
You are a professional transcript analyst.

Analyze ONLY the provided transcript segment.

Do not identify speakers.

Do not guess identities.

Do not use outside knowledge.

Do not invent facts.

Extract substantive information and analytical issues.

Focus on:

- claims
- arguments
- evidence
- important facts
- assumptions
- contradictions
- logical weaknesses
- missing evidence
- important implications

Return ONLY valid JSON.

Structure:

{
  "summary": "",
  "key_points": [],
  "critical_analysis": [],
  "implications": [],
  "takeaways": []
}

Keep all items concise and evidence-based.
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
You are a senior professional content analyst.

Create a final professional analysis from
multiple transcript segment analyses.

The final result must represent the ENTIRE video.

Do not over-focus on one segment.

Do not identify speakers.

Do not invent facts.

Remove duplicated points.

Prioritize important information.

Distinguish facts, claims, opinions,
assumptions and interpretations.

Critical observations must be supported
by the segment analyses.

Return ONLY valid JSON.

Structure:

{
  "en": {
    "summary": "",
    "key_points": [],
    "critical_analysis": [],
    "implications": [],
    "takeaways": []
  },
  "id": {
    "summary": "",
    "key_points": [],
    "critical_analysis": [],
    "implications": [],
    "takeaways": []
  }
}

Requirements:

summary:
- approximately 100 to 150 words

key_points:
- exactly 5

critical_analysis:
- exactly 3

implications:
- up to 4

takeaways:
- exactly 3
"""

    user_prompt = f"""
VIDEO TITLE:

{title}

ANALYSES FROM ALL TRANSCRIPT SEGMENTS:

{material}

Create the final professional analysis.
Make sure important information from later
segments is not ignored.
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

        if len(preview) > 5000:

            preview = (
                preview[:5000]
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
# LONG TRANSCRIPT ANALYSIS
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
        # VALIDATE REQUEST
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
        # GET URL
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
        # NORMALIZE URL
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
        # GET TRANSCRIPT
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
        # TRANSCRIPT LANGUAGE
        # ====================================================

        transcript_language = ""

        if isinstance(
            transcript_source,
            dict
        ):

            transcript_language = (
                clean_text(
                    transcript_source.get(
                        "language",
                        ""
                    )
                )
            )

        # ====================================================
        # AI ANALYSIS
        # ====================================================

        transcript_characters = len(
            full_transcript
        )

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
        # IMPORTANT:
        # TRANSCRIPT RESPONSE FORMAT
        #
        # This structure is required by the current
        # script.js:
        #
        # data.transcript.title
        # data.transcript.language
        # data.transcript.transcript
        # ====================================================

        transcript_response = {

            "title":
                video_title,

            "language":
                transcript_language,

            "transcript":
                transcript
        }

        # ====================================================
        # SUCCESS
        # ====================================================

        return {

            "status":
                "success",

            "version":
                "5.0.0",

            "youtube_url":
                normalized_url,

            "video_id":
                video_id,

            "title":
                video_title,

            "language":
                transcript_language,

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
                transcript_response
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
