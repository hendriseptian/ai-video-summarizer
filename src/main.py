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
    version="6.0.0"
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
            "V6 is running on Cloudflare"
        ),
        "version": "6.0.0"
    }


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
async def health():

    return {
        "status": "healthy",
        "version": "6.0.0",
        "model": AI_MODEL
    }


# ============================================================
# HTTP ERROR HANDLER
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
    # JSON embedded inside text
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
        # Standard JSON
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
# CONVERT ANALYSIS OBJECT TO PROFESSIONAL TEXT
# ============================================================

def convert_analysis_object(
    item
):

    if not isinstance(
        item,
        dict
    ):

        return clean_text(
            item
        )

    # ========================================================
    # POSSIBLE AI FIELD NAMES
    # ========================================================

    issue = clean_text(
        item.get(
            "issue",
            ""
        )
    )

    reason = clean_text(
        item.get(
            "reason",
            ""
        )
    )

    analysis = clean_text(
        item.get(
            "analysis",
            ""
        )
    )

    observation = clean_text(
        item.get(
            "observation",
            ""
        )
    )

    significance = clean_text(
        item.get(
            "significance",
            ""
        )
    )

    implication = clean_text(
        item.get(
            "implication",
            ""
        )
    )

    evidence = clean_text(
        item.get(
            "evidence",
            ""
        )
    )

    # ========================================================
    # BEST CASE:
    # ANALYSIS ALREADY PROVIDED
    # ========================================================

    if analysis:

        return analysis


    # ========================================================
    # OBSERVATION + SIGNIFICANCE
    # ========================================================

    if observation:

        if significance:

            return (
                observation
                + " "
                + significance
            )

        if reason:

            return (
                observation
                + " "
                + reason
            )

        if implication:

            return (
                observation
                + " "
                + implication
            )

        return observation


    # ========================================================
    # ISSUE + REASON
    #
    # Convert raw AI structure into professional prose.
    # ========================================================

    if issue:

        sentence = issue

        if reason:

            sentence = (
                sentence
                + " "
                + reason
            )

        elif significance:

            sentence = (
                sentence
                + " "
                + significance
            )

        elif implication:

            sentence = (
                sentence
                + " "
                + implication
            )

        elif evidence:

            sentence = (
                sentence
                + " "
                + evidence
            )

        return sentence


    # ========================================================
    # GENERIC DICTIONARY FALLBACK
    # ========================================================

    values = []

    for value in item.values():

        text = clean_text(
            value
        )

        if text:

            values.append(
                text
            )

    if values:

        return " ".join(
            values
        )

    return ""


# ============================================================
# NORMALIZE LIST
# ============================================================

def normalize_list(
    value,
    maximum,
    convert_objects=True
):

    if not isinstance(
        value,
        list
    ):

        return []

    result = []

    for item in value:

        # ----------------------------------------------------
        # STRING
        # ----------------------------------------------------

        if isinstance(
            item,
            str
        ):

            text = clean_text(
                item
            )

            if text:

                result.append(
                    text
                )

            continue

        # ----------------------------------------------------
        # DICTIONARY
        # ----------------------------------------------------

        if (
            isinstance(
                item,
                dict
            )
            and
            convert_objects
        ):

            text = convert_analysis_object(
                item
            )

            if text:

                result.append(
                    text
                )

            continue

    return result[:maximum]


# ============================================================
# NORMALIZE CRITICAL ANALYSIS
# ============================================================

def normalize_critical_analysis(
    value
):

    if not isinstance(
        value,
        list
    ):

        return []

    result = []

    for item in value:

        # ----------------------------------------------------
        # STRING
        # ----------------------------------------------------

        if isinstance(
            item,
            str
        ):

            text = clean_text(
                item
            )

            if text:

                result.append(
                    text
                )

            continue

        # ----------------------------------------------------
        # OBJECT
        # ----------------------------------------------------

        if isinstance(
            item,
            dict
        ):

            text = convert_analysis_object(
                item
            )

            if text:

                result.append(
                    text
                )

    return result[:5]


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

    # ========================================================
    # SUMMARY
    # ========================================================

    summary = clean_text(
        data.get(
            "summary",
            ""
        )
    )

    # ========================================================
    # KEY POINTS
    # ========================================================

    key_points = normalize_list(
        data.get(
            "key_points",
            []
        ),
        5
    )

    # ========================================================
    # CRITICAL ANALYSIS
    # ========================================================

    critical_analysis = (
        normalize_critical_analysis(
            data.get(
                "critical_analysis",
                []
            )
        )
    )

    # ========================================================
    # IMPLICATIONS
    # ========================================================

    implications = normalize_list(
        data.get(
            "implications",
            []
        ),
        4
    )

    # ========================================================
    # TAKEAWAYS
    # ========================================================

    takeaways = normalize_list(
        data.get(
            "takeaways",
            []
        ),
        3
    )

    # ========================================================
    # RETURN
    # ========================================================

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
# BUILD TRANSCRIPT CHUNKS
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
    # FreeTranscriptAPI uses GET.
    #
    # Query:
    # ?video_url=<youtube-url>
    # ========================================================

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

    # ========================================================
    # PARSE RESPONSE
    # ========================================================

    try:

        data = response.json()

    except Exception:

        data = {}

    # ========================================================
    # API ERROR
    # ========================================================

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

    # ========================================================
    # NORMALIZE TRANSCRIPT
    # ========================================================

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
You are a senior professional content analyst.

Your output will be used in a professional office environment,
including management review, media monitoring, research,
briefing, reporting and decision support.

Analyze the provided YouTube transcript rigorously.

============================================================
1. SOURCE DISCIPLINE
============================================================

Use ONLY the provided transcript.

Do NOT use outside knowledge.

Do NOT search for additional information.

Do NOT invent facts.

Do NOT assume facts that are not supported.

Do NOT identify speakers.

Do NOT guess speaker identities.

Do NOT attribute statements to specific people.

Do NOT create quotations.

Do NOT add information that is not contained
or reasonably supported by the transcript.

============================================================
2. ANALYTICAL OBJECTIVE
============================================================

The purpose is NOT merely to summarize.

The purpose is to produce a professional assessment
of the substantive content.

Determine:

- the central subject
- the main message
- major themes
- important claims
- supporting evidence
- factual statements
- opinions
- assumptions
- interpretations
- conclusions
- limitations
- inconsistencies
- missing context
- potential implications

Prioritize substance over surface-level description.

============================================================
3. EXECUTIVE SUMMARY
============================================================

Write an executive-level summary.

The summary should answer:

- What is the content fundamentally about?
- What is the central message?
- What are the most important themes?
- What conclusions are reasonably supported?

Do NOT simply list topics.

Do NOT begin with phrases such as:

"The transcript discusses..."

"The video talks about..."

"The speaker explains..."

Instead, directly describe the substantive content.

The summary should be approximately
120 to 150 words.

============================================================
4. KEY POINTS
============================================================

Provide exactly 5 key points.

Each point must represent an important substantive
element of the content.

Avoid:

- trivial details
- repeated information
- generic observations
- statements that merely repeat the summary

Each point should be concise but informative.

============================================================
5. CRITICAL ANALYSIS
============================================================

Critical analysis is the most important analytical section.

Evaluate the quality and strength of the content.

Consider:

- evidence quality
- unsupported claims
- logical gaps
- assumptions
- contradictions
- overgeneralization
- causal claims
- missing context
- selective framing
- ambiguity
- conclusions stronger than available evidence
- consistency between claims and supporting information

IMPORTANT:

Do NOT criticize simply because information is missing.

Do NOT manufacture weaknesses.

If the content is reasonably supported,
acknowledge that.

If a limitation exists, explain its significance.

Critical analysis should naturally contain:

1. analytical observation
2. why the observation matters

But DO NOT label them.

============================================================
6. CRITICAL ANALYSIS WRITING STYLE
============================================================

CRITICAL_ANALYSIS MUST BE STRINGS ONLY.

NEVER return objects.

BAD:

{
  "issue": "The criteria are unclear.",
  "reason": "The discussion does not explain them."
}

BAD:

"Issue: unclear criteria."

BAD:

"Reason: insufficient information."

BAD:

"The transcript does not provide information about..."

GOOD:

"The criteria used to select participants and judges are not
explained in sufficient detail, limiting the ability to assess
whether the stated professional qualifications were applied
consistently."

GOOD:

"Information regarding the winners' rewards is not sufficiently
detailed, limiting assessment of the competitive incentives
associated with the event."

GOOD:

"The event is presented as having institutional significance,
but the discussion provides limited concrete evidence regarding
its broader impact on the community."

Do NOT repeatedly use the phrase:

"The transcript does not provide..."

Instead, express the analytical consequence.

============================================================
7. CRITICAL ANALYSIS TONE
============================================================

Use professional analytical language.

Avoid:

- emotional language
- sensational language
- insulting language
- casual language
- excessive criticism
- unsupported judgments

The objective is:

SHARP BUT FAIR.

============================================================
8. IMPLICATIONS
============================================================

Provide up to 4 meaningful implications.

Implications may include:

- practical consequences
- risks
- opportunities
- decision considerations
- broader significance
- limitations
- lessons

Only provide implications supported by the content.

Do not invent consequences.

============================================================
9. TAKEAWAYS
============================================================

Provide exactly 3 concise takeaways.

These should represent the most important conclusions
that a professional reader should remember.

============================================================
10. LANGUAGE
============================================================

Produce BOTH:

English

and

Indonesian.

The Indonesian version must preserve the meaning
of the English version.

Do NOT add facts during translation.

============================================================
11. OUTPUT
============================================================

Return ONLY valid JSON.

Do NOT use Markdown.

Do NOT use code fences.

Do NOT add commentary before or after the JSON.

The exact structure is:

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
12. STRICT DATA TYPES
============================================================

summary:
STRING

key_points:
ARRAY OF STRINGS

critical_analysis:
ARRAY OF STRINGS

implications:
ARRAY OF STRINGS

takeaways:
ARRAY OF STRINGS

NEVER return:

critical_analysis:
[
  {
    "issue": "...",
    "reason": "..."
  }
]

ALWAYS return:

critical_analysis:
[
  "Professional analytical statement...",
  "Professional analytical statement...",
  "Professional analytical statement..."
]
"""


# ============================================================
# BUILD AI PROMPT
# ============================================================

def build_ai_prompt(
    transcript_text,
    title=""
):

    return f"""
Analyze the following YouTube video.

============================================================
VIDEO TITLE
============================================================

{title}

============================================================
SOURCE TRANSCRIPT
============================================================

{transcript_text}

============================================================
FINAL REQUIREMENTS
============================================================

Produce a professional office-quality analysis.

The analysis must be based ONLY on the source transcript.

Do not identify speakers.

Do not use outside knowledge.

Do not invent information.

Do not merely repeat the transcript.

Prioritize:

- central message
- substantive points
- claims
- evidence
- analytical limitations
- logical consistency
- context
- implications

For Critical Analysis:

Write professional analytical prose.

NEVER return:

{{
    "issue": "...",
    "reason": "..."
}}

Instead return one professional analytical sentence
or paragraph per item.

Do not use the labels:

Issue
Reason
Evidence
Transcript
Observation

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

                # =================================================
                # JSON MODE
                # =================================================

                "response_format": {
                    "type":
                        "json_object"
                },

                # =================================================
                # DETERMINISTIC
                # =================================================

                "temperature":
                    0.0,

                "seed":
                    42,

                # =================================================
                # OUTPUT SPACE
                # =================================================

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
    # STANDARD WORKERS AI RESPONSE
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

    # ========================================================
    # UNKNOWN RESPONSE
    # ========================================================

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

    # ========================================================
    # PARSE
    # ========================================================

    try:

        parsed = parse_ai_json(
            raw
        )

    except Exception as exc:

        preview = clean_text(
            raw
        )

        if len(preview) > 6000:

            preview = (
                preview[:6000]
                + "..."
            )

        raise RuntimeError(
            "AI returned invalid JSON. "
            f"Raw response: {preview}. "
            f"Parser error: {str(exc)}"
        )

    # ========================================================
    # ENGLISH
    # ========================================================

    en_data = normalize_analysis(
        parsed.get(
            "en",
            {}
        )
    )

    # ========================================================
    # INDONESIAN
    # ========================================================

    id_data = normalize_analysis(
        parsed.get(
            "id",
            {}
        )
    )

    # ========================================================
    # RETURN
    # ========================================================

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
You are a professional content analyst.

Analyze ONLY the provided transcript segment.

Do not identify speakers.

Do not guess identities.

Do not use outside knowledge.

Do not invent facts.

Extract substantive information.

Evaluate:

- important claims
- arguments
- evidence
- assumptions
- logical weaknesses
- contradictions
- missing context
- implications

Return ONLY valid JSON.

Do not use Markdown.

Do not use code fences.

Structure:

{
  "summary": "",
  "key_points": [],
  "critical_analysis": [],
  "implications": [],
  "takeaways": []
}

IMPORTANT:

critical_analysis MUST contain strings.

NEVER return objects such as:

{
  "issue": "...",
  "reason": "..."
}

Write concise professional analytical prose.
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

============================================================
TRANSCRIPT SEGMENT
============================================================

{chunk}

============================================================
INSTRUCTION
============================================================

Return ONLY valid JSON.

Critical analysis must be professional prose
and strings only.
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

The final analysis must represent the entire video.

Do not over-focus on a single segment.

Do not identify speakers.

Do not invent facts.

Remove duplicated points.

Prioritize substantive information.

Distinguish:

- facts
- claims
- opinions
- assumptions
- interpretations

Critical analysis must evaluate:

- evidence
- logical consistency
- unsupported claims
- missing context
- assumptions
- contradictions
- overgeneralization
- significance

Do not manufacture criticism.

Critical analysis MUST contain strings only.

NEVER return objects.

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
- approximately 120 to 150 words

key_points:
- exactly 5

critical_analysis:
- exactly 3

implications:
- up to 4

takeaways:
- exactly 3

Do not use labels such as:

Issue
Reason
Evidence
Transcript
Observation

Critical analysis must be written as natural
professional analytical prose.
"""

    user_prompt = f"""
============================================================
VIDEO TITLE
============================================================

{title}

============================================================
SEGMENT ANALYSES
============================================================

{material}

============================================================
FINAL TASK
============================================================

Create one integrated professional analysis
of the entire video.

Do not simply concatenate the segment analyses.

Synthesize them.

Prioritize the most important themes and conclusions.

Return ONLY valid JSON.
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

        if len(preview) > 6000:

            preview = (
                preview[:6000]
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
        # TRANSCRIPT
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
        # TRANSCRIPT HASH
        # ====================================================

        transcript_hash = (
            create_transcript_hash(
                transcript
            )
        )

        # ====================================================
        # LANGUAGE
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
        # LENGTH
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
        # IMPORTANT FRONTEND COMPATIBILITY
        #
        # script.js expects:
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
                "6.0.0",

            # =================================================
            # VIDEO
            # =================================================

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
