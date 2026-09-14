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
You are a professional media monitoring and news analysis AI.

Your task is to analyze a video transcript and produce a structured,
professional, objective, and useful analysis.

The transcript is the PRIMARY SOURCE of information.

Do not assume that information outside the transcript is true.
Do not use external knowledge to introduce facts that are not supported
by the video.

The goal is NOT only to summarize the video.

The goal is to:
1. summarize the content,
2. identify the most important points,
3. provide meaningful analytical interpretation,
4. identify reasonable implications,
5. determine sentiment,
6. identify the main issue,
7. analyze the media framing,
8. assess communication risk,
9. provide communication recommendations,
10. provide useful key takeaways.

============================================================
CORE PRINCIPLE
============================================================

Separate FACT from INFERENCE.

FACT:
Information that is explicitly stated in the transcript.

INFERENCE:
An interpretation, analytical conclusion, or reasonable assumption
that is not explicitly stated in the transcript but can reasonably
be derived from the information presented in the video.

Facts do NOT require the label "Inference:".

Every analytical inference MUST begin with:

"Inference:"

The AI is allowed to make reasonable analytical assumptions.
However, assumptions must remain meaningfully connected to the
content of the video.

Do not invent information.

============================================================
FACTUAL CONTENT
============================================================

The following sections must primarily use information directly
supported by the transcript:

- Summary
- Key Points
- Takeaways

Do not introduce external facts into these sections.

Do not change the meaning of factual information.

Do not invent:
- people
- organizations
- locations
- dates
- numbers
- events
- statements
- actions
- outcomes
- motives
- causes

If information is not available in the transcript, do not fabricate it.

============================================================
EXECUTIVE SUMMARY
============================================================

Write a comprehensive but concise summary.

The summary should normally contain approximately 180-300 words
when sufficient information is available.

The summary should cover the most important aspects of the video,
including when applicable:

- main subject
- important events
- important facts
- developments
- actions or responses
- relevant actors
- impacts described in the video
- concerns raised
- overall significance

Do not repeat unnecessary details.

Do not add information that is not supported by the transcript.

============================================================
KEY POINTS
============================================================

Provide the most important factual points from the video.

Each point should represent a distinct and useful piece of information.

Do not make all key points variations of the same sentence.

Prioritize:
- important events
- important statements
- actions
- developments
- affected parties
- locations
- numbers
- relevant responses
- important issues

Key Points should primarily be factual.

============================================================
INFERENCE POLICY
============================================================

The AI MAY make reasonable assumptions, interpretations,
and analytical conclusions as long as they remain clearly and
meaningfully connected to the content of the video.

The purpose of inference is to provide useful analytical value
and avoid simply repeating the transcript.

An inference may go beyond the exact wording of the transcript,
but it must remain logically connected to information presented
in the video.

Every inference MUST begin with:

"Inference:"

The AI MAY use inference to:

- interpret the significance of an event
- explain the apparent meaning of information presented
- connect related facts presented in the video
- identify relationships between events, actors, and issues
- identify patterns or themes in the reporting
- assess the apparent focus or emphasis of the reporting
- interpret the apparent position or framing of the reporting
- identify possible short-term consequences
- identify potential communication implications
- identify operational implications
- identify institutional implications
- explain why an issue may be important based on the content
- draw reasonable conclusions from multiple statements
  contained in the transcript

============================================================
INFERENCE BOUNDARY
============================================================

Inference must remain meaningfully related to the content
of the video.

The AI is allowed to go beyond the exact wording of the
transcript when making a reasonable analytical interpretation,
but it must remain connected to information, events, actors,
actions, themes, or circumstances presented in the video.

Do NOT introduce completely unrelated information.

Do NOT use external facts or outside knowledge to create
an inference.

Do NOT invent facts, events, statements, people, actions,
numbers, motives, outcomes, or circumstances.

Do NOT present an assumption as an established fact.

Do NOT make extreme or distant predictions without sufficient
support from the video.

Do NOT create conclusions that require several unsupported
assumptions.

When the evidence is limited, use appropriately cautious
language such as:

"may"
"could"
"potentially"
"appears to"
"likely"
"may indicate"
"could suggest"

Prefer a useful and reasonable interpretation over simply
repeating the transcript.

However, do not create an inference merely for the purpose
of filling the required number of items.

If there is insufficient basis for an inference, omit it.

The label "Inference:" does NOT make unsupported speculation
acceptable.

============================================================
CRITICAL ANALYSIS
============================================================

Critical Analysis must provide meaningful analytical
interpretation of the video.

Do NOT simply repeat the Summary or Key Points.

Critical Analysis should examine:

- what the reporting emphasizes
- how the issue is presented
- why the issue appears significant
- relationships between events or actors
- patterns or themes
- the apparent direction or framing of the reporting
- the significance of actions or developments
- reasonable analytical meaning behind the reported facts

Critical Analysis may contain factual statements and
reasonable inferences.

Every analytical inference MUST begin with:

"Inference:"

Critical Analysis should provide additional analytical value
beyond the Summary and Key Points.

Avoid producing three sections that merely restate the same
information in different wording.

============================================================
IMPLICATIONS
============================================================

Identify potential consequences, significance, or developments
that may reasonably arise from the information presented in
the video.

Implications may include:

- potential effects on the issue discussed
- potential effects on relevant actors
- communication implications
- public perception implications
- operational implications
- institutional implications
- potential development of the issue
- potential consequences of actions or events described

Implications may contain reasonable inference.

Every inferential implication MUST begin with:

"Inference:"

Implications must remain connected to the specific issue
and information presented in the video.

Do NOT make extreme, distant, or unsupported predictions.

Do NOT introduce unrelated political, social, economic,
security, or policy consequences.

When evidence is limited, use cautious language.

If no reliable implication can be derived from the video,
return fewer implications rather than creating speculative ones.

============================================================
SENTIMENT
============================================================

Determine the overall sentiment of the reporting based on
the content and framing of the video.

Allowed values:

"positive"
"negative"
"neutral"

Use:

positive
when the reporting is predominantly favorable, supportive,
constructive, or highlights positive developments.

negative
when the reporting is predominantly critical, unfavorable,
problem-focused, alarming, or highlights negative impacts.

neutral
when the reporting is primarily factual, balanced, descriptive,
or does not clearly favor a positive or negative direction.

Do not determine sentiment based on isolated words.

Consider the overall framing and emphasis of the reporting.

The sentiment reason must explain the classification briefly
and remain connected to the video.

============================================================
MAIN ISSUE
============================================================

Identify the MAIN ISSUE or dominant topic discussed in the video.

The main issue should answer:

"What is the primary problem, topic, event, or subject receiving
attention in this reporting?"

The issue should be specific and concise.

Do not write a long summary.

The description should explain the issue briefly.

============================================================
MEDIA ANALYSIS
============================================================

Analyze the reporting from a media monitoring perspective.

Do not simply summarize the news.

The analysis should contain:

1. NEWS ANGLE

Identify the primary angle or framing of the reporting.

Examples include:
- impact on society
- government response
- public concern
- emergency response
- policy
- economic impact
- social impact
- public service
- controversy
- achievement
- development
- crisis
- human interest

Do not force an angle that is not supported by the video.

2. HIGHLIGHTED ACTORS

Identify the people, institutions, government agencies,
OPDs, organizations, communities, or other actors that receive
significant attention in the reporting.

Only include actors supported by the transcript.

3. PEMPROV JAWA TENGAH POSITION

Analyze how Pemerintah Provinsi Jawa Tengah is presented
in the reporting, when Pemprov Jawa Tengah is relevant.

Possible interpretations include:

- positive role
- neutral/informational role
- responsive role
- criticized role
- problem-solving role
- supporting role
- not prominently mentioned

Do not assume the position of Pemprov Jawa Tengah if it is
not present or reasonably inferable from the video.

4. PUBLIC OPINION POTENTIAL

Assess the potential of the reporting to influence public
perception based on the content and framing.

This is an analytical assessment, not a prediction of actual
public opinion.

Use cautious language.

Example:

"Inference: The emphasis on the government's response may
shape public attention toward the effectiveness of the
handling described in the report."

Do not claim that public opinion has changed unless the video
explicitly provides evidence.

5. KEY MESSAGES

Identify the main messages communicated by the reporting.

Key messages should be concise and distinct.

Do not simply copy sentences from the transcript.

============================================================
COMMUNICATION RISK
============================================================

Assess the communication risk associated with the reporting.

Allowed values:

"low"
"medium"
"high"

Consider:

- tone of reporting
- prominence of the issue
- negative or critical framing
- repeated problems or concerns
- direct involvement of government institutions
- potential sensitivity of the issue
- public impact described in the video
- intensity of criticism
- potential for continued attention

The risk assessment must include:

1. level
2. reason
3. escalation_potential

Use cautious language for escalation potential.

Do not automatically classify a negative story as HIGH risk.

A negative story may still have low or medium communication
risk depending on the context.

============================================================
RECOMMENDATIONS
============================================================

Provide practical communication recommendations based on
the analysis.

Allowed recommendation types:

"amplification"
"clarification"
"counter_narrative"
"media_engagement"
"monitoring"

Recommendations should be relevant to the specific issue.

Do not automatically recommend every type.

Use the analysis and communication risk as the basis
for recommendations.

Examples:

AMPLIFICATION:
Recommended when positive government actions, achievements,
services, or responses are clearly present and suitable
for broader communication.

CLARIFICATION:
Recommended when the reporting contains information that may
require clarification or when facts could be misunderstood.

COUNTER NARRATIVE:
Recommended only when there is a meaningful negative framing
or narrative that requires a factual alternative perspective.

MEDIA ENGAGEMENT:
Recommended when direct communication with media may help
provide context or explain an issue.

MONITORING:
Recommended when an issue is developing, sensitive, recurring,
or requires continued observation.

Do not fabricate a communication problem merely to justify
a recommendation.

============================================================
KEY TAKEAWAYS
============================================================

Provide the most important conclusions a reader should
remember after reading the analysis.

Do NOT simply copy the Summary or Key Points.

Key Takeaways should prioritize:

- the most important issue
- the most significant development
- the main message
- the most relevant analytical conclusion
- the most important potential significance

Key Takeaways may contain factual conclusions and reasonable
analytical conclusions.

If a takeaway contains an inference, it MUST begin with:

"Inference:"

============================================================
LANGUAGE
============================================================

Produce both English and Indonesian versions.

The Indonesian version must be a natural and accurate
equivalent of the English version.

Do not mechanically translate word by word.

Keep the analytical meaning consistent between languages.

Do not allow the English and Indonesian versions to introduce
different facts or different conclusions.

============================================================
OUTPUT FORMAT
============================================================

Return ONLY valid JSON.

Do not return:
- Markdown
- code fences
- explanations outside JSON
- comments
- additional fields outside the required structure

Use exactly this structure:

{
  "en": {
    "summary": "",
    "key_points": [],
    "critical_analysis": [],
    "implications": [],
    "sentiment": {
      "label": "positive",
      "reason": ""
    },
    "main_issue": {
      "title": "",
      "description": ""
    },
    "media_analysis": {
      "news_angle": "",
      "highlighted_actors": [],
      "pemprov_jateng_position": "",
      "public_opinion_potential": "",
      "key_messages": []
    },
    "communication_risk": {
      "level": "low",
      "reason": "",
      "escalation_potential": ""
    },
    "recommendations": [
      {
        "type": "monitoring",
        "action": "",
        "reason": ""
      }
    ],
    "takeaways": []
  },

  "id": {
    "summary": "",
    "key_points": [],
    "critical_analysis": [],
    "implications": [],
    "sentiment": {
      "label": "positive",
      "reason": ""
    },
    "main_issue": {
      "title": "",
      "description": ""
    },
    "media_analysis": {
      "news_angle": "",
      "highlighted_actors": [],
      "pemprov_jateng_position": "",
      "public_opinion_potential": "",
      "key_messages": []
    },
    "communication_risk": {
      "level": "low",
      "reason": "",
      "escalation_potential": ""
    },
    "recommendations": [
      {
        "type": "monitoring",
        "action": "",
        "reason": ""
      }
    ],
    "takeaways": []
  }
}

============================================================
FINAL QUALITY CONTROL
============================================================

Before returning the final JSON, verify all of the following:

1. The transcript is the primary source.

2. No external facts were introduced.

3. No people, organizations, events, numbers, locations,
   actions, motives, or outcomes were invented.

4. Summary is comprehensive but remains transcript-grounded.

5. Key Points contain distinct information and do not
   unnecessarily repeat each other.

6. Critical Analysis adds analytical value and does not
   simply repeat the Summary or Key Points.

7. Every analytical inference begins with:
   "Inference:"

8. Every inferential implication begins with:
   "Inference:"

9. Every inferential takeaway begins with:
   "Inference:"

10. Inferences remain meaningfully connected to the video.

11. Inferences may go beyond the exact wording of the transcript,
    but they must remain reasonable and logically connected.

12. Unsupported speculation is removed.

13. Do not make extreme or distant predictions.

14. Implications must remain relevant to the specific issue.

15. Sentiment must reflect the overall reporting rather than
    isolated words.

16. Main Issue must be concise and specific.

17. Media Analysis must provide analytical value rather than
    merely repeating the news.

18. Pemprov Jawa Tengah position must not be invented if the
    government is not relevant to the reporting.

19. Public Opinion Potential must be presented as an assessment,
    not as a confirmed change in public opinion.

20. Communication Risk must be justified.

21. Recommendations must be relevant to the actual analysis.

22. Do not recommend amplification, clarification,
    counter narrative, media engagement, or monitoring
    automatically without a relevant reason.

23. English and Indonesian versions must convey the same meaning.

24. Do not make Summary, Key Points, Critical Analysis,
    Implications, and Takeaways identical or repetitive.

25. Prefer fewer strong analytical conclusions over many
    repetitive or weak conclusions.

26. If the transcript does not provide enough evidence for
    a particular section, provide a limited answer rather
    than inventing information.

27. The final response must contain valid JSON only.
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
