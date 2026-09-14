from pathlib import Path

source = Path("/mnt/data/Pasted text(20260914-044604).txt")
output = Path("/mnt/data/main_STEP1_STABLE_CRITICAL.py")

code = r'''from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from workers import asgi, env

import httpx2 as httpx
import json
import re
from urllib.parse import quote


# ============================================================
# APP
# ============================================================

app = FastAPI(
    title="AI Video Summarizer API",
    description="Backend API for AI Video Summarizer",
    version="2.1.0"
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
# CONSTANTS
# ============================================================

TRANSCRIPT_API_URL = (
    "https://api.freetranscriptapi.com/v1/transcript"
)

YOUTUBE_OEMBED_URL = (
    "https://www.youtube.com/oembed"
)

AI_MODEL = (
    "@cf/zai-org/glm-4.7-flash"
)

# Keep chunking deterministic.
# The same transcript always produces the same chunk boundaries.
CHUNK_SIZE = 18000


# ============================================================
# ROOT
# ============================================================

@app.get("/")
async def root():
    return {
        "status": "ok",
        "message": "AI Video Summarizer API V2.1 Stable is running on Cloudflare"
    }


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "version": "2.1.0"
    }


# ============================================================
# SAFE JSON EXTRACTION
# ============================================================

def extract_json(text):
    if not text:
        return None

    text = str(text).strip()

    # Direct JSON
    try:
        return json.loads(text)
    except Exception:
        pass

    # Remove Markdown code fences
    cleaned = re.sub(
        r"```(?:json)?",
        "",
        text,
        flags=re.IGNORECASE
    )

    cleaned = cleaned.replace("```", "").strip()

    try:
        return json.loads(cleaned)
    except Exception:
        pass

    # Find first JSON object
    start = cleaned.find("{")
    end = cleaned.rfind("}")

    if start >= 0 and end > start:
        candidate = cleaned[start:end + 1]

        try:
            return json.loads(candidate)
        except Exception:
            pass

    return None


# ============================================================
# SAFE STRING
# ============================================================

def clean_text(value):
    if value is None:
        return ""

    return str(value).strip()


# ============================================================
# FORMAT TIMESTAMP
# ============================================================

def format_timestamp(seconds):
    try:
        seconds = int(float(seconds))
    except Exception:
        seconds = 0

    hours = seconds // 3600

    minutes = (
        seconds % 3600
    ) // 60

    secs = (
        seconds % 60
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
# FETCH YOUTUBE METADATA
# ============================================================

async def get_youtube_metadata(url):

    result = {
        "title": "",
        "author_name": "",
        "author_url": "",
        "provider": "youtube_oembed"
    }

    try:
        encoded_url = quote(
            url,
            safe=""
        )

        oembed_url = (
            f"{YOUTUBE_OEMBED_URL}"
            f"?url={encoded_url}"
            f"&format=json"
        )

        async with httpx.AsyncClient() as client:
            response = await client.get(
                oembed_url,
                timeout=15.0
            )

        if response.status_code >= 400:
            return result

        data = response.json()

        result["title"] = clean_text(
            data.get("title")
        )

        result["author_name"] = clean_text(
            data.get("author_name")
        )

        result["author_url"] = clean_text(
            data.get("author_url")
        )

    except Exception:
        pass

    return result


# ============================================================
# FETCH TRANSCRIPT
# ============================================================

async def get_transcript(url):

    api_key = getattr(
        env,
        "FREETRANSCRIPT_API_KEY",
        None
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
            TRANSCRIPT_API_URL,
            params=params,
            headers=headers,
            timeout=60.0
        )

    if response.status_code >= 400:
        return {
            "ok": False,
            "status_code": response.status_code,
            "details": response.text
        }

    data = response.json()

    transcript_segments = data.get(
        "transcript",
        []
    )

    if not transcript_segments:
        return {
            "ok": False,
            "status_code": 200,
            "details": "Transcript is empty"
        }

    return {
        "ok": True,
        "data": data
    }


# ============================================================
# NORMALIZE TRANSCRIPT
# ============================================================

def normalize_segments(segments):

    normalized = []

    for index, segment in enumerate(segments):

        if not isinstance(segment, dict):
            continue

        text = clean_text(
            segment.get("text")
        )

        if not text:
            continue

        start = segment.get(
            "start",
            0
        )

        duration = segment.get(
            "duration",
            0
        )

        try:
            start = float(start)
        except Exception:
            start = 0.0

        try:
            duration = float(duration)
        except Exception:
            duration = 0.0

        normalized.append({
            "index": index,
            "start": start,
            "duration": duration,
            "text": text
        })

    return normalized


# ============================================================
# BUILD FULL TRANSCRIPT
# ============================================================

def build_full_transcript(segments):

    lines = []

    for segment in segments:

        timestamp = format_timestamp(
            segment["start"]
        )

        text = segment["text"]

        lines.append(
            f"[{timestamp}] {text}"
        )

    return "\n".join(lines)


# ============================================================
# BUILD CHUNKS
# ============================================================

def build_chunks(
    segments,
    max_chars=CHUNK_SIZE
):

    chunks = []

    current_lines = []
    current_length = 0

    for segment in segments:

        timestamp = format_timestamp(
            segment["start"]
        )

        line = (
            f"[{timestamp}] "
            f"{segment['text']}"
        )

        line_length = len(line) + 1

        # If one transcript line is extremely long,
        # keep it as one deterministic chunk.
        if (
            len(line) > max_chars
            and not current_lines
        ):
            chunks.append({
                "chunk_index": len(chunks) + 1,
                "start": segment["start"],
                "end": (
                    segment["start"]
                    + segment["duration"]
                ),
                "text": line
            })

            continue

        # Start a new deterministic chunk.
        if (
            current_lines
            and current_length + line_length
            > max_chars
        ):
            chunks.append({
                "chunk_index": len(chunks) + 1,
                "start": current_lines[0]["_start"],
                "end": current_lines[-1]["_end"],
                "text": "\n".join(
                    item["line"]
                    for item in current_lines
                )
            })

            current_lines = []
            current_length = 0

        current_lines.append({
            "line": line,
            "_start": segment["start"],
            "_end": (
                segment["start"]
                + segment["duration"]
            )
        })

        current_length += line_length

    # Last chunk
    if current_lines:
        chunks.append({
            "chunk_index": len(chunks) + 1,
            "start": current_lines[0]["_start"],
            "end": current_lines[-1]["_end"],
            "text": "\n".join(
                item["line"]
                for item in current_lines
            )
        })

    return chunks


# ============================================================
# AI CALL
# ============================================================

async def call_ai(
    system_prompt,
    user_prompt,
    max_retries=2
):

    last_error = ""

    for attempt in range(
        max_retries + 1
    ):

        try:

            response = await env.AI.run(
                AI_MODEL,
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

                    # STEP 1:
                    # deterministic sampling setting.
                    # This improves repeatability but by itself
                    # cannot guarantee byte-for-byte identical
                    # model output. Exact repeatability will be
                    # handled later with caching.
                    "temperature": 0.0,

                    "chat_template_kwargs": {
                        "enable_thinking": False
                    }
                }
            )

            content = (
                response
                .get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
            )

            if content:
                return clean_text(
                    content
                )

            last_error = (
                "AI returned empty content"
            )

        except Exception as error:

            last_error = str(error)

    raise Exception(
        f"AI request failed: {last_error}"
    )


# ============================================================
# ANALYZE CHUNK
# ============================================================

async def analyze_chunk(
    title,
    chunk
):

    system_prompt = """
You are a rigorous professional video-content analyst.

You are analyzing ONE PART of a longer YouTube video.

PRIMARY OBJECTIVE
Extract the substantive content of this transcript chunk accurately.
Do not merely paraphrase every sentence.

EVIDENCE DISCIPLINE
1. Use ONLY information contained in the supplied transcript chunk.
2. Do not use outside knowledge.
3. Do not invent facts, names, statistics, events, sources, motives,
   occupations, identities, or background information.
4. Treat statements in the transcript as claims unless the transcript
   itself provides enough evidence to establish them as facts.
5. Distinguish claims, opinions, assumptions, explanations, evidence,
   examples, and conclusions when the distinction is clear.
6. If the transcript is insufficient to establish something, do not guess.
7. Do not manufacture criticism.
8. Do not infer who is speaking.
9. Do not perform speaker identification.
10. Focus on CONTENT, ARGUMENTS, EVIDENCE, REASONING, and CONCLUSIONS.

CRITICAL READING
Look for:
- unsupported claims
- missing evidence
- weak reasoning
- logical gaps
- contradictions
- hidden assumptions
- overgeneralization
- exaggeration
- unsupported cause-and-effect
- conclusions that go beyond the information presented
- one-sided framing
- important omissions that are visible from the transcript itself

Only flag a weakness when the transcript provides a concrete basis.
If no meaningful weakness is visible in this chunk, do not invent one.

CONSISTENCY RULE
For the same transcript chunk, apply the same analytical priorities:
1. Main topic
2. Main argument or idea
3. Important supporting information
4. Evidence or examples
5. Weaknesses or limitations
6. Conclusion or implication

Ignore greetings, filler, jokes, repetition, and conversational noise
unless they materially affect the meaning.

Return ONLY valid JSON.
No Markdown.
No code fences.

Use exactly this structure:

{
  "topics": [],
  "important_points": [],
  "critical_observations": [],
  "chunk_summary": ""
}

The arrays may contain only information supported by the transcript.
Use concise but information-dense wording.
"""

    user_prompt = f"""
VIDEO TITLE:
{title}

CHUNK NUMBER:
{chunk['chunk_index']}

TIMESTAMP:
{format_timestamp(chunk['start'])} - {format_timestamp(chunk['end'])}

TRANSCRIPT:
{chunk['text']}
"""

    ai_text = await call_ai(
        system_prompt,
        user_prompt
    )

    result = extract_json(
        ai_text
    )

    if not result:
        return {
            "topics": [],
            "important_points": [],
            "critical_observations": [],
            "chunk_summary": ai_text
        }

    topics = result.get(
        "topics",
        []
    )

    important_points = result.get(
        "important_points",
        []
    )

    critical_observations = result.get(
        "critical_observations",
        []
    )

    if not isinstance(topics, list):
        topics = []

    if not isinstance(important_points, list):
        important_points = []

    if not isinstance(critical_observations, list):
        critical_observations = []

    return {
        "topics": [
            clean_text(x)
            for x in topics
            if clean_text(x)
        ],
        "important_points": [
            clean_text(x)
            for x in important_points
            if clean_text(x)
        ],
        "critical_observations": [
            clean_text(x)
            for x in critical_observations
            if clean_text(x)
        ],
        "chunk_summary": clean_text(
            result.get(
                "chunk_summary",
                ""
            )
        )
    }


# ============================================================
# FINAL SYNTHESIS
# ============================================================

async def final_synthesis(
    title,
    language,
    chunk_results
):

    analysis_blocks = []

    for index, result in enumerate(
        chunk_results,
        start=1
    ):

        analysis_blocks.append({
            "chunk": index,
            "topics": result.get(
                "topics",
                []
            ),
            "important_points": result.get(
                "important_points",
                []
            ),
            "critical_observations": result.get(
                "critical_observations",
                []
            ),
            "summary": result.get(
                "chunk_summary",
                ""
            )
        })

    analysis_text = json.dumps(
        analysis_blocks,
        ensure_ascii=False,
        separators=(",", ":")
    )

    system_prompt = """
You are the final editor and critical reviewer of a long-form YouTube video.

Your job is NOT to praise the video and NOT to rewrite the transcript.
Your job is to produce a sharp, evidence-based, intellectually honest
analysis of the content.

SOURCE LIMIT
You may use ONLY the supplied intermediate analyses.
Do not use outside knowledge.
Do not invent facts, sources, names, motives, identities, occupations,
events, statistics, or background information.

CRITICAL STANDARD
Be analytical rather than diplomatic.

Actively test the reasoning presented in the video for:
- unsupported claims
- missing evidence
- weak reasoning
- logical gaps
- contradictions
- hidden assumptions
- overgeneralization
- exaggeration
- unsupported cause-and-effect
- conclusions stronger than the evidence presented
- one-sided framing
- important omissions

IMPORTANT:
A claim is NOT automatically a fact merely because it appears in the video.

However, do NOT manufacture criticism.
If a claim is reasonable and well supported by the supplied material,
say so.
If there is insufficient evidence to judge it, explicitly say:
"Insufficient evidence in the transcript."

SPEAKER RULE
Do NOT identify speakers.
Do NOT infer speaker identity, occupation, role, motive, or background.
Focus exclusively on the content.

CONSISTENCY RULES
For repeated analysis of the same input:
- use the same analytical priorities
- preserve the same major conclusions
- do not change conclusions merely to vary wording
- do not add new sections
- do not randomly reorder important ideas
- remove duplicate points
- prioritize substantive information over filler
- preserve chronology when it materially affects understanding

OUTPUT RULES
1. Produce BOTH English and Indonesian.
2. Both languages must contain the same conclusions.
3. Do not introduce information in one language that is absent in the other.
4. Summary must be concise but substantive.
5. Provide EXACTLY 5 key points.
6. Provide 3 to 5 critical analysis observations.
7. Provide 3 concise takeaways.
8. Each key point must contain a meaningful idea, not filler.
9. Critical observations must explain WHY something is weak, unsupported,
   incomplete, or strong when the evidence permits.
10. Takeaways must identify what the viewer should understand, question,
    verify, or learn.
11. Do not use emotional, personal, political, ideological, or moral
    judgments unless they are explicitly part of the content and relevant
    to evaluating the argument.
12. Do not exaggerate criticism simply to make the analysis sound sharp.

Return ONLY valid JSON.
No Markdown.
No code fences.
No additional fields.

Use EXACTLY this structure:

{
  "en": {
    "summary": "",
    "key_points": [
      "",
      "",
      "",
      "",
      ""
    ],
    "critical_analysis": [
      "",
      "",
      ""
    ],
    "takeaways": [
      "",
      "",
      ""
    ]
  },
  "id": {
    "summary": "",
    "key_points": [
      "",
      "",
      "",
      "",
      ""
    ],
    "critical_analysis": [
      "",
      "",
      ""
    ],
    "takeaways": [
      "",
      "",
      ""
    ]
  }
}
"""

    user_prompt = f"""
VIDEO TITLE:
{title}

TRANSCRIPT LANGUAGE:
{language}

INTERMEDIATE ANALYSES FROM ALL TRANSCRIPT CHUNKS:

{analysis_text}

Now produce the final analysis.

Remember:
- use all important sections, including later chunks
- do not identify speakers
- do not use outside knowledge
- be sharp and critical, but evidence-based
- exactly 5 key points in each language
- 3 to 5 critical analysis observations
- exactly 3 takeaways
- English and Indonesian must express the same conclusions
"""

    ai_text = await call_ai(
        system_prompt,
        user_prompt
    )

    result = extract_json(
        ai_text
    )

    if not result:
        return {
            "en": {
                "summary": ai_text,
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

    en = result.get(
        "en",
        {}
    )

    id_data = result.get(
        "id",
        {}
    )

    if not isinstance(en, dict):
        en = {}

    if not isinstance(id_data, dict):
        id_data = {}

    def clean_list(value):
        if not isinstance(value, list):
            return []

        return [
            clean_text(x)
            for x in value
            if clean_text(x)
        ]

    en_key_points = clean_list(
        en.get("key_points", [])
    )

    id_key_points = clean_list(
        id_data.get("key_points", [])
    )

    en_critical = clean_list(
        en.get("critical_analysis", [])
    )

    id_critical = clean_list(
        id_data.get("critical_analysis", [])
    )

    en_takeaways = clean_list(
        en.get("takeaways", [])
    )

    id_takeaways = clean_list(
        id_data.get("takeaways", [])
    )

    # Enforce deterministic structural limits.
    # The model is instructed to produce these sizes, but the backend
    # also normalizes the result so malformed responses do not change
    # the API structure.

    en_key_points = en_key_points[:5]
    id_key_points = id_key_points[:5]

    en_critical = en_critical[:5]
    id_critical = id_critical[:5]

    en_takeaways = en_takeaways[:3]
    id_takeaways = id_takeaways[:3]

    return {
        "en": {
            "summary": clean_text(
                en.get("summary", "")
            ),
            "key_points": en_key_points,
            "critical_analysis": en_critical,
            "takeaways": en_takeaways
        },
        "id": {
            "summary": clean_text(
                id_data.get("summary", "")
            ),
            "key_points": id_key_points,
            "critical_analysis": id_critical,
            "takeaways": id_takeaways
        }
    }


# ============================================================
# ANALYZE
# ============================================================

@app.post("/analyze")
async def analyze(data: dict):

    try:

        # ====================================================
        # 1. GET URL
        # ====================================================

        url = clean_text(
            data.get("url")
        )

        if not url:
            return {
                "status": "error",
                "message": "YouTube URL is required"
            }


        # ====================================================
        # 2. YOUTUBE METADATA
        # ====================================================

        metadata = await get_youtube_metadata(
            url
        )


        # ====================================================
        # 3. TRANSCRIPT
        # ====================================================

        transcript_result = await get_transcript(
            url
        )

        if not transcript_result.get("ok"):
            return {
                "status": "error",
                "message": "FreeTranscriptAPI request failed",
                "http_status": transcript_result.get(
                    "status_code"
                ),
                "details": transcript_result.get(
                    "details"
                )
            }

        transcript_data = transcript_result["data"]


        # ====================================================
        # 4. VIDEO INFORMATION
        # ====================================================

        video_title = clean_text(
            transcript_data.get("title")
        )

        if not video_title:
            video_title = (
                metadata.get("title")
                or "Unknown title"
            )

        language = clean_text(
            transcript_data.get("language")
        )

        if not language:
            language = "unknown"

        segments = normalize_segments(
            transcript_data.get(
                "transcript",
                []
            )
        )

        if not segments:
            return {
                "status": "error",
                "message": "Transcript is empty"
            }


        # ====================================================
        # 5. BUILD COMPLETE TRANSCRIPT
        # ====================================================

        full_transcript = build_full_transcript(
            segments
        )


        # ====================================================
        # 6. BUILD DETERMINISTIC CHUNKS
        # ====================================================

        chunks = build_chunks(
            segments
        )

        if not chunks:
            return {
                "status": "error",
                "message": "Unable to create transcript chunks"
            }


        # ====================================================
        # 7. ANALYZE EACH CHUNK
        # ====================================================

        chunk_results = []

        for chunk in chunks:

            result = await analyze_chunk(
                title=video_title,
                chunk=chunk
            )

            chunk_results.append(
                result
            )


        # ====================================================
        # 8. FINAL SYNTHESIS
        # ====================================================

        ai_summary = await final_synthesis(
            title=video_title,
            language=language,
            chunk_results=chunk_results
        )


        # ====================================================
        # 9. RETURN
        # ====================================================

        return {
            "status": "success",
            "version": "2.1.0",
            "youtube_url": url,
            "title": video_title,
            "language": language,

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
                    )
            },

            "processing": {
                "total_segments":
                    len(segments),
                "total_chunks":
                    len(chunks),
                "transcript_characters":
                    len(full_transcript),
                "stability":
                    "temperature_0_no_speaker_analysis"
            },

            "summary": ai_summary,

            "transcript":
                transcript_data
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
'''

output.write_text(code, encoding="utf-8")

print(f"File berhasil dibuat: {output}")
print(f"Jumlah baris: {len(code.splitlines())}")
