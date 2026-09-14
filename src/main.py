from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from workers import asgi, env
import httpx2 as httpx

import ast
import hashlib
import json
import re


# ============================================================
# APPLICATION
# ============================================================

app = FastAPI(
    title="AI Video Summarizer API",
    version="7.1.0"
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
# CONFIGURATION
# ============================================================

AI_MODEL = "@cf/meta/llama-3.1-8b-instruct-fast"

TRANSCRIPT_API_URL = (
    "https://api.freetranscriptapi.com/v1/transcript"
)

CHUNK_SIZE = 18000

MAX_SINGLE_PASS_CHARS = 100000

MAX_FINAL_CONTEXT_CHARS = 90000

AI_TIMEOUT = 120.0

AI_MAX_TOKENS = 5000


# ============================================================
# SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """
You are a professional video content analyst.

Analyze ONLY the supplied transcript.

Do not use outside knowledge.

Do not invent facts.

Do not assume facts that are not stated.

Do not identify speakers.

Return ONLY valid JSON.

The JSON must have exactly this structure:

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

============================================================
EXECUTIVE SUMMARY
============================================================

Write a comprehensive executive summary based ONLY on
the transcript.

The summary should normally contain approximately
180-300 words.

The summary must explain the overall content of the video,
not merely state the main topic.

When supported by the transcript, naturally explain:

1. The main context or subject.
2. Important events, facts, statements, or developments.
3. Relevant responses, reactions, actions, or perspectives.
4. Important consequences, impacts, concerns, or issues.
5. The overall significance or conclusion.

Write the summary as coherent professional prose.

Use 1-3 paragraphs.

Do NOT use bullet points.

Do NOT create headings inside the summary.

Do NOT simply repeat the transcript sentence by sentence.

Do NOT make the summary unnecessarily vague.

Do NOT omit important information merely to keep it short.

Do NOT invent information.

If an aspect is not discussed in the transcript,
do not fabricate it.

The summary should allow a reader who has not watched
the video to understand the main subject, important
developments, context, implications, and conclusion.

============================================================
KEY POINTS
============================================================

Provide 5-8 of the most important points.

Each point should normally contain 1-3 sentences.

Each point must contain enough context to explain
why the information matters.

Do not repeat the same information.

Use only information supported by the transcript.

============================================================
CRITICAL ANALYSIS
============================================================

Provide 4-6 meaningful analytical observations.

Focus on:

- significance
- limitations
- missing information
- inconsistencies
- concerns
- important considerations

Each item MUST be a normal string.

Do NOT return objects or dictionaries.

Do NOT use labels such as:

Issue:
Reason:
Evidence:
Observation:
Transcript:

Do not invent facts.

============================================================
IMPLICATIONS
============================================================

Provide 3-5 reasonable implications derived
from the transcript.

Explain why the information matters and what
potential consequences or considerations arise.

Do not invent facts.

============================================================
KEY TAKEAWAYS
============================================================

Provide 3-5 meaningful conclusions.

Do not simply copy the key points.

Do not invent facts.

============================================================
LANGUAGE
============================================================

English must be professional and natural.

Indonesian must be professional, natural,
and suitable for an office analytical report.

Do not translate word-for-word when this produces
unnatural language.

============================================================
OUTPUT
============================================================

Return ONLY valid JSON.

Do not use markdown.

Do not use ```json.

Do not add explanations before or after the JSON.
"""


# ============================================================
# CHUNK PROMPT
# ============================================================

CHUNK_PROMPT = """
Extract important factual information from this transcript
section for later synthesis.

Use ONLY information contained in the transcript.

Do not invent facts.

Do not identify speakers.

Capture:

- important context
- important events
- important facts
- important statements
- reactions
- responses
- concerns
- developments
- impacts
- other information relevant to the final report

TRANSCRIPT SECTION:
"""


# ============================================================
# ERROR RESPONSE
# ============================================================

def error_response(
    message,
    error_type="server_error",
    status=500
):
    return {
        "status": "error",
        "message": message,
        "error": message,
        "error_type": error_type,
        "http_status": status
    }


# ============================================================
# YOUTUBE URL NORMALIZATION
# ============================================================

def normalize_youtube_url(
    url
):
    if not isinstance(
        url,
        str
    ):
        return ""

    url = url.strip()

    if not url:
        return ""

    url = re.sub(
        r"\s+",
        "",
        url
    )

    patterns = [
        r"youtube\.com/watch\?[^#]*v=([A-Za-z0-9_-]{11})",
        r"youtu\.be/([A-Za-z0-9_-]{11})",
        r"youtube\.com/shorts/([A-Za-z0-9_-]{11})"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            url,
            re.IGNORECASE
        )

        if match:

            video_id = match.group(
                1
            )

            return (
                "https://www.youtube.com/watch?v="
                + video_id
            )

    return ""


# ============================================================
# EXTRACT VIDEO ID
# ============================================================

def extract_video_id(
    url
):
    normalized = normalize_youtube_url(
        url
    )

    if not normalized:
        return ""

    match = re.search(
        r"[?&]v=([A-Za-z0-9_-]{11})",
        normalized
    )

    if match:
        return match.group(
            1
        )

    return ""


# ============================================================
# FORMAT TIMESTAMP
# ============================================================

def format_timestamp(
    seconds
):
    try:
        total_seconds = int(
            float(seconds)
        )
    except Exception:
        total_seconds = 0

    if total_seconds < 0:
        total_seconds = 0

    hours = total_seconds // 3600

    minutes = (
        total_seconds % 3600
    ) // 60

    secs = (
        total_seconds % 60
    )

    if hours > 0:

        return (
            f"{hours:02d}:"
            f"{minutes:02d}:"
            f"{secs:02d}"
        )

    return (
        f"{minutes:02d}:"
        f"{secs:02d}"
    )


# ============================================================
# BUILD TRANSCRIPT TEXT
# ============================================================

def build_transcript_text(
    segments
):
    lines = []

    if not isinstance(
        segments,
        list
    ):
        return ""

    for segment in segments:

        if not isinstance(
            segment,
            dict
        ):
            continue

        text = str(
            segment.get(
                "text",
                ""
            )
        ).strip()

        if not text:
            continue

        start = segment.get(
            "start",
            0
        )

        timestamp = format_timestamp(
            start
        )

        lines.append(
            f"[{timestamp}] {text}"
        )

    return "\n".join(
        lines
    )


# ============================================================
# TRANSCRIPT HASH
# ============================================================

def create_transcript_hash(
    text
):
    return hashlib.sha256(
        text.encode(
            "utf-8"
        )
    ).hexdigest()


# ============================================================
# CHUNK TEXT
# ============================================================

def chunk_text(
    text,
    chunk_size=CHUNK_SIZE
):
    if not text:
        return []

    chunks = []

    start = 0

    text_length = len(
        text
    )

    while start < text_length:

        end = min(
            start + chunk_size,
            text_length
        )

        if end < text_length:

            split_position = text.rfind(
                "\n",
                start,
                end
            )

            minimum_split = (
                start +
                int(
                    chunk_size *
                    0.65
                )
            )

            if (
                split_position >
                minimum_split
            ):
                end = split_position

        chunk = text[
            start:end
        ].strip()

        if chunk:
            chunks.append(
                chunk
            )

        start = end

    return chunks


# ============================================================
# RUN AI
# ============================================================

async def run_ai(
    system_prompt,
    user_prompt,
    max_tokens=AI_MAX_TOKENS
):

    payload = {
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
        "response_format": {
            "type": "json_object"
        },
        "temperature": 0.0,
        "seed": 42,
        "max_tokens": max_tokens
    }

    try:

        result = await env.AI.run(
            AI_MODEL,
            payload
        )

        return result

    except Exception as error:

        raise RuntimeError(
            "AI model request failed: "
            + str(error)
        )


# ============================================================
# EXTRACT AI TEXT
# ============================================================

def extract_ai_text(
    result
):

    if isinstance(
        result,
        str
    ):
        return result

    if isinstance(
        result,
        dict
    ):

        if "response" in result:

            response = result[
                "response"
            ]

            if isinstance(
                response,
                str
            ):
                return response

            if isinstance(
                response,
                dict
            ):
                return json.dumps(
                    response,
                    ensure_ascii=False
                )

        if "result" in result:

            nested = result[
                "result"
            ]

            if isinstance(
                nested,
                str
            ):
                return nested

            if isinstance(
                nested,
                dict
            ):
                return json.dumps(
                    nested,
                    ensure_ascii=False
                )

        return json.dumps(
            result,
            ensure_ascii=False
        )

    return str(
        result
    )


# ============================================================
# CLEAN JSON
# ============================================================

def clean_json_text(
    text
):

    if not text:
        return ""

    text = str(
        text
    ).strip()

    text = re.sub(
        r"^```(?:json)?\s*",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"\s*```$",
        "",
        text
    )

    first = text.find(
        "{"
    )

    last = text.rfind(
        "}"
    )

    if (
        first >= 0 and
        last > first
    ):

        text = text[
            first:last + 1
        ]

    return text.strip()


# ============================================================
# PARSE AI JSON
# ============================================================

def parse_ai_json(
    result
):

    text = extract_ai_text(
        result
    )

    text = clean_json_text(
        text
    )

    if not text:

        raise ValueError(
            "AI returned an empty response."
        )

    try:

        parsed = json.loads(
            text
        )

        if isinstance(
            parsed,
            dict
        ):
            return parsed

    except Exception:
        pass

    try:

        parsed = ast.literal_eval(
            text
        )

        if isinstance(
            parsed,
            dict
        ):
            return parsed

    except Exception:
        pass

    raise ValueError(
        "AI returned invalid JSON."
    )


# ============================================================
# NORMALIZE TEXT
# ============================================================

def normalize_text(
    value
):

    if value is None:
        return ""

    if isinstance(
        value,
        str
    ):
        return value.strip()

    if isinstance(
        value,
        list
    ):

        parts = []

        for item in value:

            text = normalize_text(
                item
            )

            if text:
                parts.append(
                    text
                )

        return " ".join(
            parts
        ).strip()

    if isinstance(
        value,
        dict
    ):

        preferred_keys = [
            "issue",
            "reason",
            "evidence",
            "observation",
            "analysis",
            "text",
            "content"
        ]

        parts = []

        for key in preferred_keys:

            if key in value:

                text = normalize_text(
                    value[key]
                )

                if text:
                    parts.append(
                        text
                    )

        if parts:

            return " ".join(
                parts
            ).strip()

        return " ".join(
            normalize_text(
                item
            )
            for item in value.values()
            if normalize_text(
                item
            )
        ).strip()

    return str(
        value
    ).strip()


# ============================================================
# NORMALIZE LIST
# ============================================================

def normalize_list(
    value
):

    if value is None:
        return []

    if isinstance(
        value,
        list
    ):

        output = []

        for item in value:

            text = normalize_text(
                item
            )

            if text:
                output.append(
                    text
                )

        return output

    text = normalize_text(
        value
    )

    if text:
        return [
            text
        ]

    return []


# ============================================================
# NORMALIZE LANGUAGE BLOCK
# ============================================================

def normalize_language_block(
    block
):

    if not isinstance(
        block,
        dict
    ):
        block = {}

    return {
        "summary": normalize_text(
            block.get(
                "summary",
                ""
            )
        ),

        "key_points": normalize_list(
            block.get(
                "key_points",
                []
            )
        ),

        "critical_analysis": normalize_list(
            block.get(
                "critical_analysis",
                []
            )
        ),

        "implications": normalize_list(
            block.get(
                "implications",
                []
            )
        ),

        "takeaways": normalize_list(
            block.get(
                "takeaways",
                []
            )
        )
    }


# ============================================================
# NORMALIZE FINAL ANALYSIS
# ============================================================

def normalize_analysis(
    data
):

    if not isinstance(
        data,
        dict
    ):
        data = {}

    return {
        "en": normalize_language_block(
            data.get(
                "en",
                {}
            )
        ),

        "id": normalize_language_block(
            data.get(
                "id",
                {}
            )
        )
    }


# ============================================================
# FETCH TRANSCRIPT
# ============================================================

async def fetch_transcript(
    video_url
):

    normalized_url = normalize_youtube_url(
        video_url
    )

    if not normalized_url:

        raise ValueError(
            "Invalid YouTube URL."
        )

    try:

        async with httpx.AsyncClient(
            timeout=AI_TIMEOUT,
            follow_redirects=True
        ) as client:

            response = await client.get(
                TRANSCRIPT_API_URL,
                params={
                    "video_url":
                        normalized_url
                }
            )

    except Exception as error:

        raise RuntimeError(
            "Failed to connect to transcript service: "
            + str(error)
        )

    if response.status_code != 200:

        try:

            error_data = response.json()

            message = error_data.get(
                "message",
                (
                    "Transcript service returned HTTP "
                    + str(
                        response.status_code
                    )
                )
            )

        except Exception:

            message = (
                response.text
                or (
                    "Transcript service returned HTTP "
                    + str(
                        response.status_code
                    )
                )
            )

        raise RuntimeError(
            message
        )

    try:

        data = response.json()

    except Exception:

        raise RuntimeError(
            "Transcript service returned invalid JSON."
        )

    if not isinstance(
        data,
        dict
    ):

        raise RuntimeError(
            "Transcript service returned invalid data."
        )

    segments = data.get(
        "transcript",
        []
    )

    if not isinstance(
        segments,
        list
    ):
        segments = []

    cleaned = []

    for segment in segments:

        if not isinstance(
            segment,
            dict
        ):
            continue

        text = str(
            segment.get(
                "text",
                ""
            )
        ).strip()

        if not text:
            continue

        try:

            start = float(
                segment.get(
                    "start",
                    0
                )
            )

        except Exception:

            start = 0.0

        try:

            duration = float(
                segment.get(
                    "duration",
                    0
                )
            )

        except Exception:

            duration = 0.0

        cleaned.append(
            {
                "text":
                    text,

                "start":
                    start,

                "duration":
                    duration
            }
        )

    if not cleaned:

        raise RuntimeError(
            "Transcript is empty or unavailable for this video."
        )

    return {
        "title":
            data.get(
                "title",
                "Untitled Video"
            ),

        "language":
            data.get(
                "language",
                "unknown"
            ),

        "transcript":
            cleaned
    }


# ============================================================
# ANALYZE LARGE TRANSCRIPT
# ============================================================

async def analyze_large_transcript(
    transcript_text
):

    chunks = chunk_text(
        transcript_text
    )

    if not chunks:

        raise ValueError(
            "Transcript could not be divided into chunks."
        )

    notes = []

    for index, chunk in enumerate(
        chunks,
        start=1
    ):

        prompt = (
            CHUNK_PROMPT
            + "\n\nCHUNK "
            + str(index)
            + " OF "
            + str(len(chunks))
            + "\n\n"
            + chunk
        )

        result = await run_ai(
            SYSTEM_PROMPT,
            prompt,
            2500
        )

        notes.append(
            extract_ai_text(
                result
            )
        )

    combined_notes = "\n\n".join(
        notes
    )

    combined_notes = combined_notes[
        :MAX_FINAL_CONTEXT_CHARS
    ]

    final_prompt = """
Create the final professional report from the following
analysis notes.

Use all relevant information.

Follow the required JSON structure.

The executive summary must normally be approximately
180-300 words.

Do not invent facts.

Do not identify speakers.

Return ONLY valid JSON.

ANALYSIS NOTES:

""" + combined_notes

    final_result = await run_ai(
        SYSTEM_PROMPT,
        final_prompt,
        5000
    )

    analysis = normalize_analysis(
        parse_ai_json(
            final_result
        )
    )

    return (
        analysis,
        "chunked",
        len(chunks)
    )


# ============================================================
# ANALYZE TRANSCRIPT
# ============================================================

async def analyze_transcript(
    transcript_text
):

    if len(
        transcript_text
    ) <= MAX_SINGLE_PASS_CHARS:

        prompt = """
Create the final professional video analysis from
the following transcript.

Use ALL relevant information.

The executive summary must normally contain
approximately 180-300 words.

Follow the required JSON structure.

Do not invent facts.

Do not identify speakers.

Return ONLY valid JSON.

TRANSCRIPT:

""" + transcript_text

        result = await run_ai(
            SYSTEM_PROMPT,
            prompt,
            5000
        )

        analysis = normalize_analysis(
            parse_ai_json(
                result
            )
        )

        return (
            analysis,
            "single_pass",
            1
        )

    return await analyze_large_transcript(
        transcript_text
    )


# ============================================================
# ROOT
# ============================================================

@app.get("/")
async def root():

    return {
        "status":
            "ok",

        "service":
            "AI Video Summarizer API",

        "version":
            "7.1.0"
    }


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
async def health():

    return {
        "status":
            "ok",

        "version":
            "7.1.0"
    }


# ============================================================
# ANALYZE ENDPOINT
# ============================================================

@app.post("/analyze")
async def analyze(
    request: Request
):

    try:

        # ----------------------------------------------------
        # READ JSON
        # ----------------------------------------------------

        try:

            body = await request.json()

        except Exception:

            return error_response(
                "Invalid JSON request body.",
                "invalid_json",
                400
            )

        if not isinstance(
            body,
            dict
        ):

            return error_response(
                "Request body must be a JSON object.",
                "invalid_request",
                400
            )

        # ----------------------------------------------------
        # READ URL
        # ----------------------------------------------------

        video_url = (
            body.get(
                "video_url"
            )
            or body.get(
                "youtube_url"
            )
            or body.get(
                "url"
            )
            or ""
        )

        if not isinstance(
            video_url,
            str
        ):

            video_url = str(
                video_url
            )

        video_url = video_url.strip()

        # ----------------------------------------------------
        # VALIDATE URL
        # ----------------------------------------------------

        if not video_url:

            return error_response(
                "YouTube URL is required.",
                "validation_error",
                400
            )

        normalized_url = normalize_youtube_url(
            video_url
        )

        if not normalized_url:

            return error_response(
                "Invalid YouTube URL.",
                "validation_error",
                400
            )

        video_id = extract_video_id(
            normalized_url
        )

        if not video_id:

            return error_response(
                "Could not extract YouTube video ID.",
                "validation_error",
                400
            )

        # ----------------------------------------------------
        # GET TRANSCRIPT
        # ----------------------------------------------------

        transcript_data = await fetch_transcript(
            normalized_url
        )

        transcript_segments = (
            transcript_data[
                "transcript"
            ]
        )

        # ----------------------------------------------------
        # BUILD TRANSCRIPT TEXT
        # ----------------------------------------------------

        transcript_text = build_transcript_text(
            transcript_segments
        )

        if not transcript_text:

            return error_response(
                "Transcript is empty.",
                "transcript_error",
                422
            )

        # ----------------------------------------------------
        # HASH
        # ----------------------------------------------------

        transcript_hash = create_transcript_hash(
            transcript_text
        )

        # ----------------------------------------------------
        # AI ANALYSIS
        # ----------------------------------------------------

        (
            analysis,
            analysis_mode,
            total_chunks
        ) = await analyze_transcript(
            transcript_text
        )

        # ----------------------------------------------------
        # FINAL RESPONSE
        # ----------------------------------------------------

        return {
            "status":
                "success",

            "video": {
                "id":
                    video_id,

                "url":
                    normalized_url
            },

            "transcript": {
                "title":
                    transcript_data[
                        "title"
                    ],

                "language":
                    transcript_data[
                        "language"
                    ],

                "transcript":
                    transcript_segments
            },

            "ai":
                analysis,

            "processing": {
                "mode":
                    analysis_mode,

                "total_segments":
                    len(
                        transcript_segments
                    ),

                "total_chunks":
                    total_chunks,

                "transcript_characters":
                    len(
                        transcript_text
                    ),

                "transcript_hash":
                    transcript_hash
            }
        }

    except ValueError as error:

        return error_response(
            str(error),
            "validation_error",
            400
        )

    except RuntimeError as error:

        return error_response(
            str(error),
            "processing_error",
            502
        )

    except Exception as error:

        return error_response(
            "Unexpected server error: "
            + str(error),
            "server_error",
            500
        )


# ============================================================
# CLOUDFLARE ASGI
# ============================================================

Default = asgi.entrypoint(app)
