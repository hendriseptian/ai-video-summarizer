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
    version="2.0.0"
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

# Ukuran chunk transcript.
# Tidak memotong transcript secara keseluruhan.
CHUNK_SIZE = 18000

# Maksimum karakter metadata/sampling yang digunakan
# untuk speaker identification.
SPEAKER_SAMPLE_SIZE = 30000


# ============================================================
# ROOT
# ============================================================

@app.get("/")
async def root():

    return {
        "status": "ok",
        "message": "AI Video Summarizer API V2 is running on Cloudflare"
    }


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
async def health():

    return {
        "status": "healthy",
        "version": "2.0.0"
    }


# ============================================================
# SAFE JSON EXTRACTION
# ============================================================

def extract_json(text):

    if not text:
        return None

    text = str(text).strip()

    # --------------------------------------------------------
    # Direct JSON
    # --------------------------------------------------------

    try:

        return json.loads(text)

    except Exception:
        pass


    # --------------------------------------------------------
    # Remove markdown code block
    # --------------------------------------------------------

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


    # --------------------------------------------------------
    # Find first JSON object
    # --------------------------------------------------------

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

        seconds = int(
            float(seconds)
        )

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


    for index, segment in enumerate(
        segments
    ):

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

def build_full_transcript(
    segments
):

    lines = []


    for segment in segments:

        timestamp = format_timestamp(
            segment["start"]
        )


        text = segment["text"]


        lines.append(
            f"[{timestamp}] {text}"
        )


    return "\n".join(
        lines
    )


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


        # ----------------------------------------------------
        # If one line is extremely long
        # ----------------------------------------------------

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


        # ----------------------------------------------------
        # Create new chunk
        # ----------------------------------------------------

        if (
            current_lines
            and
            current_length + line_length
            > max_chars
        ):

            chunks.append({

                "chunk_index": len(chunks) + 1,

                "start": current_lines[0][
                    "_start"
                ],

                "end": current_lines[-1][
                    "_end"
                ],

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


    # --------------------------------------------------------
    # Last chunk
    # --------------------------------------------------------

    if current_lines:

        chunks.append({

            "chunk_index": len(chunks) + 1,

            "start": current_lines[0][
                "_start"
            ],

            "end": current_lines[-1][
                "_end"
            ],

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

                            "content":
                                system_prompt

                        },

                        {

                            "role": "user",

                            "content":
                                user_prompt

                        }

                    ],

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
# SPEAKER IDENTIFICATION
# ============================================================

async def identify_speakers(
    title,
    author_name,
    transcript
):

    sample = transcript[
        :SPEAKER_SAMPLE_SIZE
    ]


    system_prompt = """
You are a professional video analyst and critical content reviewer.

Your task is to analyze the provided video transcript and produce a
concise, sharp, structured, evidence-based analysis.

==================================================
CORE OBJECTIVE
==================================================

The goal is NOT to simply rewrite or repeat the transcript.

The goal is to identify:

- the central message
- the most important arguments
- the important claims
- the evidence presented
- the assumptions being made
- weaknesses in reasoning
- logical gaps
- contradictions
- unsupported claims
- missing evidence
- misleading framing
- important conclusions
- practical takeaways

The analysis must remain faithful to the transcript.

==================================================
EVIDENCE DISCIPLINE
==================================================

1. Use ONLY information contained in the transcript.

2. NEVER invent:
   - facts
   - statistics
   - sources
   - events
   - names
   - occupations
   - identities
   - intentions
   - background information
   - external context

3. Do NOT use outside knowledge.

4. Do NOT assume that a statement made in the video is automatically
   a fact.

5. A statement presented by a speaker should be treated as a CLAIM
   unless the transcript itself provides sufficient evidence to
   establish it.

6. Clearly distinguish between:
   - FACT STATED IN THE TRANSCRIPT
   - CLAIM
   - OPINION
   - ASSUMPTION
   - INFERENCE
   - CONCLUSION
   - UNVERIFIED STATEMENT

7. If the transcript does not contain enough information to evaluate
   a claim, explicitly state:

   "Insufficient evidence in the transcript."

8. Do not manufacture criticism.

9. Every critical observation must be supported by something actually
   stated in the transcript.

10. If an argument is strong and well supported by the transcript,
    say so.

11. If an argument is weak or unsupported, explain WHY it is weak.

12. Avoid excessive certainty when the transcript does not justify
    certainty.

==================================================
SPEAKER HANDLING
==================================================

Do NOT identify or infer speaker identities.

Do NOT infer:

- profession
- occupation
- role
- background
- personal identity
- intentions

unless explicitly stated in the transcript.

Do not attempt speaker recognition.

The analysis should focus on the CONTENT of the discussion.

==================================================
SUMMARY
==================================================

Write a concise summary of the central message of the video.

The summary must:

- capture the main subject
- explain the central message
- avoid unnecessary details
- avoid repeating the transcript sentence by sentence
- avoid unsupported interpretation

The summary should answer:

"What is this video mainly about?"

==================================================
KEY POINTS
==================================================

Provide EXACTLY 5 key points.

Each key point must represent an important idea from the transcript.

Do not create five points simply by splitting the same idea.

Each point should preferably contain:

- the important idea
- relevant context
- why the point matters

Prioritize substantive information over jokes, filler, greetings,
repetitions, and conversational noise.

==================================================
CRITICAL ANALYSIS
==================================================

Evaluate the content critically.

Look specifically for:

1. Unsupported claims
2. Missing evidence
3. Weak reasoning
4. Logical gaps
5. Contradictions
6. Hidden assumptions
7. Overgeneralization
8. Exaggeration
9. Cause-and-effect claims without sufficient support
10. Conclusions that go beyond the evidence presented
11. One-sided framing
12. Important information that is missing from the discussion

However:

Do NOT criticize something unless the transcript provides a basis
for the criticism.

If there is no meaningful weakness, state that the transcript does
not provide enough evidence to identify a significant weakness.

Critical analysis should be precise, not emotional.

Avoid political, ideological, moral, or personal judgments unless
they are explicitly part of the transcript and relevant to the
analysis.

==================================================
TAKEAWAYS
==================================================

Provide concise practical conclusions.

Takeaways should answer:

- What should the viewer understand?
- What is the most important lesson?
- What should the viewer be cautious about?
- What deserves further verification?

Do not introduce information from outside the transcript.

==================================================
CONSISTENCY RULES
==================================================

The same transcript should produce the same analytical structure.

Always follow the same order:

1. Summary
2. Key Points
3. Critical Analysis
4. Takeaways

Always provide:

- exactly 5 key points
- the same JSON structure
- concise writing
- evidence-based reasoning
- no speaker identification

Do not randomly change the writing structure.

Do not add unnecessary sections.

==================================================
LANGUAGE
==================================================

Produce two versions:

EN:
Natural professional English.

ID:
Natural professional Indonesian.

The Indonesian version must not be a word-for-word translation if
that would make the language unnatural.

Both versions must contain the same analytical conclusions.

Do not introduce new information in one language that does not exist
in the other.

==================================================
OUTPUT FORMAT
==================================================

Return ONLY valid JSON.

Do NOT use Markdown.

Do NOT use:
```json

Do NOT include explanations outside the JSON.

Use exactly this structure:

{
  "en": {
    "summary": "...",
    "key_points": [
      "...",
      "...",
      "...",
      "...",
      "..."
    ],
    "critical_analysis": [
      "...",
      "...",
      "...",
      "..."
    ],
    "takeaways": [
      "...",
      "...",
      "..."
    ]
  },
  "id": {
    "summary": "...",
    "key_points": [
      "...",
      "...",
      "...",
      "...",
      "..."
    ],
    "critical_analysis": [
      "...",
      "...",
      "...",
      "..."
    ],
    "takeaways": [
      "...",
      "...",
      "..."
    ]
  }
}

The JSON must be valid and parseable.

No trailing comments.

No additional fields.
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

            "speakers": []

        }


    speakers = result.get(
        "speakers",
        []
    )


    if not isinstance(
        speakers,
        list
    ):

        speakers = []


    cleaned_speakers = []


    for speaker in speakers:

        if not isinstance(
            speaker,
            dict
        ):

            continue


        name = clean_text(
            speaker.get("name")
        )

        role = clean_text(
            speaker.get("role")
        )

        evidence = clean_text(
            speaker.get("evidence")
        )


        try:

            confidence = float(
                speaker.get(
                    "confidence",
                    0
                )
            )

        except Exception:

            confidence = 0.0


        confidence = max(
            0.0,
            min(
                1.0,
                confidence
            )
        )


        if not name:

            continue


        cleaned_speakers.append({

            "name": name,

            "role": role or "Unknown",

            "confidence":
                round(
                    confidence,
                    2
                ),

            "evidence": evidence

        })


    return {

        "speakers":
            cleaned_speakers

    }


# ============================================================
# FORMAT SPEAKER MAP
# ============================================================

def speaker_map_text(
    speaker_data
):

    speakers = speaker_data.get(
        "speakers",
        []
    )


    if not speakers:

        return (
            "No reliable speaker identity "
            "was established."
        )


    lines = []


    for index, speaker in enumerate(
        speakers,
        start=1
    ):

        lines.append(

            f"{index}. "
            f"{speaker.get('name', 'Unknown')} "
            f"- "
            f"{speaker.get('role', 'Unknown')} "
            f"- confidence "
            f"{speaker.get('confidence', 0)}"

        )


    return "\n".join(
        lines
    )


# ============================================================
# ANALYZE CHUNK
# ============================================================

async def analyze_chunk(
    title,
    speaker_data,
    chunk
):

    speaker_context = (
        speaker_map_text(
            speaker_data
        )
    )


    system_prompt = """

You are an accurate video-content analyst.

You are analyzing ONE PART of a longer YouTube video.

IMPORTANT:

1. Use ONLY information in the supplied transcript chunk.

2. Do not invent facts.

3. Do not add facts from outside knowledge.

4. Preserve the meaning of what was actually said.

5. Speaker identities supplied in SPEAKER MAP are fixed.
   Do not change them.

6. The transcript itself does NOT contain speaker labels.

7. Therefore, DO NOT invent exact speaker attribution
   for individual sentences.

8. Mention a person's name only when the transcript
   itself provides enough evidence.

9. Focus on:
   - important topics
   - arguments
   - stories
   - explanations
   - opinions
   - examples
   - conclusions
   - important events

10. Ignore filler and repetitive conversation unless
    it is meaningful.

11. This is an intermediate analysis.
    Do not write a final global conclusion.

Return ONLY valid JSON.

Use EXACTLY this structure:

{
  "topics": [
    "Topic 1",
    "Topic 2"
  ],
  "important_points": [
    "Important point 1",
    "Important point 2"
  ],
  "speaker_mentions": [
    {
      "name": "Name",
      "role": "Role",
      "context": "What the transcript says about this person."
    }
  ],
  "chunk_summary": "Detailed summary of this chunk."
}

If there are no speaker mentions:

"speaker_mentions": []

Do not use Markdown.
Do not use ```json.
"""


    user_prompt = f"""

VIDEO TITLE:
{title}

SPEAKER MAP:

{speaker_context}

CURRENT CHUNK:
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

            "speaker_mentions": [],

            "chunk_summary": ai_text

        }


    return {

        "topics":
            result.get(
                "topics",
                []
            ),

        "important_points":
            result.get(
                "important_points",
                []
            ),

        "speaker_mentions":
            result.get(
                "speaker_mentions",
                []
            ),

        "chunk_summary":
            clean_text(
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
    speaker_data,
    chunk_results
):

    speaker_context = (
        speaker_map_text(
            speaker_data
        )
    )


    # --------------------------------------------------------
    # Build intermediate analysis
    # --------------------------------------------------------

    analysis_blocks = []


    for index, result in enumerate(
        chunk_results,
        start=1
    ):

        block = {

            "chunk": index,

            "topics":
                result.get(
                    "topics",
                    []
                ),

            "important_points":
                result.get(
                    "important_points",
                    []
                ),

            "speaker_mentions":
                result.get(
                    "speaker_mentions",
                    []
                ),

            "summary":
                result.get(
                    "chunk_summary",
                    ""
                )

        }


        analysis_blocks.append(
            block
        )


    analysis_text = json.dumps(
        analysis_blocks,
        ensure_ascii=False
    )


    system_prompt = """

You are the final editor of a long-form YouTube video
analysis.

You receive intermediate analyses from ALL parts of a
video.

Your task is to create one coherent final analysis.

IMPORTANT:

1. Use ONLY the supplied intermediate analyses.

2. Do not invent facts.

3. Do not add external knowledge.

4. Preserve important details from the entire video.

5. Do not focus only on the beginning.

6. Do not omit important later sections.

7. Speaker identities in the SPEAKER MAP are fixed.

8. Never swap speaker identities.

9. Do not create speaker identities that are not in
   the speaker map.

10. Do not claim that a person said something unless
    the supplied analysis supports it.

11. The final summary should be proportional to the
    amount and importance of information in the video.

12. Longer videos may have longer summaries.

13. Do NOT artificially limit the summary to a fixed
    number of sentences.

14. Key points should be dynamic:
    use as many as necessary to cover the important
    content. Do not force exactly five points.

15. Remove duplicate points.

16. Preserve chronology when chronology matters.

17. The English and Indonesian versions must communicate
    the same information.

Return ONLY valid JSON.

Use EXACTLY this structure:

{
  "en": {
    "summary": "Detailed but coherent summary.",
    "key_points": [
      "Important point 1",
      "Important point 2"
    ],
    "takeaways": "Overall conclusion and main takeaways."
  },
  "id": {
    "summary": "Ringkasan detail tetapi tetap koheren.",
    "key_points": [
      "Poin penting 1",
      "Poin penting 2"
    ],
    "takeaways": "Kesimpulan dan inti utama."
  }
}

Do not use Markdown.
Do not use ```json.
Return only the JSON object.
"""


    user_prompt = f"""

VIDEO TITLE:
{title}

TRANSCRIPT LANGUAGE:
{language}

SPEAKER MAP:

{speaker_context}

INTERMEDIATE ANALYSES FROM THE ENTIRE VIDEO:

{analysis_text}

Create the final analysis.

Make sure information from later chunks is also represented.

The video may be long, therefore the summary may also be
long when the content requires it.
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

                "takeaways": ""

            },

            "id": {

                "summary": "",

                "key_points": [],

                "takeaways": ""

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


    en_key_points = en.get(
        "key_points",
        []
    )

    id_key_points = id_data.get(
        "key_points",
        []
    )


    if not isinstance(
        en_key_points,
        list
    ):

        en_key_points = []


    if not isinstance(
        id_key_points,
        list
    ):

        id_key_points = []


    return {

        "en": {

            "summary":
                clean_text(
                    en.get(
                        "summary",
                        ""
                    )
                ),

            "key_points":
                [
                    clean_text(x)
                    for x in en_key_points
                    if clean_text(x)
                ],

            "takeaways":
                clean_text(
                    en.get(
                        "takeaways",
                        ""
                    )
                )

        },

        "id": {

            "summary":
                clean_text(
                    id_data.get(
                        "summary",
                        ""
                    )
                ),

            "key_points":
                [
                    clean_text(x)
                    for x in id_key_points
                    if clean_text(x)
                ],

            "takeaways":
                clean_text(
                    id_data.get(
                        "takeaways",
                        ""
                    )
                )

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

                "message":
                    "YouTube URL is required"

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

        transcript_result = (
            await get_transcript(
                url
            )
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


        # ====================================================
        # 4. VIDEO INFORMATION
        # ====================================================

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


        segments = normalize_segments(
            transcript_data.get(
                "transcript",
                []
            )
        )


        if not segments:

            return {

                "status": "error",

                "message":
                    "Transcript is empty"

            }


        # ====================================================
        # 5. BUILD COMPLETE TRANSCRIPT
        # ====================================================

        full_transcript = (
            build_full_transcript(
                segments
            )
        )


        # ====================================================
        # 6. SPEAKER IDENTIFICATION
        # ====================================================

        speaker_data = (
            await identify_speakers(

                title=video_title,

                author_name=metadata.get(
                    "author_name",
                    ""
                ),

                transcript=full_transcript

            )
        )


        # ====================================================
        # 7. BUILD CHUNKS
        # ====================================================

        chunks = build_chunks(
            segments
        )


        if not chunks:

            return {

                "status": "error",

                "message":
                    "Unable to create transcript chunks"

            }


        # ====================================================
        # 8. ANALYZE EACH CHUNK
        # ====================================================

        chunk_results = []


        for chunk in chunks:

            result = await analyze_chunk(

                title=video_title,

                speaker_data=speaker_data,

                chunk=chunk

            )


            chunk_results.append(
                result
            )


        # ====================================================
        # 9. FINAL SYNTHESIS
        # ====================================================

        ai_summary = await final_synthesis(

            title=video_title,

            language=language,

            speaker_data=speaker_data,

            chunk_results=chunk_results

        )


        # ====================================================
        # 10. RETURN
        # ====================================================

        return {

            "status": "success",

            "version": "2.0.0",

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

            "speaker_analysis":
                speaker_data,

            "processing": {

                "total_segments":
                    len(segments),

                "total_chunks":
                    len(chunks),

                "transcript_characters":
                    len(full_transcript)

            },

            "summary": ai_summary,

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
# WORKERS ENTRYPOINT
# ============================================================

Default = asgi.entrypoint(app)
