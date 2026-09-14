from pathlib import Path
import re
import py_compile

src = Path("/mnt/data/main_fixed_cloudflare.py")
out = Path("/mnt/data/main_v2.py")

text = src.read_text(encoding="utf-8")

# ------------------------------------------------------------
# 1) Version
# ------------------------------------------------------------
text = text.replace(
    'version="7.1.0"',
    'version="8.0.0"',
    1
)
text = text.replace(
    '"7.1.0"',
    '"8.0.0"'
)

# ------------------------------------------------------------
# 2) Replace SYSTEM_PROMPT
# ------------------------------------------------------------
new_system_prompt = r'''SYSTEM_PROMPT = """
You are a professional media monitoring and news analysis AI.

Analyze ONLY the supplied video transcript.

The transcript is the PRIMARY SOURCE of information.

Do not use outside knowledge to introduce facts that are not supported
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

Do not identify speakers.

Return ONLY valid JSON.

============================================================
CORE PRINCIPLE
============================================================

Separate FACT from INFERENCE.

FACT:
Information explicitly stated in the transcript.

INFERENCE:
An interpretation, analytical conclusion, or reasonable assumption
that is not explicitly stated but can reasonably be derived from
the information presented in the video.

Facts do NOT require the label "Inference:".

Every analytical inference MUST begin with:

"Inference:"

The AI MAY make reasonable assumptions and interpretations.
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

Do not introduce external facts.

Do not change the meaning of factual information.

Do not invent people, organizations, locations, dates, numbers,
events, statements, actions, outcomes, motives, or causes.

============================================================
EXECUTIVE SUMMARY
============================================================

Write a comprehensive executive summary.

Normally write approximately 180-300 words when sufficient
information is available.

Cover when supported:
- main subject
- context
- important events and facts
- important statements
- responses or actions
- relevant actors
- impacts or concerns
- overall significance or conclusion

Write coherent professional prose in 1-3 paragraphs.

Do not use bullet points or headings inside the summary.

Do not repeat the transcript sentence by sentence.

============================================================
KEY POINTS
============================================================

Provide 5-8 important points.

Each point should normally contain 1-3 sentences.

Each point must contain distinct and useful information.

Prioritize:
- important events
- statements
- actions
- developments
- affected parties
- locations
- numbers
- responses
- important issues

Use information supported by the transcript.

============================================================
INFERENCE POLICY
============================================================

The AI MAY make reasonable assumptions, interpretations, and
analytical conclusions when they are clearly and meaningfully
connected to the video.

The purpose of inference is to provide useful analytical value
and avoid simply repeating the transcript.

An inference may go beyond the exact wording of the transcript,
but it must remain logically connected to information presented
in the video.

Every inference MUST begin with:

"Inference:"

The AI MAY use inference to:
- interpret significance
- explain apparent meaning
- connect related facts
- identify relationships between events, actors, and issues
- identify patterns or themes
- assess reporting emphasis
- interpret apparent framing
- identify possible short-term consequences
- identify communication implications
- identify operational or institutional implications
- explain why an issue may be important
- draw reasonable conclusions from multiple transcript statements

============================================================
INFERENCE BOUNDARY
============================================================

Inference must remain meaningfully related to the content
of the video.

The AI is allowed to go beyond exact wording when making
a reasonable analytical interpretation, but it must remain
connected to information, events, actors, actions, themes,
or circumstances presented in the video.

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

When evidence is limited, use cautious language such as:
"may", "could", "potentially", "appears to", "likely",
"may indicate", or "could suggest".

Prefer a useful and reasonable interpretation over simply
repeating the transcript.

Do not create an inference merely to fill a required number
of items.

If there is insufficient basis for an inference, omit it.

The label "Inference:" does NOT make unsupported speculation
acceptable.

============================================================
CRITICAL ANALYSIS
============================================================

Provide 3-5 meaningful analytical observations.

Do NOT simply repeat the Summary or Key Points.

Focus on:
- significance
- reporting emphasis
- framing
- relationships between facts or actors
- patterns or themes
- important considerations
- limitations or information gaps
- concerns supported by the video

Critical Analysis may contain factual statements and reasonable
inferences.

Every analytical inference MUST begin with:

"Inference:"

Prioritize analytical value over repetition.

============================================================
IMPLICATIONS
============================================================

Provide 2-4 meaningful implications.

Identify potential consequences, significance, or developments
that may reasonably arise from the information presented.

Implications may include:
- potential effects on the issue
- potential effects on relevant actors
- communication implications
- public perception implications
- operational implications
- institutional implications
- potential development of the issue

Implications may contain reasonable inference.

Every inferential implication MUST begin with:

"Inference:"

Do NOT make extreme, distant, or unsupported predictions.

Do NOT introduce unrelated political, social, economic, security,
or policy consequences.

Use cautious language when appropriate.

If no reliable implication can be derived, return fewer items.

============================================================
SENTIMENT
============================================================

Determine the overall sentiment of the reporting.

Allowed values only:
"positive"
"negative"
"neutral"

positive:
The reporting is predominantly favorable, supportive,
constructive, or highlights positive developments.

negative:
The reporting is predominantly critical, unfavorable,
problem-focused, alarming, or highlights negative impacts.

neutral:
The reporting is primarily factual, balanced, descriptive,
or does not clearly favor a positive or negative direction.

Do not classify sentiment based on isolated words.

Consider the overall framing and emphasis.

Provide a short reason based on the video.

============================================================
MAIN ISSUE
============================================================

Identify the MAIN ISSUE or dominant topic.

Answer:

"What is the primary problem, topic, event, or subject
receiving attention in this reporting?"

Keep the title concise and specific.

The description should briefly explain the issue.

============================================================
MEDIA ANALYSIS
============================================================

Analyze the reporting from a media monitoring perspective.

Do NOT simply summarize the news.

Provide:

1. NEWS ANGLE

Identify the primary angle or framing.

Possible examples:
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

Do not force an angle that is not supported.

2. HIGHLIGHTED ACTORS

Identify people, institutions, government agencies,
OPDs, organizations, communities, or other actors
receiving significant attention.

Only include actors supported by the transcript.

3. PEMPROV JAWA TENGAH POSITION

Analyze how Pemerintah Provinsi Jawa Tengah is presented,
when relevant.

Possible interpretations:
- positive role
- neutral/informational role
- responsive role
- criticized role
- problem-solving role
- supporting role
- not prominently mentioned

Do not invent a position if Pemprov Jawa Tengah is not relevant.

4. PUBLIC OPINION POTENTIAL

Assess the potential of the reporting to influence public
perception based on its content and framing.

This is an analytical assessment, not a claim that public
opinion has actually changed.

Use cautious language.

5. KEY MESSAGES

Identify the main messages communicated by the reporting.

Keep messages concise and distinct.

============================================================
COMMUNICATION RISK
============================================================

Assess communication risk.

Allowed values only:
"low"
"medium"
"high"

Consider:
- reporting tone
- prominence of the issue
- negative or critical framing
- repeated problems or concerns
- direct government involvement
- issue sensitivity
- public impact described
- intensity of criticism
- potential for continued attention

Do NOT automatically classify a negative story as high risk.

Provide:
1. level
2. reason
3. escalation_potential

Use cautious language for escalation potential.

============================================================
RECOMMENDATIONS
============================================================

Provide practical communication recommendations based on
the analysis.

Allowed types only:
"amplification"
"clarification"
"counter_narrative"
"media_engagement"
"monitoring"

Use only recommendations relevant to the actual issue.

Do not automatically recommend every type.

AMPLIFICATION:
Use when positive actions, achievements, services,
or responses are present and suitable for broader communication.

CLARIFICATION:
Use when information may be misunderstood or requires factual
clarification.

COUNTER NARRATIVE:
Use only when a meaningful negative framing or narrative
requires a factual alternative perspective.

MEDIA ENGAGEMENT:
Use when direct communication with media may help provide
context or explanation.

MONITORING:
Use when an issue is developing, sensitive, recurring,
or requires continued observation.

Do not fabricate a communication problem merely to justify
a recommendation.

============================================================
KEY TAKEAWAYS
============================================================

Provide 2-4 important conclusions a reader should remember.

Do NOT simply copy the Summary or Key Points.

Prioritize:
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

The Indonesian version must be natural, professional,
and suitable for an office analytical report.

Do not translate word-for-word when unnatural.

English and Indonesian must convey the same facts and conclusions.

============================================================
OUTPUT FORMAT
============================================================

Return ONLY valid JSON.

Do not return Markdown, code fences, comments, or explanations.

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

Before returning JSON:

1. Transcript remains the primary source.
2. No external facts were introduced.
3. No facts, people, organizations, numbers, events,
   motives, or outcomes were invented.
4. Summary is comprehensive and transcript-grounded.
5. Key Points are distinct.
6. Critical Analysis adds analytical value.
7. Implications add potential consequences or significance.
8. Every analytical inference begins with "Inference:".
9. Every inferential implication begins with "Inference:".
10. Every inferential takeaway begins with "Inference:".
11. Inferences remain meaningfully connected to the video.
12. Unsupported speculation is removed.
13. No extreme or distant predictions.
14. Sentiment reflects overall reporting.
15. Main Issue is concise and specific.
16. Media Analysis does not merely repeat the news.
17. Pemprov Jawa Tengah position is not invented.
18. Public Opinion Potential is an assessment, not a confirmed
    change in public opinion.
19. Communication Risk is justified.
20. Recommendations are relevant to the actual analysis.
21. English and Indonesian convey the same meaning.
22. Summary, Key Points, Critical Analysis, Implications,
    and Takeaways are not repetitive copies.
23. Prefer fewer strong conclusions over many weak conclusions.
24. If evidence is insufficient, omit or reduce the section.
25. Return valid JSON only.
"""
'''
text = re.sub(
    r'SYSTEM_PROMPT = """.*?"""\n\n\n# ============================================================\n# CHUNK PROMPT',
    new_system_prompt + '\n\n# ============================================================\n# CHUNK PROMPT',
    text,
    count=1,
    flags=re.S
)

# ------------------------------------------------------------
# 3) Add chunk-specific system prompt and monitoring prompt
# ------------------------------------------------------------
anchor = '# ============================================================\n# CHUNK PROMPT'
insert = r'''# ============================================================
# CHUNK SYSTEM PROMPT
# ============================================================

CHUNK_SYSTEM_PROMPT = """
You are a transcript extraction assistant.

Extract only important factual information from the supplied
transcript section.

Do not analyze, speculate, infer, or add outside knowledge.

Do not identify speakers.

Return ONLY valid JSON with this structure:

{
  "facts": [],
  "events": [],
  "actors": [],
  "issues": [],
  "locations": [],
  "numbers": [],
  "responses": [],
  "concerns": [],
  "developments": []
}
"""


# ============================================================
# MONITORING REPORT SYSTEM PROMPT
# ============================================================

MONITORING_SYSTEM_PROMPT = """
You are a professional media monitoring and communication
analysis AI.

Your task is to aggregate multiple previously analyzed
news/video items into ONE professional media monitoring report.

IMPORTANT:

Use ONLY the supplied analysis records.

Do not use outside knowledge.

Do not invent facts, exposure counts, stations, actors,
issues, locations, sentiment, or events.

The analysis records are the source dataset.

The purpose is to identify patterns across multiple reports,
not to repeat each individual report.

============================================================
REPORT OBJECTIVE
============================================================

Produce a professional monitoring report covering:

- total exposure
- number of news items
- number of TV stations
- Pemprov Jawa Tengah exposure
- sentiment distribution
- dominant issues
- affected regions
- highlighted actors
- media angles
- Pemprov Jawa Tengah position
- public opinion potential
- key messages
- communication risk
- news trend
- recommendations
- conclusion

============================================================
AGGREGATION RULES
============================================================

Count and group information across all supplied records.

Dominant issues should be based on recurrence and prominence.

Do not merge unrelated issues merely because they are similar.

Affected regions should only include regions explicitly present
in the supplied records.

Highlighted actors should reflect actors repeatedly or
prominently appearing across the records.

Media angles should identify the dominant framing across
the reporting set.

============================================================
SENTIMENT
============================================================

Use the sentiment labels already assigned to the individual
records.

Allowed values:

"positive"
"negative"
"neutral"

Calculate the distribution from the supplied records.

Do not invent counts.

Overall sentiment should reflect the distribution and
dominant reporting tone.

============================================================
PEMPROV JAWA TENGAH
============================================================

Assess how Pemprov Jawa Tengah is positioned across the
reporting set.

Possible positions include:
- positive
- neutral
- responsive
- criticized
- mixed
- limited visibility
- not prominently mentioned

Do not invent involvement.

============================================================
PUBLIC OPINION POTENTIAL
============================================================

Assess the potential for the reporting to shape public
attention or perception.

This is an analytical assessment.

Do not claim that public opinion actually changed unless
the supplied records explicitly support that conclusion.

Use cautious language.

============================================================
COMMUNICATION RISK
============================================================

Assess overall communication risk:

"low"
"medium"
"high"

Consider:
- volume
- sentiment
- issue sensitivity
- prominence
- criticism
- government involvement
- repeated concerns
- potential continuation of coverage

Do not automatically classify a negative issue as high risk.

Provide:
- level
- reason
- escalation_potential

============================================================
NEWS TREND
============================================================

Identify how the dominant issue or coverage develops across
the reporting set when the supplied records provide enough
information.

Do not force a three-stage trend if the data does not support it.

Use the smallest useful number of stages.

============================================================
RECOMMENDATIONS
============================================================

Recommendations must be based on the aggregated analysis.

Allowed types:

"amplification"
"clarification"
"counter_narrative"
"media_engagement"
"monitoring"

Do not automatically include all types.

Recommendations should be practical and relevant.

============================================================
OUTPUT
============================================================

Return ONLY valid JSON.

Use exactly this structure:

{
  "report": {
    "title": "",
    "period": {
      "start": "",
      "end": ""
    }
  },
  "statistics": {
    "total_exposure": 0,
    "total_news": 0,
    "total_tv_stations": 0,
    "pemprov_jateng_exposure": 0
  },
  "sentiment": {
    "overall": "neutral",
    "distribution": {
      "positive": 0,
      "negative": 0,
      "neutral": 0
    }
  },
  "dominant_issues": [],
  "affected_regions": [],
  "media_analysis": {
    "dominant_angle": "",
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
  "news_trend": {
    "stages": []
  },
  "recommendations": [],
  "conclusion": "",
  "sources": []
}
"""

'''
text = text.replace(anchor, insert + anchor, 1)

# ------------------------------------------------------------
# 4) Replace CHUNK_PROMPT
# ------------------------------------------------------------
text = re.sub(
    r'CHUNK_PROMPT = """.*?"""\n\n\n# ============================================================\n# ERROR RESPONSE',
    r'''CHUNK_PROMPT = """
Extract the important factual information from this transcript
section for later synthesis.

Return JSON with:
{
  "facts": [],
  "events": [],
  "actors": [],
  "issues": [],
  "locations": [],
  "numbers": [],
  "responses": [],
  "concerns": [],
  "developments": []
}

Use ONLY information contained in the transcript section.

Do not invent facts.

TRANSCRIPT SECTION:
"""


# ============================================================
# ERROR RESPONSE''',
    text,
    count=1,
    flags=re.S
)

# ------------------------------------------------------------
# 5) Replace normalization block
# ------------------------------------------------------------
new_norm = r'''# ============================================================
# NORMALIZE TEXT
# ============================================================

def normalize_text(value):
    if value is None:
        return ""

    if isinstance(value, str):
        return value.strip()

    if isinstance(value, list):
        parts = []
        for item in value:
            text = normalize_text(item)
            if text:
                parts.append(text)
        return " ".join(parts).strip()

    if isinstance(value, dict):
        preferred_keys = [
            "issue",
            "reason",
            "evidence",
            "observation",
            "analysis",
            "text",
            "content",
            "description",
            "action",
            "escalation_potential",
            "news_angle"
        ]

        parts = []

        for key in preferred_keys:
            if key in value:
                text = normalize_text(value[key])
                if text:
                    parts.append(text)

        if parts:
            return " ".join(parts).strip()

        values = []
        for item in value.values():
            text = normalize_text(item)
            if text:
                values.append(text)

        return " ".join(values).strip()

    return str(value).strip()


# ============================================================
# NORMALIZE LIST
# ============================================================

def normalize_list(value):
    if value is None:
        return []

    if isinstance(value, list):
        output = []

        for item in value:
            text = normalize_text(item)

            if text:
                output.append(text)

        return output

    text = normalize_text(value)

    if text:
        return [text]

    return []


# ============================================================
# NORMALIZE RECOMMENDATIONS
# ============================================================

def normalize_recommendations(value):
    if not isinstance(value, list):
        return []

    allowed_types = {
        "amplification",
        "clarification",
        "counter_narrative",
        "media_engagement",
        "monitoring"
    }

    output = []

    for item in value:
        if isinstance(item, dict):
            recommendation_type = str(
                item.get("type", "monitoring")
            ).strip().lower()

            if recommendation_type not in allowed_types:
                recommendation_type = "monitoring"

            action = normalize_text(
                item.get("action", "")
            )

            reason = normalize_text(
                item.get("reason", "")
            )

            if action:
                output.append({
                    "type": recommendation_type,
                    "action": action,
                    "reason": reason
                })

        else:
            action = normalize_text(item)

            if action:
                output.append({
                    "type": "monitoring",
                    "action": action,
                    "reason": ""
                })

    return output


# ============================================================
# NORMALIZE SENTIMENT
# ============================================================

def normalize_sentiment(value):
    if isinstance(value, dict):
        label = str(
            value.get("label", "neutral")
        ).strip().lower()

        reason = normalize_text(
            value.get("reason", "")
        )
    else:
        label = str(
            value or "neutral"
        ).strip().lower()

        reason = ""

    if label not in {
        "positive",
        "negative",
        "neutral"
    }:
        label = "neutral"

    return {
        "label": label,
        "reason": reason
    }


# ============================================================
# NORMALIZE COMMUNICATION RISK
# ============================================================

def normalize_communication_risk(value):
    if not isinstance(value, dict):
        value = {}

    level = str(
        value.get("level", "low")
    ).strip().lower()

    if level not in {
        "low",
        "medium",
        "high"
    }:
        level = "low"

    return {
        "level": level,
        "reason": normalize_text(
            value.get("reason", "")
        ),
        "escalation_potential": normalize_text(
            value.get("escalation_potential", "")
        )
    }


# ============================================================
# NORMALIZE MEDIA ANALYSIS
# ============================================================

def normalize_media_analysis(value):
    if not isinstance(value, dict):
        value = {}

    return {
        "news_angle": normalize_text(
            value.get("news_angle", "")
        ),

        "highlighted_actors": normalize_list(
            value.get("highlighted_actors", [])
        ),

        "pemprov_jateng_position": normalize_text(
            value.get(
                "pemprov_jateng_position",
                ""
            )
        ),

        "public_opinion_potential": normalize_text(
            value.get(
                "public_opinion_potential",
                ""
            )
        ),

        "key_messages": normalize_list(
            value.get("key_messages", [])
        )
    }


# ============================================================
# ENFORCE INFERENCE LABELS
# ============================================================

def enforce_inference_labels(analysis):
    if not isinstance(analysis, dict):
        return analysis

    for language in ["en", "id"]:
        section = analysis.get(language)

        if not isinstance(section, dict):
            continue

        for field in [
            "critical_analysis",
            "implications"
        ]:
            items = section.get(field, [])

            if not isinstance(items, list):
                continue

            normalized = []

            for item in items:
                text = normalize_text(item)

                if not text:
                    continue

                if not text.lower().startswith(
                    "inference:"
                ):
                    text = "Inference: " + text

                normalized.append(text)

            section[field] = normalized

    return analysis


# ============================================================
# NORMALIZE LANGUAGE BLOCK
# ============================================================

def normalize_language_block(block):
    if not isinstance(block, dict):
        block = {}

    result = {
        "summary": normalize_text(
            block.get("summary", "")
        ),

        "key_points": normalize_list(
            block.get("key_points", [])
        ),

        "critical_analysis": normalize_list(
            block.get("critical_analysis", [])
        ),

        "implications": normalize_list(
            block.get("implications", [])
        ),

        "sentiment": normalize_sentiment(
            block.get("sentiment", {})
        ),

        "main_issue": {
            "title": normalize_text(
                (
                    block.get(
                        "main_issue",
                        {}
                    )
                    if isinstance(
                        block.get(
                            "main_issue",
                            {}
                        ),
                        dict
                    )
                    else {}
                ).get("title", "")
            ),

            "description": normalize_text(
                (
                    block.get(
                        "main_issue",
                        {}
                    )
                    if isinstance(
                        block.get(
                            "main_issue",
                            {}
                        ),
                        dict
                    )
                    else {}
                ).get("description", "")
            )
        },

        "media_analysis": normalize_media_analysis(
            block.get("media_analysis", {})
        ),

        "communication_risk": normalize_communication_risk(
            block.get("communication_risk", {})
        ),

        "recommendations": normalize_recommendations(
            block.get("recommendations", [])
        ),

        "takeaways": normalize_list(
            block.get("takeaways", [])
        )
    }

    return result


# ============================================================
# NORMALIZE FINAL ANALYSIS
# ============================================================

def normalize_analysis(data):
    if not isinstance(data, dict):
        data = {}

    result = {
        "en": normalize_language_block(
            data.get("en", {})
        ),
        "id": normalize_language_block(
            data.get("id", {})
        )
    }

    return enforce_inference_labels(result)


# ============================================================
# NORMALIZE MONITORING REPORT
# ============================================================

def normalize_monitoring_report(data):
    if not isinstance(data, dict):
        data = {}

    report = data.get("report", {})
    if not isinstance(report, dict):
        report = {}

    statistics = data.get("statistics", {})
    if not isinstance(statistics, dict):
        statistics = {}

    sentiment = data.get("sentiment", {})
    if not isinstance(sentiment, dict):
        sentiment = {}

    distribution = sentiment.get("distribution", {})
    if not isinstance(distribution, dict):
        distribution = {}

    dominant_issues = data.get(
        "dominant_issues",
        []
    )
    if not isinstance(dominant_issues, list):
        dominant_issues = []

    normalized_issues = []

    for item in dominant_issues:
        if not isinstance(item, dict):
            continue

        try:
            exposure_count = int(
                item.get("exposure_count", 0)
            )
        except Exception:
            exposure_count = 0

        try:
            percentage = float(
                item.get("percentage", 0)
            )
        except Exception:
            percentage = 0.0

        normalized_issues.append({
            "issue": normalize_text(
                item.get("issue", "")
            ),
            "exposure_count": max(
                exposure_count,
                0
            ),
            "percentage": max(
                percentage,
                0.0
            ),
            "description": normalize_text(
                item.get("description", "")
            )
        })

    affected_regions = data.get(
        "affected_regions",
        []
    )
    if not isinstance(affected_regions, list):
        affected_regions = []

    normalized_regions = []

    for item in affected_regions:
        if not isinstance(item, dict):
            continue

        try:
            count = int(
                item.get("exposure_count", 0)
            )
        except Exception:
            count = 0

        normalized_regions.append({
            "region": normalize_text(
                item.get("region", "")
            ),
            "exposure_count": max(
                count,
                0
            ),
            "issues": normalize_list(
                item.get("issues", [])
            )
        })

    recommendations = normalize_recommendations(
        data.get("recommendations", [])
    )

    sources = data.get("sources", [])
    if not isinstance(sources, list):
        sources = []

    normalized_sources = []

    for item in sources:
        if isinstance(item, dict):
            try:
                count = int(
                    item.get("exposure_count", 0)
                )
            except Exception:
                count = 0

            normalized_sources.append({
                "station": normalize_text(
                    item.get("station", "")
                ),
                "exposure_count": max(
                    count,
                    0
                )
            })

    overall = str(
        sentiment.get(
            "overall",
            "neutral"
        )
    ).strip().lower()

    if overall not in {
        "positive",
        "negative",
        "neutral"
    }:
        overall = "neutral"

    return {
        "report": {
            "title": normalize_text(
                report.get("title", "")
            ),
            "period": {
                "start": normalize_text(
                    (
                        report.get(
                            "period",
                            {}
                        )
                        if isinstance(
                            report.get(
                                "period",
                                {}
                            ),
                            dict
                        )
                        else {}
                    ).get("start", "")
                ),
                "end": normalize_text(
                    (
                        report.get(
                            "period",
                            {}
                        )
                        if isinstance(
                            report.get(
                                "period",
                                {}
                            ),
                            dict
                        )
                        else {}
                    ).get("end", "")
                )
            }
        },

        "statistics": {
            "total_exposure": max(
                int(
                    statistics.get(
                        "total_exposure",
                        0
                    ) or 0
                ),
                0
            ),
            "total_news": max(
                int(
                    statistics.get(
                        "total_news",
                        0
                    ) or 0
                ),
                0
            ),
            "total_tv_stations": max(
                int(
                    statistics.get(
                        "total_tv_stations",
                        0
                    ) or 0
                ),
                0
            ),
            "pemprov_jateng_exposure": max(
                int(
                    statistics.get(
                        "pemprov_jateng_exposure",
                        0
                    ) or 0
                ),
                0
            )
        },

        "sentiment": {
            "overall": overall,
            "distribution": {
                "positive": max(
                    int(
                        distribution.get(
                            "positive",
                            0
                        ) or 0
                    ),
                    0
                ),
                "negative": max(
                    int(
                        distribution.get(
                            "negative",
                            0
                        ) or 0
                    ),
                    0
                ),
                "neutral": max(
                    int(
                        distribution.get(
                            "neutral",
                            0
                        ) or 0
                    ),
                    0
                )
            }
        },

        "dominant_issues": normalized_issues,
        "affected_regions": normalized_regions,

        "media_analysis": normalize_media_analysis(
            data.get(
                "media_analysis",
                {}
            )
        ),

        "communication_risk": normalize_communication_risk(
            data.get(
                "communication_risk",
                {}
            )
        ),

        "news_trend": {
            "stages": normalize_list(
                (
                    data.get(
                        "news_trend",
                        {}
                    )
                    if isinstance(
                        data.get(
                            "news_trend",
                            {}
                        ),
                        dict
                    )
                    else {}
                ).get("stages", [])
            )
        },

        "recommendations": recommendations,

        "conclusion": normalize_text(
            data.get("conclusion", "")
        ),

        "sources": normalized_sources
    }


'''
text = re.sub(
    r'# ============================================================\n# NORMALIZE TEXT.*?# ============================================================\n# FETCH TRANSCRIPT',
    new_norm + '# ============================================================\n# FETCH TRANSCRIPT',
    text,
    count=1,
    flags=re.S
)

# ------------------------------------------------------------
# 6) Use chunk-specific system prompt
# ------------------------------------------------------------
text = text.replace(
    'result = await run_ai(\n            SYSTEM_PROMPT,\n            prompt,\n            2500\n        )',
    'result = await run_ai(\n            CHUNK_SYSTEM_PROMPT,\n            prompt,\n            2500\n        )',
    1
)

# ------------------------------------------------------------
# 7) Replace large-transcript final prompt wording
# ------------------------------------------------------------
text = text.replace(
    'Create the final professional report from the following\nanalysis notes.',
    'Create the final professional video analysis from the following\nfactual extraction notes.',
    1
)

# ------------------------------------------------------------
# 8) Add monitoring endpoint before ROOT
# ------------------------------------------------------------
monitoring_endpoint = r'''
# ============================================================
# MONITORING REPORT ENDPOINT
# ============================================================

@app.post("/monitoring-report")
async def monitoring_report(
    request: Request
):

    try:

        body = await request.json()

        if not isinstance(body, dict):
            return error_response(
                "Request body must be a JSON object.",
                "invalid_request",
                400
            )

        analyses = (
            body.get("analyses")
            or body.get("items")
            or []
        )

        if not isinstance(analyses, list):
            return error_response(
                "analyses must be an array.",
                "validation_error",
                400
            )

        if not analyses:
            return error_response(
                "At least one analysis record is required.",
                "validation_error",
                400
            )

        if len(analyses) > 100:
            return error_response(
                "Maximum 100 analysis records per monitoring report.",
                "validation_error",
                400
            )

        period = body.get("period", {})
        if not isinstance(period, dict):
            period = {}

        start_date = str(
            period.get("start", "")
        ).strip()

        end_date = str(
            period.get("end", "")
        ).strip()

        # ----------------------------------------------------
        # BUILD AGGREGATION DATA
        # ----------------------------------------------------

        records = []

        for index, item in enumerate(
            analyses,
            start=1
        ):

            if not isinstance(item, dict):
                continue

            video = item.get("video", {})
            if not isinstance(video, dict):
                video = {}

            ai = item.get("ai", {})
            if not isinstance(ai, dict):
                ai = {}

            # Prefer Indonesian analysis for the monitoring layer.
            # Fall back to English if Indonesian is unavailable.
            language_data = ai.get("id")

            if not isinstance(
                language_data,
                dict
            ):
                language_data = ai.get(
                    "en",
                    {}
                )

            if not isinstance(
                language_data,
                dict
            ):
                language_data = {}

            records.append({
                "record_id": index,

                "video": {
                    "id": normalize_text(
                        video.get("id", "")
                    ),
                    "title": normalize_text(
                        video.get("title", "")
                    ),
                    "url": normalize_text(
                        video.get("url", "")
                    ),
                    "station": normalize_text(
                        video.get("station", "")
                    ),
                    "source": normalize_text(
                        video.get("source", "")
                    ),
                    "publication_date": normalize_text(
                        video.get(
                            "publication_date",
                            ""
                        )
                    )
                },

                "analysis": language_data
            })

        if not records:
            return error_response(
                "No valid analysis records were supplied.",
                "validation_error",
                400
            )

        # ----------------------------------------------------
        # DETERMINISTIC STATISTICS
        # ----------------------------------------------------

        total_news = len(records)

        stations = []

        positive = 0
        negative = 0
        neutral = 0

        pemprov_exposure = 0

        for record in records:

            video = record["video"]
            analysis = record["analysis"]

            station = video.get(
                "station",
                ""
            ).strip()

            if station:
                stations.append(
                    station
                )

            sentiment = analysis.get(
                "sentiment",
                {}
            )

            if isinstance(
                sentiment,
                dict
            ):
                label = str(
                    sentiment.get(
                        "label",
                        "neutral"
                    )
                ).strip().lower()
            else:
                label = "neutral"

            if label == "positive":
                positive += 1
            elif label == "negative":
                negative += 1
            else:
                neutral += 1

            media_analysis = analysis.get(
                "media_analysis",
                {}
            )

            if not isinstance(
                media_analysis,
                dict
            ):
                media_analysis = {}

            pemprov_position = normalize_text(
                media_analysis.get(
                    "pemprov_jateng_position",
                    ""
                )
            ).lower()

            if (
                pemprov_position
                and
                "not prominently mentioned"
                not in pemprov_position
                and
                "tidak disebut"
                not in pemprov_position
                and
                "tidak menonjol"
                not in pemprov_position
            ):
                pemprov_exposure += 1

        unique_stations = sorted(
            set(
                item
                for item in stations
                if item
            )
        )

        # ----------------------------------------------------
        # BUILD AI AGGREGATION INPUT
        # ----------------------------------------------------

        aggregation_payload = {
            "period": {
                "start": start_date,
                "end": end_date
            },

            "deterministic_statistics": {
                "total_news": total_news,
                "total_exposure": total_news,
                "total_tv_stations": len(
                    unique_stations
                ),
                "pemprov_jateng_exposure": pemprov_exposure,

                "sentiment_distribution": {
                    "positive": positive,
                    "negative": negative,
                    "neutral": neutral
                },

                "stations": unique_stations
            },

            "records": records
        }

        aggregation_text = json.dumps(
            aggregation_payload,
            ensure_ascii=False
        )

        if len(aggregation_text) > MAX_FINAL_CONTEXT_CHARS:
            aggregation_text = aggregation_text[
                :MAX_FINAL_CONTEXT_CHARS
            ]

        prompt = """
Create the final professional media monitoring report
from the supplied analysis records.

Use the deterministic statistics as authoritative counts
for total news, total exposure, TV stations, and sentiment.

Do not change deterministic counts.

Use the supplied individual analysis records to determine:
- dominant issues
- affected regions
- media angles
- highlighted actors
- Pemprov Jawa Tengah position
- public opinion potential
- key messages
- communication risk
- news trend
- recommendations
- conclusion

Return ONLY valid JSON.

PERIOD:
""" + json.dumps(
            {
                "start": start_date,
                "end": end_date
            },
            ensure_ascii=False
        ) + """

AGGREGATION DATA:

""" + aggregation_text

        result = await run_ai(
            MONITORING_SYSTEM_PROMPT,
            prompt,
            5000
        )

        report = normalize_monitoring_report(
            parse_ai_json(result)
        )

        # Force authoritative deterministic statistics.
        report["report"]["period"]["start"] = start_date
        report["report"]["period"]["end"] = end_date

        report["statistics"]["total_news"] = total_news
        report["statistics"]["total_exposure"] = total_news
        report["statistics"]["total_tv_stations"] = len(
            unique_stations
        )
        report["statistics"]["pemprov_jateng_exposure"] = (
            pemprov_exposure
        )

        report["sentiment"]["distribution"] = {
            "positive": positive,
            "negative": negative,
            "neutral": neutral
        }

        sentiment_counts = {
            "positive": positive,
            "negative": negative,
            "neutral": neutral
        }

        report["sentiment"]["overall"] = max(
            sentiment_counts,
            key=sentiment_counts.get
        )

        # Build deterministic source list when station metadata exists.
        station_counts = {}

        for station in stations:
            station_counts[station] = (
                station_counts.get(
                    station,
                    0
                ) + 1
            )

        report["sources"] = [
            {
                "station": station,
                "exposure_count": count
            }
            for station, count
            in sorted(
                station_counts.items(),
                key=lambda item: (
                    -item[1],
                    item[0]
                )
            )
        ]

        return {
            "status": "success",
            "report": report,
            "processing": {
                "total_records": total_news,
                "total_tv_stations": len(
                    unique_stations
                ),
                "sentiment_distribution": {
                    "positive": positive,
                    "negative": negative,
                    "neutral": neutral
                }
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


'''
text = text.replace(
    '# ============================================================\n# ROOT',
    monitoring_endpoint + '# ============================================================\n# ROOT',
    1
)

# ------------------------------------------------------------
# 9) Add optional metadata to /analyze response
# ------------------------------------------------------------
# Capture metadata from request body.
needle = '''        video_id = extract_video_id(
            normalized_url
        )

        if not video_id:

            return error_response(
                "Could not extract YouTube video ID.",
                "validation_error",
                400
            )
'''
replacement = '''        video_id = extract_video_id(
            normalized_url
        )

        if not video_id:

            return error_response(
                "Could not extract YouTube video ID.",
                "validation_error",
                400
            )

        # Optional media-monitoring metadata.
        # Existing frontend requests remain fully compatible.
        station = str(
            body.get("station", "")
            or body.get("tv_station", "")
            or ""
        ).strip()

        source = str(
            body.get("source", "")
            or ""
        ).strip()

        publication_date = str(
            body.get("publication_date", "")
            or body.get("date", "")
            or ""
        ).strip()
'''
text = text.replace(needle, replacement, 1)

# Replace video response block to include metadata.
old_video = '''            "video": {
                "id":
                    video_id,

                "url":
                    normalized_url
            },
'''
new_video = '''            "video": {
                "id":
                    video_id,

                "url":
                    normalized_url,

                "title":
                    transcript_data[
                        "title"
                    ],

                "station":
                    station,

                "source":
                    source,

                "publication_date":
                    publication_date
            },
'''
text = text.replace(old_video, new_video, 1)

# ------------------------------------------------------------
# 10) Save and compile
# ------------------------------------------------------------
out.write_text(text, encoding="utf-8")

py_compile.compile(
    str(out),
    doraise=True
)

print(f"V2 created successfully: {out}")
print(f"Lines: {len(text.splitlines())}")
print("Syntax check: PASSED")
