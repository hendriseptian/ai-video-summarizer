from pathlib import Path
import re

src = Path("/mnt/data/main_v2.py")
out = Path("/mnt/data/main_v3_consistent.py")

text = src.read_text(encoding="utf-8")

# 1) Add a strict cross-language consistency section to the main AI prompt.
anchor = """============================================================
OUTPUT FORMAT
============================================================"""
insert = r"""============================================================
CROSS-LANGUAGE CONSISTENCY LOCK
============================================================

CRITICAL RULE:

English and Indonesian are TWO LANGUAGE VERSIONS of ONE analysis.
They are NOT two independent analyses.

First determine ONE master analytical conclusion from the transcript.
Then express that SAME conclusion in both languages.

The following MUST be identical in meaning between "en" and "id":

- sentiment label
- sentiment conclusion/reason
- main issue
- key points and factual coverage
- media angle
- highlighted actors
- Pemprov Jawa Tengah position
- public opinion potential
- key messages
- communication risk level
- communication risk reasoning
- escalation potential
- recommendation types
- recommendation priorities
- critical analysis conclusions
- implications
- takeaways

The Indonesian version MUST NOT independently reinterpret the video.

Do NOT let translation change the analytical conclusion.

For controlled categorical fields, use exactly the same underlying
decision in both languages:

sentiment:
positive / negative / neutral

communication_risk.level:
low / medium / high

recommendations[].type:
amplification / clarification / counter_narrative /
media_engagement / monitoring

Only the language of the text should change.

For example:

EN:
"sentiment": {
  "label": "positive",
  "reason": "The reporting emphasizes..."
}

ID:
"sentiment": {
  "label": "positive",
  "reason": "Pemberitaan menekankan..."
}

NOT:

EN = positive
ID = neutral

Likewise, if EN recommends "amplification", ID must recommend
"amplification" with the Indonesian wording "amplifikasi".

If a fact appears in the English Key Points, preserve that fact
in the Indonesian Key Points unless there is a genuine reason
that the information cannot be represented naturally.

Keep important dates, locations, names, numbers, participants,
officials, actions, and developments consistent across languages.

Do not omit important factual details merely because the language
is different.

============================================================
OUTPUT FORMAT
============================================================"""
if anchor not in text:
    raise RuntimeError("Prompt anchor not found")
text = text.replace(anchor, insert, 1)

# 2) Strengthen the final quality control.
qc_anchor = """21. English and Indonesian convey the same meaning.
22. Summary, Key Points, Critical Analysis, Implications,
    and Takeaways are not repetitive copies."""
qc_replacement = """21. English and Indonesian convey the same meaning.
22. English and Indonesian are two language renderings of ONE master analysis.
23. Sentiment label MUST be identical between EN and ID.
24. Communication risk level MUST be identical between EN and ID.
25. Recommendation types MUST be identical between EN and ID.
26. Important facts, dates, numbers, actors, issues, and conclusions
    MUST NOT be selectively omitted or changed between languages.
27. Summary, Key Points, Critical Analysis, Implications,
    and Takeaways are not repetitive copies."""
if qc_anchor not in text:
    raise RuntimeError("QC anchor not found")
text = text.replace(qc_anchor, qc_replacement, 1)

# 3) Replace normalize_analysis with a consistency-locking implementation.
old = '''def normalize_analysis(data):
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
'''

new = r'''def synchronize_language_analysis(result):
    """
    Enforce analytical consistency between EN and ID.

    EN and ID remain separate language blocks, but controlled
    analytical decisions are locked to the same master result.
    This prevents translation from changing sentiment, risk,
    or recommendation strategy.
    """

    if not isinstance(result, dict):
        return result

    en = result.get("en")
    id_block = result.get("id")

    if not isinstance(en, dict) or not isinstance(id_block, dict):
        return result

    # --------------------------------------------------------
    # SENTIMENT LABEL
    # --------------------------------------------------------
    en_sentiment = en.get("sentiment", {})
    id_sentiment = id_block.get("sentiment", {})

    if not isinstance(en_sentiment, dict):
        en_sentiment = {}

    if not isinstance(id_sentiment, dict):
        id_sentiment = {}

    canonical_sentiment = (
        str(
            en_sentiment.get("label", "neutral")
        )
        .strip()
        .lower()
    )

    if canonical_sentiment not in {
        "positive",
        "negative",
        "neutral"
    }:
        canonical_sentiment = "neutral"

    id_sentiment["label"] = canonical_sentiment

    # Keep the Indonesian reason generated by the model,
    # but never allow it to alter the categorical decision.
    if not id_sentiment.get("reason"):
        id_sentiment["reason"] = en_sentiment.get(
            "reason",
            ""
        )

    en["sentiment"] = en_sentiment
    id_block["sentiment"] = id_sentiment

    # --------------------------------------------------------
    # COMMUNICATION RISK LEVEL
    # --------------------------------------------------------
    en_risk = en.get("communication_risk", {})
    id_risk = id_block.get("communication_risk", {})

    if not isinstance(en_risk, dict):
        en_risk = {}

    if not isinstance(id_risk, dict):
        id_risk = {}

    canonical_risk = (
        str(
            en_risk.get("level", "low")
        )
        .strip()
        .lower()
    )

    if canonical_risk not in {
        "low",
        "medium",
        "high"
    }:
        canonical_risk = "low"

    id_risk["level"] = canonical_risk

    if not id_risk.get("reason"):
        id_risk["reason"] = en_risk.get(
            "reason",
            ""
        )

    if not id_risk.get("escalation_potential"):
        id_risk["escalation_potential"] = en_risk.get(
            "escalation_potential",
            ""
        )

    en["communication_risk"] = en_risk
    id_block["communication_risk"] = id_risk

    # --------------------------------------------------------
    # RECOMMENDATION TYPES
    # --------------------------------------------------------
    en_recommendations = en.get(
        "recommendations",
        []
    )
    id_recommendations = id_block.get(
        "recommendations",
        []
    )

    if not isinstance(en_recommendations, list):
        en_recommendations = []

    if not isinstance(id_recommendations, list):
        id_recommendations = []

    allowed_types = {
        "amplification",
        "clarification",
        "counter_narrative",
        "media_engagement",
        "monitoring"
    }

    canonical_types = []

    for item in en_recommendations:
        if not isinstance(item, dict):
            continue

        recommendation_type = str(
            item.get("type", "")
        ).strip().lower()

        if recommendation_type in allowed_types:
            canonical_types.append(
                recommendation_type
            )

    # Remove duplicates while preserving order.
    canonical_types = list(
        dict.fromkeys(
            canonical_types
        )
    )

    # Rebuild ID recommendations so strategic types cannot diverge.
    id_by_type = {}

    for item in id_recommendations:
        if not isinstance(item, dict):
            continue

        recommendation_type = str(
            item.get("type", "")
        ).strip().lower()

        if recommendation_type in allowed_types:
            id_by_type[recommendation_type] = item

    synced_id_recommendations = []

    for recommendation_type in canonical_types:

        id_item = id_by_type.get(
            recommendation_type,
            {}
        )

        en_item = next(
            (
                item
                for item in en_recommendations
                if isinstance(item, dict)
                and str(
                    item.get("type", "")
                ).strip().lower()
                == recommendation_type
            ),
            {}
        )

        synced_id_recommendations.append({
            "type": recommendation_type,
            "action": normalize_text(
                id_item.get(
                    "action",
                    ""
                )
            ) or normalize_text(
                en_item.get(
                    "action",
                    ""
                )
            ),
            "reason": normalize_text(
                id_item.get(
                    "reason",
                    ""
                )
            ) or normalize_text(
                en_item.get(
                    "reason",
                    ""
                )
            )
        })

    id_block["recommendations"] = (
        synced_id_recommendations
    )

    result["en"] = en
    result["id"] = id_block

    return result


def synchronize_factual_coverage(result):
    """
    Keep the two language versions structurally aligned.

    This does not copy English prose into Indonesian. It only
    ensures that important list sections are populated from the
    master EN result if the model accidentally leaves the ID
    version empty.
    """

    if not isinstance(result, dict):
        return result

    en = result.get("en")
    id_block = result.get("id")

    if not isinstance(en, dict) or not isinstance(id_block, dict):
        return result

    list_fields = [
        "key_points",
        "critical_analysis",
        "implications",
        "takeaways"
    ]

    for field_name in list_fields:

        en_items = en.get(
            field_name,
            []
        )

        id_items = id_block.get(
            field_name,
            []
        )

        if not isinstance(en_items, list):
            en_items = []

        if not isinstance(id_items, list):
            id_items = []

        # If ID is accidentally empty, use the EN content as a
        # fallback rather than returning an incomplete analysis.
        # The normal case remains the model-generated Indonesian text.
        if en_items and not id_items:
            id_block[field_name] = en_items.copy()

    # Main issue fallback if one language is accidentally empty.
    en_issue = en.get(
        "main_issue",
        {}
    )

    id_issue = id_block.get(
        "main_issue",
        {}
    )

    if not isinstance(en_issue, dict):
        en_issue = {}

    if not isinstance(id_issue, dict):
        id_issue = {}

    if not id_issue.get("title"):
        id_issue["title"] = en_issue.get(
            "title",
            ""
        )

    if not id_issue.get("description"):
        id_issue["description"] = en_issue.get(
            "description",
            ""
        )

    id_block["main_issue"] = id_issue

    result["en"] = en
    result["id"] = id_block

    return result


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

    result = enforce_inference_labels(
        result
    )

    result = synchronize_language_analysis(
        result
    )

    result = synchronize_factual_coverage(
        result
    )

    return result
'''

if old not in text:
    raise RuntimeError("normalize_analysis block not found")
text = text.replace(old, new, 1)

# 4) Add a second safety instruction to the final prompts so the model
#    treats EN as the master analytical result and ID as its translation.
prompt_anchor = """Create the final professional video analysis from
the following transcript."""
prompt_replacement = """Create the final professional video analysis from
the following transcript.

IMPORTANT: Produce ONE master analysis first. Treat the English analysis
as the master analytical decision set. The Indonesian analysis must be
a faithful Indonesian rendering of that same analysis, not a separate
interpretation. Do not change sentiment, risk level, recommendation
types, facts, numbers, actors, issues, or conclusions between languages."""
# Replace only the first occurrence in the single-pass prompt, and the
# corresponding chunk final prompt separately below.
text = text.replace(prompt_anchor, prompt_replacement, 1)

chunk_anchor = """Create the final professional video analysis from the following
factual extraction notes."""
chunk_replacement = """Create the final professional video analysis from the following
factual extraction notes.

IMPORTANT: Produce ONE master analysis first. Treat the English analysis
as the master analytical decision set. The Indonesian analysis must be
a faithful Indonesian rendering of that same analysis, not a separate
interpretation. Do not change sentiment, risk level, recommendation
types, facts, numbers, actors, issues, or conclusions between languages."""
if chunk_anchor in text:
    text = text.replace(chunk_anchor, chunk_replacement, 1)

# 5) Bump version.
text = text.replace(
    'version="8.0.0"',
    'version="8.1.0"',
    1
)
text = text.replace(
    '"version":\n                "8.0.0"',
    '"version":\n                "8.1.0"',
    1
)

out.write_text(text, encoding="utf-8")

print(f"Created: {out}")
print("Changes:")
print("- Added strict EN/ID master-analysis consistency rules.")
print("- Locked sentiment label EN/ID.")
print("- Locked communication risk level EN/ID.")
print("- Locked recommendation types EN/ID.")
print("- Added factual-coverage fallback for empty ID sections.")
print("- Updated API version to 8.1.0.")
