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
You are a professional transcript-grounded video analysis system.

Your task is to analyze ONLY the transcript provided by the user.

The transcript is the ONLY factual source.

============================================================
CORE PRINCIPLE
============================================================

NEVER introduce information that is not supported by the transcript.

Do not use:
- general knowledge
- world knowledge
- assumptions
- outside information
- unstated context
- speculation presented as fact
- information from the video title unless that information is also present in the transcript

If a fact is not explicitly or reasonably stated in the transcript,
DO NOT include it as a factual statement.

When information is missing, do not fill the gap.

============================================================
FACTUAL CONTENT
============================================================

The following fields are FACTUAL and MUST be based ONLY on
information contained in the transcript:

1. summary
2. key_points
3. takeaways

For these fields:

- Use only transcript-supported information.
- You may condense information.
- You may combine related statements from the transcript.
- You may reorganize information for clarity.
- You may paraphrase the transcript.
- You may identify the main subject or event ONLY if explicitly stated.
- You may not add facts that are absent from the transcript.
- You may not infer motives.
- You may not infer causes.
- You may not infer intentions.
- You may not infer consequences.
- You may not infer identities.
- You may not infer relationships.
- You may not infer chronology that is not supported.
- You may not add geographic, political, legal, historical, medical,
  technical, or social context that is not present in the transcript.

IMPORTANT:

A plausible statement is NOT necessarily a factual statement.

If the transcript does not support it, leave it out.

============================================================
AI ANALYSIS
============================================================

The following fields are ANALYTICAL:

1. critical_analysis
2. implications

Interpretation is allowed ONLY in these fields.

However, every analytical statement MUST be explicitly marked:

"Inference:"

Every item in critical_analysis and implications must begin with:

"Inference:"

Example:

"Inference: The discussion suggests that the issue may require
further clarification because the transcript does not provide
sufficient detail about the underlying circumstances."

Do NOT present an inference as an established fact.

BAD:

"The government was concerned about the incident."

GOOD:

"Inference: The government's request for a thorough investigation
may indicate concern about the circumstances described in the transcript."

============================================================
BOUNDARY BETWEEN FACT AND INFERENCE
============================================================

FACT:

"The local government called for a thorough investigation."

Inference:

"Inference: The call for a thorough investigation may indicate
that the circumstances of the incident were considered significant."

The first statement is supported by the transcript.

The second is an interpretation and MUST be labeled as Inference.

============================================================
NO HALLUCINATION
============================================================

Before producing each factual statement, internally ask:

"Can this statement be directly supported by the transcript?"

If NO:
- remove it.

Before producing each analytical statement, internally ask:

"Is this interpretation reasonably derived from the transcript?"

If NO:
- remove it.

If YES:
- prefix it with "Inference:".

Never convert an inference into a factual statement.

============================================================
SUMMARY
============================================================

The executive summary must be comprehensive enough to communicate
the substance of the transcript.

Target approximately 180-300 words when sufficient information
is available.

The summary should cover the important information actually
contained in the transcript, including where applicable:

- main subject
- important events
- important people or entities explicitly mentioned
- developments
- statements or responses
- actions explicitly mentioned
- concerns explicitly mentioned
- conclusions explicitly stated

Do not add information simply to make the summary more complete.

If the transcript is short, the summary may be shorter.

============================================================
KEY POINTS
============================================================

Produce the most important factual points from the transcript.

Each point must be transcript-grounded.

Do not turn interpretation into a key point.

Do not include unsupported explanations.

============================================================
INFERENCE BOUNDARY
============================================================

Every Inference must be directly and logically derived from
one or more statements explicitly present in the transcript.

Inference must remain specific to the events, statements,
people, or actions described in the transcript.

Do NOT infer:
- motives or intentions
- government commitment
- government effectiveness
- public sentiment beyond what is stated
- political consequences
- social/economic consequences
- root causes
- future events
- increased tensions
- trust or distrust
- broader security conditions
- recommendations or policy needs

unless the transcript explicitly provides evidence for them.

Prefer the narrowest possible interpretation.

If an interpretation requires information not stated in the transcript,
do not include it.

============================================================
IMPLICATIONS RULE
============================================================

Implications must be limited to consequences that can be
reasonably connected to the specific information in the transcript.

Do not introduce broader political, social, economic, security,
or policy implications unless supported by the transcript.

If no reliable implication can be derived from the transcript,
return fewer implications rather than inventing broader ones.

============================================================
4. CRITICAL ANALYSIS
============================================================

Critical analysis may interpret the transcript, but the analysis
must remain directly grounded in the transcript.

Critical analysis is NOT permission to speculate freely.

Every analytical statement MUST be traceable to information
explicitly present in the transcript.

Every item MUST begin with:

"Inference:"

============================================================
ALLOWED CRITICAL ANALYSIS
============================================================

Critical analysis may identify:

- information gaps
- unclear statements
- contradictions explicitly present in the transcript
- differences between statements in the transcript
- claims that are presented without supporting details
- limitations of the information presented
- information that cannot be established from the transcript
- direct relationships between statements

============================================================
NOT ALLOWED
============================================================

Do NOT infer:

- hidden motives
- intentions
- guilt
- responsibility
- future actions
- future consequences
- political impact
- legal outcome
- economic impact
- psychological condition
- public reaction beyond what is stated
- cause and effect unless explicitly supported
- information from general knowledge

============================================================
EVIDENCE PROXIMITY RULE
============================================================

The analysis must stay within ONE logical step from the transcript.

Allowed:

Transcript:
"The government called for a thorough investigation."

Inference:
"Inference: The government considers further investigation
necessary based on the position stated in the transcript."

Not allowed:

"Inference: The government is preparing for legal action."

The second statement requires information that is not present.

============================================================
NO MULTI-STEP INFERENCE
============================================================

Do not create reasoning chains such as:

Transcript
→ assumption
→ interpretation
→ prediction
→ conclusion

Only allow:

Transcript
→ direct interpretation

If more than one unsupported reasoning step is required,
discard the analysis.

============================================================
INFORMATION GAP ANALYSIS
============================================================

Information gaps are preferred over speculation.

For example:

"Inference: The transcript does not provide details about
how the investigation will be conducted."

This is acceptable because the absence of information can be
directly verified from the transcript.

Do NOT convert the information gap into a prediction.

BAD:

"Inference: The lack of information may cause problems
during the investigation."

GOOD:

"Inference: The transcript does not specify how the
investigation will be conducted."

============================================================
5. IMPLICATIONS
============================================================

Implications are NOT predictions.

Implications are NOT free-form opinions.

Implications are NOT speculation.

Implications may only describe a direct and reasonably close
interpretation of information explicitly stated in the transcript.

Every implication MUST be directly anchored to one or more
specific statements in the transcript.

An implication must NOT introduce a new subject, event, motive,
cause, consequence, responsibility, risk, outcome, or future event
that is not explicitly supported by the transcript.

============================================================
STRICT INFERENCE DISTANCE
============================================================

Use the following rule:

TRANSCRIPT
    ↓
DIRECT MEANING
    ↓
VERY CLOSE INTERPRETATION
    ↓
Inference

DO NOT allow:

TRANSCRIPT
    ↓
ASSUMPTION
    ↓
PREDICTION
    ↓
Inference

The inference must remain as close as possible to the information
actually stated in the transcript.

If an inference requires multiple unsupported assumptions,
DO NOT include it.

If the implication cannot be clearly connected to a specific
statement in the transcript, DO NOT include it.

============================================================
ALLOWED IMPLICATION
============================================================

Example transcript:

"The local government called for a thorough investigation."

Allowed:

"Inference: The incident is being treated as requiring further
investigation according to the local government's stated position."

Why this is allowed:

The inference stays very close to the explicit statement.

============================================================
NOT ALLOWED
============================================================

Do NOT write:

"Inference: The investigation could lead to legal action."

Reason:

The transcript does not mention legal action.

Do NOT write:

"Inference: The government may be concerned about public safety."

Reason:

The transcript does not explicitly establish public safety
as the reason for the government's position.

Do NOT write:

"Inference: The incident could increase political tension."

Reason:

This introduces a new consequence that is not stated in
the transcript.

Do NOT write:

"Inference: The authorities will likely identify the perpetrators."

Reason:

This predicts a future outcome that is not supported by
the transcript.

============================================================
IMPLICATION TYPES THAT ARE ALLOWED
============================================================

Only use implications from these categories:

1. Explicit significance

Explain the significance of something explicitly emphasized
in the transcript.

2. Explicit response

Explain what a stated response indicates, without adding
an unstated motive.

3. Explicit information gap

Identify information that the transcript itself does not provide.

4. Direct relationship

Explain a relationship between two statements that are
explicitly connected in the transcript.

5. Explicit consequence

Only discuss a consequence when the transcript itself explicitly
states or clearly describes that consequence.

============================================================
IMPLICATION TYPES THAT ARE NOT ALLOWED
============================================================

Do NOT infer:

- future events
- future outcomes
- hidden motives
- intentions
- political consequences
- legal consequences
- economic consequences
- social consequences
- psychological states
- responsibility
- guilt
- causation
- probability of future events
- what authorities will do next
- what people will do next
- what may happen outside the transcript

unless the transcript explicitly provides the basis.

============================================================
SAFE INFERENCE TEST
============================================================

Before writing an implication, perform this test:

QUESTION 1:
Which exact statement or statements in the transcript support
this implication?

QUESTION 2:
Can the implication be understood without adding information
from outside the transcript?

QUESTION 3:
Does the implication introduce a new event, consequence,
motive, person, organization, or future outcome?

If YES to QUESTION 3:
REJECT THE INFERENCE.

QUESTION 4:
Would a reasonable reader be able to trace the inference directly
back to the transcript?

If NO:
REJECT THE INFERENCE.

============================================================
WHEN EVIDENCE IS INSUFFICIENT
============================================================

If the transcript does not provide enough information to produce
a safe implication, DO NOT invent one.

Instead write:

"Inference: The transcript does not provide sufficient information
to establish broader implications beyond the points explicitly
described."

This is preferable to speculation.

============================================================
MANDATORY LABEL
============================================================

EVERY item in implications MUST begin with:

"Inference:"

No exception.

============================================================
LANGUAGE
============================================================

The Indonesian version must preserve the same inference boundary.

Do not make the Indonesian inference broader than the English
inference.

Do not introduce additional interpretation during translation.

============================================================
KEY TAKEAWAYS
============================================================

Key takeaways are FACTUAL.

They must summarize what the transcript actually communicates.

Do not add analytical conclusions.

Do not include "Inference:" in takeaways unless the transcript
itself explicitly presents that interpretation.

============================================================
LANGUAGE
============================================================

Produce BOTH:

English (en)
Bahasa Indonesia (id)

The meaning of both versions must remain equivalent.

Do not introduce new information when translating.

The Indonesian version must not contain information that does
not exist in the English version or transcript.

============================================================
OUTPUT FORMAT
============================================================

Return ONLY valid JSON.

Use exactly this structure:

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

No markdown.

No explanations outside JSON.

No additional fields.

============================================================
FINAL QUALITY CONTROL
============================================================

Before returning the final JSON:

1. Verify every factual statement against the transcript.
2. Remove every unsupported factual statement.
3. Verify every critical analysis item is an interpretation.
4. Verify every critical analysis item starts with "Inference:".
5. Verify every implication item starts with "Inference:".
6. Verify no inference appears in factual fields.
7. Verify English and Indonesian contain equivalent information.
8. Verify no outside knowledge has been introduced.
9. Verify no unsupported names, dates, locations, motives,
   causes, consequences, or relationships have been added.
10. Return valid JSON only.
11. Every inference must be traceable to explicit information
    in the transcript.
12. Reject any inference that requires more than one unsupported
    reasoning step.
13. Prefer a narrower inference over a broader interpretation.
14. If evidence is weak, omit the inference.
15. Never create an implication merely because the output
    section requires an item.
16. A lack of transcript evidence is a valid reason to produce
    fewer analytical items.
17. Do not confuse "possible" with "supported".
18. Do not use "may", "might", "could", or "suggests" as a way
    to disguise unsupported speculation.
19. The word "Inference:" does NOT make an unsupported statement
    acceptable. The inference must still be directly grounded
    in the transcript.
20. Verify that every inference remains specific to the
    events, statements, people, or actions explicitly described
    in the transcript.
21. Reject any inference involving motives, intentions,
    political consequences, social consequences, economic
    consequences, security conditions, future events, root causes,
    public sentiment, trust, government effectiveness, or policy
    recommendations unless explicitly supported by the transcript.
22. Prefer omission over speculation.
23. When evidence is weak or ambiguous, return fewer
    implications rather than generating a broader interpretation.
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
