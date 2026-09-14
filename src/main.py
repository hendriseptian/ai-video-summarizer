from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from workers import asgi, env
import httpx2 as httpx

import json
import re
import hashlib
import ast


# ============================================================
# APPLICATION
# ============================================================

app = FastAPI(
    title="AI Video Summarizer API",
    version="7.0.0"
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

MAX_SINGLE_PASS_CHARS = 100000

CHUNK_SIZE = 18000

MAX_FINAL_CONTEXT_CHARS = 90000

AI_TIMEOUT = 120.0

AI_TEMPERATURE = 0.0

AI_SEED = 42

AI_MAX_TOKENS = 5000


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/")
async def root():
    return {
        "status": "ok",
        "service": "AI Video Summarizer API",
        "version": "7.0.0"
    }


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "version": "7.0.0"
    }


# ============================================================
# ERROR RESPONSE
# ============================================================

def error_response(
    message,
    error_type="server_error",
    http_status=500
):
    return {
        "status": "error",
        "message": message,
        "error": message,
        "error_type": error_type,
        "http_status": http_status
    }


# ============================================================
# YOUTUBE URL NORMALIZATION
# ============================================================

def normalize_youtube_url(url: str) -> str:

    if not isinstance(url, str):
        return ""

    url = url.strip()

    if not url:
        return ""

    # Remove whitespace
    url = re.sub(r"\s+", "", url)

    # youtube.com/watch?v=...
    match = re.search(
        r"(?:youtube\.com/watch\?[^#]*v=)([A-Za-z0-9_-]{11})",
        url,
        re.IGNORECASE
    )

    if match:
        video_id = match.group(1)

        return (
            "https://www.youtube.com/watch?v="
            + video_id
        )

    # youtu.be/...
    match = re.search(
        r"(?:youtu\.be/)([A-Za-z0-9_-]{11})",
        url,
        re.IGNORECASE
    )

    if match:
        video_id = match.group(1)

        return (
            "https://www.youtube.com/watch?v="
            + video_id
        )

    # youtube.com/shorts/...
    match = re.search(
        r"(?:youtube\.com/shorts/)([A-Za-z0-9_-]{11})",
        url,
        re.IGNORECASE
    )

    if match:
        video_id = match.group(1)

        return (
            "https://www.youtube.com/watch?v="
            + video_id
        )

    return ""


# ============================================================
# EXTRACT VIDEO ID
# ============================================================

def extract_video_id(url: str) -> str:

    normalized = normalize_youtube_url(url)

    if not normalized:
        return ""

    match = re.search(
        r"[?&]v=([A-Za-z0-9_-]{11})",
        normalized
    )

    if match:
        return match.group(1)

    return ""


# ============================================================
# TRANSCRIPT TEXT BUILDER
# ============================================================

def build_transcript_text(
    transcript_segments
):

    if not isinstance(
        transcript_segments,
        list
    ):
        return ""

    lines = []

    for index, segment in enumerate(
        transcript_segments,
        start=1
    ):

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

        try:
            start_float = float(start)
        except Exception:
            start_float = 0.0

        timestamp = format_timestamp(
            start_float
        )

        lines.append(
            f"[{timestamp}] {text}"
        )

    return "\n".join(lines)


# ============================================================
# TIMESTAMP
# ============================================================

def format_timestamp(
    seconds
):

    try:
        seconds = float(seconds)
    except Exception:
        seconds = 0.0

    if seconds < 0:
        seconds = 0.0

    total_seconds = int(
        seconds
    )

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
# HASH
# ============================================================

def create_transcript_hash(
    transcript_text
):

    return hashlib.sha256(
        transcript_text.encode(
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

    text_length = len(text)

    while start < text_length:

        end = min(
            start + chunk_size,
            text_length
        )

        # Try to end at a paragraph/newline
        if end < text_length:

            newline_position = text.rfind(
                "\n",
                start,
                end
            )

            if (
                newline_position >
                start + int(chunk_size * 0.65)
            ):
                end = newline_position

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
# AI SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """
You are a professional video content analyst.

Your task is to analyze a YouTube transcript and produce a
professional report in BOTH English and Indonesian.

You must work ONLY from information contained in the transcript.

Do not invent facts.

Do not assume facts that are not stated.

Do not identify speakers.

Do not add external knowledge.

The output MUST be valid JSON.

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

The summary must explain the overall content of the video
rather than only stating its main topic.

When supported by the transcript, naturally cover:

1. The main context or subject discussed.
2. The most important events, facts, statements,
   or developments.
3. Relevant responses, reactions, actions, or perspectives.
4. Important consequences, impacts, concerns, or issues.
5. The overall significance or conclusion.

Write the summary as coherent professional prose
in 1-3 paragraphs.

Do NOT use bullet points.

Do NOT create headings inside the summary.

Do NOT simply repeat the transcript sentence by sentence.

Do NOT make the summary unnecessarily vague or generic.

Do NOT omit important information merely to keep the
summary short.

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

Each point should contain enough context to explain
why the information is important.

Each point should normally be 1-3 sentences.

Use only information supported by the transcript.

Do not repeat the same information across multiple points.

============================================================
CRITICAL ANALYSIS
============================================================

Provide 4-6 meaningful analytical observations.

Each observation should explain the significance,
weakness, inconsistency, missing information,
limitation, or important consideration found in
the content.

Write each observation as natural professional prose.

Do NOT use labels such as:

Issue:
Reason:
Evidence:
Observation:
Transcript:

Do NOT return dictionary/object structures for
individual analysis items.

Each item must be a normal string.

Do not invent facts.

============================================================
IMPLICATIONS
============================================================

Provide 3-5 implications that can reasonably be derived
from the transcript.

Explain why the information matters and what potential
consequences or considerations arise.

Do not invent information.

============================================================
KEY TAKEAWAYS
============================================================

Provide 3-5 concise but meaningful takeaways.

Each takeaway should capture an important conclusion
from the video.

Do not simply copy the key points.

Do not invent facts.

============================================================
LANGUAGE
============================================================

English must be professional and natural.

Indonesian must be professional, natural, and suitable
for an office or analytical report.

Do not translate word-for-word if that makes the
language unnatural.

============================================================
OUTPUT
============================================================

Return ONLY valid JSON.

No markdown.

No ```json.

No explanation before or after the JSON.
"""


# ============================================================
# CHUNK ANALYSIS PROMPT
# ============================================================

CHUNK_PROMPT = """
Analyze the following transcript section.

Extract the factual information needed for a later
professional report.

Do NOT invent information.

Do NOT identify speakers.

Return concise structured notes containing:

- major facts
- important events
- important statements
- reactions or responses
- concerns or issues
- impacts or implications
- important context

Focus on information that may be important in the
final comprehensive analysis.

TRANSCRIPT SECTION:

"""


# ============================================================
# FINAL SYNTHESIS PROMPT
# ============================================================

FINAL_SYNTHESIS_PROMPT = """
Create the final professional video analysis from the
transcript information provided below.

The material may contain multiple transcript sections.

Use ALL relevant information.

Do not invent facts.

Do not identify speakers.

Do not omit important information simply to make the
summary short.

Follow the required JSON structure and all requirements
from the system prompt.

The final executive summary should normally be
approximately 180-300 words.

SOURCE MATERIAL:

"""


# ============================================================
# AI CALL
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

        "temperature":
            AI_TEMPERATURE,

        "seed":
            AI_SEED,

        "max_tokens":
            max_tokens
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

        try:

            return json.dumps(
                result,
                ensure_ascii=False
            )

        except Exception:
            return str(result)

    return str(result)


# ============================================================
# CLEAN AI JSON
# ============================================================

def clean_ai_json_text(
    text
):

    if not text:
        return ""

    text = text.strip()

    # Remove markdown fences
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

    # Locate JSON object
    first = text.find("{")

    last = text.rfind("}")

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

    text =
        extract_ai_text(
            result
        )

    text =
        clean_ai_json_text(
            text
        )

    if not text:
        raise ValueError(
            "AI returned an empty response."
        )

    # Normal JSON
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

    # Python dictionary fallback
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

        return " ".join(
            normalize_text(
                item
            )
            for item in value
            if normalize_text(
                item
            )
        ).strip()

    if isinstance(
        value,
        dict
    ):

        parts = []

        for key in [
            "issue",
            "reason",
            "evidence",
            "observation",
            "analysis",
            "text",
            "content"
        ]:

            if key in value:

                item =
                    normalize_text(
                        value[key]
                    )

                if item:
                    parts.append(
                        item
                    )

        if parts:
            return " ".join(
                parts
            )

        return " ".join(
            normalize_text(
                item
            )
            for item in value.values()
        ).strip()

    return str(value).strip()


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
        str
    ):

        text =
            value.strip()

        if not text:
            return []

        return [
            text
        ]

    if not isinstance(
        value,
        list
    ):

        text =
            normalize_text(
                value
            )

        return (
            [text]
            if text
            else []
        )

    output = []

    for item in value:

        text =
            normalize_text(
                item
            )

        if text:
            output.append(
                text
            )

    return output


# ============================================================
# CONVERT ANALYSIS OBJECT
# ============================================================

def convert_analysis_object(
    value
):

    if isinstance(
        value,
        dict
    ):

        return normalize_text(
            value
        )

    return normalize_text(
        value
    )


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

    summary =
        convert_analysis_object(
            block.get(
                "summary",
                ""
            )
        )

    key_points =
        normalize_list(
            block.get(
                "key_points",
                []
            )
        )

    critical_analysis =
        normalize_list(
            block.get(
                "critical_analysis",
                []
            )
        )

    implications =
        normalize_list(
            block.get(
                "implications",
                []
            )
        )

    takeaways =
        normalize_list(
            block.get(
                "takeaways",
                []
            )
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
# NORMALIZE FINAL ANALYSIS
# ============================================================

def normalize_final_analysis(
    parsed
):

    if not isinstance(
        parsed,
        dict
    ):
        parsed = {}

    english =
        parsed.get(
            "en",
            {}
        )

    indonesian =
        parsed.get(
            "id",
            {}
        )

    result = {
        "en":
            normalize_language_block(
                english
            ),

        "id":
            normalize_language_block(
                indonesian
            )
    }

    # If only one language is returned,
    # copy it as fallback to the other language.
    if not result["en"]["summary"]:

        if result["id"]["summary"]:

            result["en"]["summary"] =
                result["id"]["summary"]

    if not result["id"]["summary"]:

        if result["en"]["summary"]:

            result["id"]["summary"] =
                result["en"]["summary"]

    return result


# ============================================================
# FETCH TRANSCRIPT
# ============================================================

async def fetch_transcript(
    video_url
):

    normalized_url =
        normalize_youtube_url(
            video_url
        )

    if not normalized_url:

        raise ValueError(
            "Invalid YouTube URL."
        )

    params = {
        "video_url":
            normalized_url
    }

    try:

        async with httpx.AsyncClient(
            timeout=AI_TIMEOUT,
            follow_redirects=True
        ) as client:

            response =
                await client.get(
                    TRANSCRIPT_API_URL,
                    params=params
                )

    except Exception as error:

        raise RuntimeError(
            "Failed to connect to transcript service: "
            + str(error)
        )

    if response.status_code != 200:

        try:
            error_data =
                response.json()

            message =
                error_data.get(
                    "message",
                    "Transcript service returned an error."
                )

        except Exception:

            message =
                response.text or (
                    "Transcript service returned HTTP "
                    + str(response.status_code)
                )

        raise RuntimeError(
            message
        )

    try:

        data =
            response.json()

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

    transcript =
        data.get(
            "transcript",
            []
        )

    if not isinstance(
        transcript,
        list
    ):

        transcript = []

    cleaned_transcript = []

    for segment in transcript:

        if not isinstance(
            segment,
            dict
        ):
            continue

        text =
            str(
                segment.get(
                    "text",
                    ""
                )
            ).strip()

        if not text:
            continue

        start =
            segment.get(
                "start",
                0
            )

        duration =
            segment.get(
                "duration",
                0
            )

        try:
            start =
                float(start)
        except Exception:
            start = 0.0

        try:
            duration =
                float(duration)
        except Exception:
            duration = 0.0

        cleaned_transcript.append(
            {
                "text":
                    text,

                "start":
                    start,

                "duration":
                    duration
            }
        )

    if not cleaned_transcript:

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
            cleaned_transcript
    }


# ============================================================
# CHUNK ANALYSIS
# ============================================================

async def analyze_chunks(
    chunks
):

    chunk_notes = []

    for index, chunk in enumerate(
        chunks,
        start=1
    ):

        prompt =
            CHUNK_PROMPT + (
                "\n\nCHUNK "
                + str(index)
                + " OF "
                + str(len(chunks))
                + "\n\n"
                + chunk
            )

        result =
            await run_ai(
                SYSTEM_PROMPT,
                prompt,
                max_tokens=2500
            )

        text =
            extract_ai_text(
                result
            )

        chunk_notes.append(
            "CHUNK "
            + str(index)
            + "\n"
            + text
        )

    return "\n\n".join(
        chunk_notes
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

        prompt =
            FINAL_SYNTHESIS_PROMPT + (
                transcript_text
            )

        result =
            await run_ai(
                SYSTEM_PROMPT,
                prompt,
                max_tokens=AI_MAX_TOKENS
            )

        parsed =
            parse_ai_json(
                result
            )

        return (
            normalize_final_analysis(
                parsed
            ),
            "single_pass",
            1
        )

    # Large transcript
    chunks =
        chunk_text(
            transcript_text
        )

    if not chunks:

        raise ValueError(
            "Transcript could not be divided into chunks."
        )

    chunk_notes =
        await analyze_chunks(
            chunks
        )

    # Limit final context if necessary
    if len(
        chunk_notes
    ) > MAX_FINAL_CONTEXT_CHARS:

        chunk_notes =
            chunk_notes[
                :MAX_FINAL_CONTEXT_CHARS
            ]

    final_prompt =
        FINAL_SYNTHESIS_PROMPT + (
            chunk_notes
        )

    result =
        await run_ai(
            SYSTEM_PROMPT,
            final_prompt,
            max_tokens=AI_MAX_TOKENS
        )

    parsed =
        parse_ai_json(
            result
        )

    return (
        normalize_final_analysis(
            parsed
        ),
        "chunked",
        len(chunks)
    )


# ============================================================
# ANALYZE ENDPOINT
# ============================================================

@app.post("/analyze")
async def analyze(
    request: Request
):

    try:

        # ----------------------------------------------------
        # READ REQUEST BODY
        # ----------------------------------------------------

        try:

            body =
                await request.json()

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
        # ACCEPT MULTIPLE FIELD NAMES
        # ----------------------------------------------------

        video_url = (
            body.get("video_url")
            or body.get("youtube_url")
            or body.get("url")
            or ""
        )

        if not isinstance(
            video_url,
            str
        ):

            video_url = str(
                video_url
            )

        video_url =
            video_url.strip()

        # ----------------------------------------------------
        # VALIDATE
        # ----------------------------------------------------

        if not video_url:

            return error_response(
                "YouTube URL is required.",
                "validation_error",
                400
            )

        normalized_url =
            normalize_youtube_url(
                video_url
            )

        if not normalized_url:

            return error_response(
                "Invalid YouTube URL.",
                "validation_error",
                400
            )

        video_id =
            extract_video_id(
                normalized_url
            )

        if not video_id:

            return error_response(
                "Could not extract YouTube video ID.",
                "validation_error",
                400
            )

        # ----------------------------------------------------
        # FETCH TRANSCRIPT
        # ----------------------------------------------------

        transcript_data =
            await fetch_transcript(
                normalized_url
            )

        transcript_segments =
            transcript_data[
                "transcript"
            ]

        # ----------------------------------------------------
        # BUILD TRANSCRIPT
        # ----------------------------------------------------

        transcript_text =
            build_transcript_text(
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

        transcript_hash =
            create_transcript_hash(
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
        # RESPONSE
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

application = asgi(app)
