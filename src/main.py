import json
import hashlib
import re
from typing import Any

import httpx2 as httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from workers import asgi, env


# ============================================================
# CONFIGURATION
# ============================================================

app = FastAPI(
    title="AI Video Summarizer API",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


TRANSCRIPT_API_URL = (
    "https://api.freetranscriptapi.com/v1/transcript"
)

YOUTUBE_OEMBED_URL = (
    "https://www.youtube.com/oembed"
)

# Transcript normal akan dianalisis dengan 1 AI call.
# Transcript sangat panjang akan otomatis memakai chunking.
MAX_SINGLE_PASS_CHARS = 60000

# Untuk transcript panjang.
CHUNK_SIZE = 18000


# ============================================================
# UTILITY
# ============================================================

def clean_text(value: Any) -> str:
    if value is None:
        return ""

    return str(value).strip()


def extract_video_id(url: str) -> str | None:
    """
    Extract YouTube video ID from several common URL formats.
    """

    url = clean_text(url)

    patterns = [
        r"(?:youtube\.com/watch\?v=)([A-Za-z0-9_-]{11})",
        r"(?:youtu\.be/)([A-Za-z0-9_-]{11})",
        r"(?:youtube\.com/embed/)([A-Za-z0-9_-]{11})",
        r"(?:youtube\.com/shorts/)([A-Za-z0-9_-]{11})",
    ]

    for pattern in patterns:
        match = re.search(pattern, url)

        if match:
            return match.group(1)

    return None


def normalize_youtube_url(url: str) -> str:
    """
    Normalize YouTube URL so query parameters such as
    ?t=3 do not create a different video reference.
    """

    video_id = extract_video_id(url)

    if video_id:
        return f"https://www.youtube.com/watch?v={video_id}"

    return url.strip()


def transcript_hash(transcript: list[dict]) -> str:
    """
    Create deterministic hash from transcript.
    Useful later for persistent cache.
    """

    raw = json.dumps(
        transcript,
        ensure_ascii=False,
        sort_keys=True
    )

    return hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()


def parse_json_response(text: str) -> dict:
    """
    Safely parse JSON returned by AI.

    Handles cases where the model accidentally returns
    markdown code fences.
    """

    text = clean_text(text)

    if not text:
        raise ValueError("AI returned empty response")

    # Remove markdown fences.
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

    text = text.strip()

    # Direct JSON.
    try:
        result = json.loads(text)

        if isinstance(result, dict):
            return result

    except Exception:
        pass

    # Try extracting the first JSON object.
    start = text.find("{")
    end = text.rfind("}")

    if start >= 0 and end > start:
        candidate = text[start:end + 1]

        try:
            result = json.loads(candidate)

            if isinstance(result, dict):
                return result

        except Exception:
            pass

    raise ValueError(
        "AI response is not valid JSON"
    )


# ============================================================
# TRANSCRIPT
# ============================================================

def normalize_transcript(data: Any) -> list[dict]:
    """
    Normalize FreeTranscriptAPI transcript format.

    Output:
    [
        {
            "start": 0.0,
            "duration": 2.1,
            "text": "..."
        }
    ]
    """

    if isinstance(data, dict):
        raw_transcript = data.get("transcript", [])

    elif isinstance(data, list):
        raw_transcript = data

    else:
        raw_transcript = []

    result = []

    for item in raw_transcript:

        if not isinstance(item, dict):
            continue

        text = clean_text(
            item.get("text", "")
        )

        if not text:
            continue

        try:
            start = float(
                item.get("start", 0)
            )
        except Exception:
            start = 0.0

        try:
            duration = float(
                item.get("duration", 0)
            )
        except Exception:
            duration = 0.0

        result.append(
            {
                "start": start,
                "duration": duration,
                "text": text
            }
        )

    return result


def transcript_to_text(
    transcript: list[dict]
) -> str:

    lines = []

    for item in transcript:

        start = item.get("start", 0)

        text = clean_text(
            item.get("text", "")
        )

        if not text:
            continue

        lines.append(
            f"[{start:.2f}s] {text}"
        )

    return "\n".join(lines)


def chunk_transcript(
    transcript: list[dict],
    max_chars: int = CHUNK_SIZE
) -> list[str]:

    chunks = []

    current_lines = []
    current_length = 0

    for item in transcript:

        start = item.get("start", 0)

        text = clean_text(
            item.get("text", "")
        )

        if not text:
            continue

        line = f"[{start:.2f}s] {text}"

        line_length = len(line)

        if (
            current_lines
            and current_length + line_length > max_chars
        ):
            chunks.append(
                "\n".join(current_lines)
            )

            current_lines = []
            current_length = 0

        current_lines.append(line)
        current_length += line_length

    if current_lines:
        chunks.append(
            "\n".join(current_lines)
        )

    return chunks


# ============================================================
# YOUTUBE METADATA
# ============================================================

async def get_youtube_metadata(
    url: str
) -> dict:

    normalized_url = normalize_youtube_url(url)

    params = {
        "url": normalized_url,
        "format": "json"
    }

    try:

        async with httpx.AsyncClient(
            timeout=20
        ) as client:

            response = await client.get(
                YOUTUBE_OEMBED_URL,
                params=params
            )

            response.raise_for_status()

            data = response.json()

            return {
                "title": clean_text(
                    data.get("title", "")
                ),
                "author_name": clean_text(
                    data.get("author_name", "")
                ),
                "author_url": clean_text(
                    data.get("author_url", "")
                ),
                "thumbnail_url": clean_text(
                    data.get("thumbnail_url", "")
                ),
                "video_id": extract_video_id(
                    normalized_url
                ),
                "url": normalized_url
            }

    except Exception:

        return {
            "title": "",
            "author_name": "",
            "author_url": "",
            "thumbnail_url": "",
            "video_id": extract_video_id(
                normalized_url
            ),
            "url": normalized_url
        }


# ============================================================
# FREE TRANSCRIPT API
# ============================================================

async def get_transcript(
    url: str
) -> tuple[list[dict], dict]:

    payload = {
        "url": normalize_youtube_url(url)
    }

    try:

        async with httpx.AsyncClient(
            timeout=60
        ) as client:

            response = await client.post(
                TRANSCRIPT_API_URL,
                json=payload
            )

            response.raise_for_status()

            data = response.json()

    except Exception as exc:

        raise HTTPException(
            status_code=502,
            detail=(
                "Failed to retrieve transcript: "
                f"{str(exc)}"
            )
        )

    transcript = normalize_transcript(data)

    if not transcript:

        raise HTTPException(
            status_code=404,
            detail="Transcript not found for this video."
        )

    return transcript, data


# ============================================================
# AI
# ============================================================

async def call_ai(
    system_prompt: str,
    user_prompt: str
) -> str:

    try:

        response = await env.AI.run(
            "@cf/meta/llama-3.1-8b-instruct-fast",
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

                # Stabil / lebih konsisten
                "temperature": 0.0,

                # Seed tetap untuk membantu hasil konsisten
                "seed": 42,

                # Batasi output supaya tidak terlalu panjang
                "max_tokens": 2048
            }
        )

    except Exception as exc:

        raise HTTPException(
            status_code=502,
            detail=(
                "Cloudflare AI request failed: "
                f"{type(exc).__name__}: {str(exc)}"
            )
        )

    if isinstance(response, dict):

        if "response" in response:

            return clean_text(
                response["response"]
            )

        if "result" in response:

            result = response["result"]

            if isinstance(result, dict):

                if "response" in result:

                    return clean_text(
                        result["response"]
                    )

            return clean_text(result)

    return clean_text(response)


# ============================================================
# AI PROMPTS
# ============================================================

SYSTEM_PROMPT = """
You are a highly critical professional video analyst.

Analyze ONLY the transcript provided by the user.

Your analysis must be:
- accurate
- evidence-based
- concise
- critical
- neutral
- consistent
- useful

IMPORTANT RULES:

1. Never invent facts.
2. Never use outside knowledge.
3. Never assume information that is not present in the transcript.
4. Distinguish between:
   - factual statements
   - claims
   - opinions
   - assumptions
   - interpretations
5. Do not criticize something merely because it is controversial.
6. Criticism must be supported by the transcript.
7. If evidence is insufficient, explicitly say so.
8. Identify important logical weaknesses when present.
9. Identify unsupported claims when present.
10. Identify contradictions when present.
11. Identify overgeneralization when present.
12. Identify exaggerated conclusions when present.
13. Identify unsupported cause-and-effect relationships when present.
14. Identify missing evidence when it materially affects the conclusion.
15. Identify one-sided framing when it materially affects the argument.
16. Do not perform speaker identification.
17. Do not guess who is speaking.
18. Do not add facts from the real world.
19. Do not praise or criticize based on personal preference.
20. Focus on the substance of the transcript.

The final answer MUST be valid JSON.

Do not use markdown.

Return exactly this structure:

{
  "summary": "",
  "key_points": [],
  "critical_analysis": [],
  "takeaways": []
}

Requirements:

summary:
- 1 concise but informative paragraph.

key_points:
- exactly 5 items.
- Each item must capture an important point from the transcript.
- Do not repeat the same point.

critical_analysis:
- 3 to 5 items.
- Each item must contain a meaningful critical observation.
- Only mention weaknesses when supported by the transcript.
- If the transcript is generally strong, say what is strong and what limitations remain.

takeaways:
- exactly 3 items.
- Practical or intellectual conclusions from the transcript.
"""


def build_single_pass_prompt(
    transcript_text: str
) -> str:

    return f"""
Analyze the following complete video transcript.

Do not identify speakers.

TRANSCRIPT:

{transcript_text}

Return ONLY valid JSON.
"""


def build_chunk_prompt(
    chunk_text: str,
    chunk_number: int,
    total_chunks: int
) -> str:

    return f"""
Analyze this transcript segment.

Segment:
{chunk_number} of {total_chunks}

Do not identify speakers.

TRANSCRIPT SEGMENT:

{chunk_text}

Return ONLY valid JSON using this structure:

{{
  "summary": "",
  "key_points": [],
  "critical_analysis": [],
  "takeaways": []
}}

For this segment:
- summary: concise
- key_points: important points only
- critical_analysis: evidence-based critical observations
- takeaways: concise conclusions
"""


def build_final_synthesis_prompt(
    analyses: list[dict]
) -> str:

    material = json.dumps(
        analyses,
        ensure_ascii=False,
        indent=2
    )

    return f"""
Create the final analysis from the following transcript analyses.

The analyses came from different sections of the SAME video.

Combine them carefully.

Do not invent information.

Do not identify speakers.

Remove duplicate points.

Prioritize the most important information.

CRITICAL ANALYSIS must remain evidence-based.

Return ONLY valid JSON.

Required structure:

{{
  "summary": "",
  "key_points": [],
  "critical_analysis": [],
  "takeaways": []
}}

Requirements:

summary:
- 1 concise paragraph.

key_points:
- exactly 5 items.

critical_analysis:
- 3 to 5 items.

takeaways:
- exactly 3 items.

SOURCE ANALYSES:

{material}
"""


# ============================================================
# JSON NORMALIZATION
# ============================================================

def normalize_analysis(
    data: dict
) -> dict:

    summary = clean_text(
        data.get("summary", "")
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

    if not isinstance(key_points, list):
        key_points = []

    if not isinstance(
        critical_analysis,
        list
    ):
        critical_analysis = []

    if not isinstance(takeaways, list):
        takeaways = []

    key_points = [
        clean_text(x)
        for x in key_points
        if clean_text(x)
    ]

    critical_analysis = [
        clean_text(x)
        for x in critical_analysis
        if clean_text(x)
    ]

    takeaways = [
        clean_text(x)
        for x in takeaways
        if clean_text(x)
    ]

    # Keep maximum lengths deterministic.
    key_points = key_points[:5]

    critical_analysis = (
        critical_analysis[:5]
    )

    takeaways = takeaways[:3]

    return {
        "summary": summary,
        "key_points": key_points,
        "critical_analysis": critical_analysis,
        "takeaways": takeaways
    }


# ============================================================
# SINGLE PASS ANALYSIS
# ============================================================

async def analyze_single_pass(
    transcript_text: str
) -> dict:

    prompt = build_single_pass_prompt(
        transcript_text
    )

    raw = await call_ai(
        SYSTEM_PROMPT,
        prompt
    )

    try:

        parsed = parse_json_response(
            raw
        )

    except Exception as exc:

        raise HTTPException(
            status_code=502,
            detail=(
                "AI returned invalid JSON: "
                f"{str(exc)}"
            )
        )

    return normalize_analysis(
        parsed
    )


# ============================================================
# CHUNK ANALYSIS
# ============================================================

async def analyze_chunk(
    chunk_text: str,
    chunk_number: int,
    total_chunks: int
) -> dict:

    system_prompt = """
You are a professional transcript analyst.

Analyze ONLY the provided transcript segment.

Never identify speakers.

Never invent facts.

Focus on:
- important information
- claims
- arguments
- evidence
- logical weaknesses
- contradictions
- assumptions
- unsupported conclusions

Return ONLY valid JSON.
"""

    prompt = build_chunk_prompt(
        chunk_text,
        chunk_number,
        total_chunks
    )

    raw = await call_ai(
        system_prompt,
        prompt
    )

    try:

        parsed = parse_json_response(
            raw
        )

    except Exception as exc:

        raise HTTPException(
            status_code=502,
            detail=(
                "AI returned invalid JSON "
                f"for chunk {chunk_number}: "
                f"{str(exc)}"
            )
        )

    return normalize_analysis(
        parsed
    )


async def analyze_long_transcript(
    transcript: list[dict]
) -> dict:

    chunks = chunk_transcript(
        transcript,
        CHUNK_SIZE
    )

    if not chunks:

        raise HTTPException(
            status_code=400,
            detail="Transcript is empty."
        )

    analyses = []

    for index, chunk in enumerate(
        chunks,
        start=1
    ):

        result = await analyze_chunk(
            chunk,
            index,
            len(chunks)
        )

        analyses.append(result)

    final_prompt = (
        build_final_synthesis_prompt(
            analyses
        )
    )

    raw = await call_ai(
        SYSTEM_PROMPT,
        final_prompt
    )

    try:

        parsed = parse_json_response(
            raw
        )

    except Exception as exc:

        raise HTTPException(
            status_code=502,
            detail=(
                "Final AI synthesis returned "
                f"invalid JSON: {str(exc)}"
            )
        )

    return normalize_analysis(
        parsed
    )


# ============================================================
# TRANSLATION
# ============================================================

TRANSLATION_SYSTEM_PROMPT = """
You are a professional translator.

Translate the supplied English video analysis into natural Indonesian.

Preserve:
- meaning
- structure
- critical nuance
- factual accuracy

Do not add information.

Do not remove important information.

Do not identify speakers.

Return ONLY valid JSON.

Required structure:

{
  "summary": "",
  "key_points": [],
  "critical_analysis": [],
  "takeaways": []
}
"""


def build_translation_prompt(
    english_data: dict
) -> str:

    source = json.dumps(
        english_data,
        ensure_ascii=False
    )

    return f"""
Translate this analysis from English to Indonesian.

SOURCE:

{source}

Return ONLY valid JSON.
"""


async def translate_analysis(
    english_data: dict
) -> dict:

    raw = await call_ai(
        TRANSLATION_SYSTEM_PROMPT,
        build_translation_prompt(
            english_data
        )
    )

    try:

        parsed = parse_json_response(
            raw
        )

    except Exception as exc:

        raise HTTPException(
            status_code=502,
            detail=(
                "AI translation returned "
                f"invalid JSON: {str(exc)}"
            )
        )

    return normalize_analysis(
        parsed
    )


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/")
async def root():

    return {
        "status": "ok",
        "service": "AI Video Summarizer API",
        "version": "2.0.0"
    }


@app.get("/health")
async def health():

    return {
        "status": "healthy"
    }


# ============================================================
# ANALYZE ENDPOINT
# ============================================================

@app.post("/analyze")
async def analyze_video(
    payload: dict
):

    url = clean_text(
        payload.get("url", "")
    )

    if not url:

        raise HTTPException(
            status_code=400,
            detail="YouTube URL is required."
        )

    video_id = extract_video_id(
        url
    )

    if not video_id:

        raise HTTPException(
            status_code=400,
            detail="Invalid YouTube URL."
        )

    # --------------------------------------------------------
    # 1. GET YOUTUBE METADATA
    # --------------------------------------------------------

    metadata = await get_youtube_metadata(
        url
    )

    # --------------------------------------------------------
    # 2. GET TRANSCRIPT
    # --------------------------------------------------------

    transcript, transcript_source = (
        await get_transcript(url)
    )

    # --------------------------------------------------------
    # 3. TRANSCRIPT HASH
    # --------------------------------------------------------

    t_hash = transcript_hash(
        transcript
    )

    transcript_text = transcript_to_text(
        transcript
    )

    if not transcript_text:

        raise HTTPException(
            status_code=404,
            detail="Transcript text is empty."
        )

    # --------------------------------------------------------
    # 4. AI ANALYSIS
    # --------------------------------------------------------

    if len(transcript_text) <= MAX_SINGLE_PASS_CHARS:

        # FAST PATH
        #
        # Most normal videos use only ONE AI analysis call.
        #
        english_analysis = (
            await analyze_single_pass(
                transcript_text
            )
        )

        analysis_mode = "single_pass"

    else:

        # LONG VIDEO PATH
        #
        # Very long transcript uses chunking.
        #

        english_analysis = (
            await analyze_long_transcript(
                transcript
            )
        )

        analysis_mode = "chunked"

    # --------------------------------------------------------
    # 5. INDONESIAN VERSION
    # --------------------------------------------------------

    indonesian_analysis = (
        await translate_analysis(
            english_analysis
        )
    )

    # --------------------------------------------------------
    # 6. FINAL RESPONSE
    # --------------------------------------------------------

    return {
        "success": True,

        "video": {
            "id": video_id,
            "url": normalize_youtube_url(
                url
            ),
            "title": metadata.get(
                "title",
                ""
            ),
            "author_name": metadata.get(
                "author_name",
                ""
            ),
            "author_url": metadata.get(
                "author_url",
                ""
            ),
            "thumbnail_url": metadata.get(
                "thumbnail_url",
                ""
            )
        },

        "transcript": transcript,

        "transcript_info": {
            "language": transcript_source.get(
                "language",
                ""
            )
            if isinstance(
                transcript_source,
                dict
            )
            else "",
            "segments": len(
                transcript
            ),
            "characters": len(
                transcript_text
            ),
            "hash": t_hash
        },

        "analysis": {
            "mode": analysis_mode,
            "single_pass": (
                analysis_mode
                == "single_pass"
            )
        },

        "summary": {
            "en": english_analysis,
            "id": indonesian_analysis
        }
    }


# ============================================================
# CLOUDFLARE WORKERS ENTRYPOINT
# ============================================================

Default = asgi.entrypoint(app)
