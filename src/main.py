from fastapi import FastAPI
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
# CONFIGURATION
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

CHUNK_SIZE = 18000


# ============================================================
# ROOT
# ============================================================

@app.get("/")
async def root():

    return {
        "status": "ok",
        "message": "AI Video Summarizer API V2.1 is running"
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
# CLEAN TEXT
# ============================================================

def clean_text(value):

    if value is None:
        return ""

    return str(value).strip()


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

    # Remove Markdown code fence
    cleaned = re.sub(
        r"```(?:json)?",
        "",
        text,
        flags=re.IGNORECASE
    )

    cleaned = cleaned.replace(
        "```",
        ""
    ).strip()

    try:
        return json.loads(cleaned)
    except Exception:
        pass

    # Find JSON object inside additional text
    start = cleaned.find("{")
    end = cleaned.rfind("}")

    if start >= 0 and end > start:

        candidate = cleaned[
            start:end + 1
        ]

        try:
            return json.loads(candidate)
        except Exception:
            pass

    return None


# ============================================================
# FORMAT TIMESTAMP
# ============================================================

def format_timestamp(seconds):

    try:
        seconds = int(
            float(seconds)
        )
    except Exception:
        seconds = 0

    hours = seconds // 3600

    minutes = (
        seconds % 3600
    ) // 60

    secs = seconds % 60

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
# YOUTUBE METADATA
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
# FREE TRANSCRIPT API
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

    transcript = data.get(
        "transcript",
        []
    )

    if not transcript:

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

        lines.append(
            f"[{timestamp}] {segment['text']}"
        )

    return "\n".join(lines)


# ============================================================
# BUILD DETERMINISTIC CHUNKS
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

        # Very long individual segment
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

        # Start a new chunk
        if (
            current_lines
            and
            current_length + line_length
            > max_chars
        ):

            chunks.append({
                "chunk_index": len(chunks) + 1,
                "start": current_lines[0]["start"],
                "end": current_lines[-1]["end"],
                "text": "\n".join(
                    item["line"]
                    for item in current_lines
                )
            })

            current_lines = []
            current_length = 0

        current_lines.append({
            "line": line,
            "start": segment["start"],
            "end": (
                segment["start"]
                + segment["duration"]
            )
        })

        current_length += line_length

    # Last chunk
    if current_lines:

        chunks.append({
            "chunk_index": len(chunks) + 1,
            "start": current_lines[0]["start"],
            "end": current_lines[-1]["end"],
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
                    # Lowest possible temperature for
                    # maximum practical consistency.
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
# CHUNK ANALYSIS
# ============================================================

async def analyze_chunk(
    title,
    chunk
):

    system_prompt = """
You are a rigorous professional video-content analyst.

Your task is to analyze ONE PART of a longer YouTube video.

==================================================
PRIMARY OBJECTIVE
==================================================

Extract the substantive content accurately.

Do not simply rewrite every sentence.

Identify:

- important topics
- important arguments
- claims
- evidence
- examples
- reasoning
- conclusions
- assumptions
- weaknesses
- contradictions
- missing evidence

==================================================
EVIDENCE RULES
==================================================

1. Use ONLY information contained in the supplied transcript.

2. Do NOT use outside knowledge.

3. Do NOT invent:
   - facts
   - statistics
   - sources
   - names
   - events
   - identities
   - occupations
   - motives
   - background information

4. Do NOT identify speakers.

5. Do NOT infer speaker identity.

6. Treat statements as claims unless the transcript itself provides
   enough evidence to establish them as facts.

7. Distinguish between:
   - factual statements
   - claims
   - opinions
   - assumptions
   - examples
   - conclusions

8. If evidence is insufficient, do not guess.

==================================================
CRITICAL READING
==================================================

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
- conclusions stronger than the evidence
- one-sided framing
- important omissions

Only identify a weakness when the transcript provides a basis.

Do not manufacture criticism.

==================================================
CONSISTENCY
==================================================

For the same transcript chunk:

- use the same analytical priorities
- preserve the same meaning
- do not randomly change conclusions
- ignore filler and repetition
- prioritize substantive information

==================================================
OUTPUT
==================================================

Return ONLY valid JSON.

No Markdown.
No code fences.
No explanations.

Use exactly:

{
  "topics": [],
  "important_points": [],
  "critical_observations": [],
  "chunk_summary": ""
}
"""

    user_prompt = f"""
VIDEO TITLE:
{title}

CHUNK:
{chunk['chunk_index']}

TIMESTAMP:
{format_timestamp(chunk['start'])}
-
{format_timestamp(chunk['end'])}

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

    if not isinstance(
        topics,
        list
    ):
        topics = []

    if not isinstance(
        important_points,
        list
    ):
        important_points = []

    if not isinstance(
        critical_observations,
        list
    ):
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
        separators=(
            ",",
            ":"
        )
    )

    system_prompt = """
You are the final editor and critical reviewer of a YouTube video.

Your task is to create a sharp, accurate, evidence-based analysis
of the COMPLETE video.

==================================================
SOURCE LIMIT
==================================================

Use ONLY the supplied intermediate analyses.

Do NOT use outside knowledge.

Do NOT invent:

- facts
- statistics
- sources
- names
- events
- identities
- occupations
- motives
- background information

==================================================
CRITICAL STANDARD
==================================================

Do not automatically treat statements in the video as facts.

Evaluate the strength of the reasoning presented.

Look for:

1. Unsupported claims
2. Missing evidence
3. Weak reasoning
4. Logical gaps
5. Contradictions
6. Hidden assumptions
7. Overgeneralization
8. Exaggeration
9. Unsupported cause-and-effect
10. Conclusions stronger than the evidence
11. One-sided framing
12. Important omissions

For every criticism, explain WHY the issue matters.

Do not criticize merely for the sake of criticism.

If something is well supported, say so.

If evidence is insufficient, explicitly state:

"Insufficient evidence in the transcript."

==================================================
SPEAKER RULE
==================================================

Do NOT identify speakers.

Do NOT infer:

- speaker identity
- occupation
- role
- background
- motive

Focus exclusively on the content.

==================================================
SUMMARY
==================================================

Summarize the central message.

Do not simply rewrite the transcript.

Focus on:

- what the video is about
- the central argument
- the most important conclusion

==================================================
KEY POINTS
==================================================

Provide EXACTLY 5 key points.

Each point must contain a meaningful idea.

Do not create five points from the same idea.

Prioritize substantive information.

Ignore greetings, filler, jokes, and repetition unless they are
important to understanding the content.

==================================================
CRITICAL ANALYSIS
==================================================

Provide 3 to 5 critical observations.

Each observation should explain:

- what the issue is
- what evidence is available
- why the issue matters

Potential issues include:

- unsupported claims
- missing evidence
- logical gaps
- contradictions
- assumptions
- exaggeration
- weak causal reasoning
- overgeneralization
- one-sided framing

Do not invent weaknesses.

==================================================
TAKEAWAYS
==================================================

Provide EXACTLY 3 takeaways.

They should explain:

- what the viewer should understand
- what the viewer should question
- what may require verification

==================================================
LANGUAGE
==================================================

Produce:

EN = professional English

ID = professional Indonesian

Both versions MUST communicate the same conclusions.

Do not introduce information in one language that is absent from
the other.

==================================================
CONSISTENCY
==================================================

For the same input:

- preserve the same conclusions
- preserve the same important ideas
- use the same analytical priorities
- do not randomly change conclusions
- do not add unnecessary sections

==================================================
OUTPUT FORMAT
==================================================

Return ONLY valid JSON.

No Markdown.
No code fences.
No explanations.

Use EXACTLY:

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

INTERMEDIATE ANALYSES:

{analysis_text}

Create the final analysis.

Important:

- Use information from ALL chunks.
- Do not focus only on the beginning.
- Do not identify speakers.
- Do not use outside knowledge.
- Be sharp and critical.
- Be evidence-based.
- Exactly 5 key points.
- 3 to 5 critical analysis observations.
- Exactly 3 takeaways.
- English and Indonesian must contain the same conclusions.
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

    if not isinstance(
        en,
        dict
    ):
        en = {}

    if not isinstance(
        id_data,
        dict
    ):
        id_data = {}

    def clean_list(value):

        if not isinstance(
            value,
            list
        ):
            return []

        return [
            clean_text(x)
            for x in value
            if clean_text(x)
        ]

    en_key_points = clean_list(
        en.get(
            "key_points",
            []
        )
    )

    id_key_points = clean_list(
        id_data.get(
            "key_points",
            []
        )
    )

    en_critical = clean_list(
        en.get(
            "critical_analysis",
            []
        )
    )

    id_critical = clean_list(
        id_data.get(
            "critical_analysis",
            []
        )
    )

    en_takeaways = clean_list(
        en.get(
            "takeaways",
            []
        )
    )

    id_takeaways = clean_list(
        id_data.get(
            "takeaways",
            []
        )
    )

    # Enforce output structure
    en_key_points = en_key_points[:5]
    id_key_points = id_key_points[:5]

    en_critical = en_critical[:5]
    id_critical = id_critical[:5]

    en_takeaways = en_takeaways[:3]
    id_takeaways = id_takeaways[:3]

    return {
        "en": {
            "summary": clean_text(
                en.get(
                    "summary",
                    ""
                )
            ),

            "key_points": en_key_points,

            "critical_analysis": en_critical,

            "takeaways": en_takeaways
        },

        "id": {
            "summary": clean_text(
                id_data.get(
                    "summary",
                    ""
                )
            ),

            "key_points": id_key_points,

            "critical_analysis": id_critical,

            "takeaways": id_takeaways
        }
    }


# ============================================================
# ANALYZE ENDPOINT
# ============================================================

@app.post("/analyze")
async def analyze(data: dict):

    try:

        # ----------------------------------------------------
        # 1. URL
        # ----------------------------------------------------

        url = clean_text(
            data.get("url")
        )

        if not url:

            return {
                "status": "error",
                "message": "YouTube URL is required"
            }


        # ----------------------------------------------------
        # 2. YOUTUBE METADATA
        # ----------------------------------------------------

        metadata = await get_youtube_metadata(
            url
        )


        # ----------------------------------------------------
        # 3. TRANSCRIPT
        # ----------------------------------------------------

        transcript_result = await get_transcript(
            url
        )

        if not transcript_result.get(
            "ok"
        ):

            return {
                "status": "error",

                "message":
                    "FreeTranscriptAPI request failed",

                "http_status":
                    transcript_result.get(
                        "status_code"
                    ),

                "details":
                    transcript_result.get(
                        "details"
                    )
            }

        transcript_data = (
            transcript_result["data"]
        )


        # ----------------------------------------------------
        # 4. VIDEO INFORMATION
        # ----------------------------------------------------

        video_title = clean_text(
            transcript_data.get(
                "title"
            )
        )

        if not video_title:

            video_title = (
                metadata.get(
                    "title"
                )
                or
                "Unknown title"
            )

        language = clean_text(
            transcript_data.get(
                "language"
            )
        )

        if not language:

            language = "unknown"


        # ----------------------------------------------------
        # 5. NORMALIZE TRANSCRIPT
        # ----------------------------------------------------

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


        # ----------------------------------------------------
        # 6. FULL TRANSCRIPT
        # ----------------------------------------------------

        full_transcript = (
            build_full_transcript(
                segments
            )
        )


        # ----------------------------------------------------
        # 7. CHUNKS
        # ----------------------------------------------------

        chunks = build_chunks(
            segments
        )

        if not chunks:

            return {
                "status": "error",
                "message":
                    "Unable to create transcript chunks"
            }


        # ----------------------------------------------------
        # 8. ANALYZE CHUNKS
        # ----------------------------------------------------

        chunk_results = []

        for chunk in chunks:

            result = await analyze_chunk(
                title=video_title,
                chunk=chunk
            )

            chunk_results.append(
                result
            )


        # ----------------------------------------------------
        # 9. FINAL SYNTHESIS
        # ----------------------------------------------------

        ai_summary = await final_synthesis(
            title=video_title,
            language=language,
            chunk_results=chunk_results
        )


        # ----------------------------------------------------
        # 10. RETURN
        # ----------------------------------------------------

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
                    "temperature_0",

                "speaker_identification":
                    False
            },

            "summary":
                ai_summary,

            "transcript":
                transcript_data
        }


    except Exception as error:

        return {

            "status": "error",

            "message":
                "Worker exception",

            "error_type":
                type(error).__name__,

            "error":
                str(error)
        }


# ============================================================
# CLOUDFLARE WORKERS ENTRYPOINT
# ============================================================

Default = asgi.entrypoint(app)
