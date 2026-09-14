from pathlib import Path
import re

src = Path("/mnt/data/script_current.txt")
out = Path("/mnt/data/script_fixed_id_recommendation.js")
text = src.read_text(encoding="utf-8")

# Replace the existing recommendation renderer with a language-aware version.
start = text.find("function recommendationCard(")
if start == -1:
    raise RuntimeError("recommendationCard() not found")

# Find the next section after recommendationCard.
marker = "\n/* ============================================================\n   TEXT CARD"
end = text.find(marker, start)
if end == -1:
    raise RuntimeError("End of recommendationCard section not found")

new_func = r'''function recommendationCard(
    value
) {

    if (
        value === null ||
        value === undefined ||
        value === ""
    ) {
        return "";
    }

    /*
     * Recommendation strategy is controlled by the backend.
     * The type is language-neutral; only the displayed label changes.
     */
    const typeLabels = {
        amplification: currentLanguage === "id"
            ? "Amplifikasi"
            : "Amplification",

        amplification_media: currentLanguage === "id"
            ? "Amplifikasi Media"
            : "Media Amplification",

        clarification: currentLanguage === "id"
            ? "Klarifikasi"
            : "Clarification",

        counter_narrative: currentLanguage === "id"
            ? "Counter Narrative"
            : "Counter Narrative",

        media_engagement: currentLanguage === "id"
            ? "Engagement Media"
            : "Media Engagement",

        monitoring: currentLanguage === "id"
            ? "Monitoring Lanjutan"
            : "Continued Monitoring",

        continued_monitoring: currentLanguage === "id"
            ? "Monitoring Lanjutan"
            : "Continued Monitoring",

        monitoring_lanjutan: currentLanguage === "id"
            ? "Monitoring Lanjutan"
            : "Continued Monitoring",

        follow_up_monitoring: currentLanguage === "id"
            ? "Monitoring Lanjutan"
            : "Continued Monitoring"
    };

    const labels = currentLanguage === "id"
        ? {
            type: "Tipe",
            action: "Tindakan",
            reason: "Alasan",
            recommendation: "Rekomendasi"
        }
        : {
            type: "Type",
            action: "Action",
            reason: "Reason",
            recommendation: "Recommendation"
        };

    function normalizeType(type) {
        return String(
            type === null ||
            type === undefined
                ? ""
                : type
        )
            .trim()
            .toLowerCase()
            .replace(/\s+/g, "_")
            .replace(/-/g, "_");
    }

    function renderRecommendationItem(item) {

        if (
            !item ||
            typeof item !== "object"
        ) {
            return "";
        }

        const rawType =
            item.type ||
            item.Type ||
            item.TYPE ||
            "";

        const type =
            normalizeType(
                rawType
            );

        const displayedType =
            typeLabels[type] ||
            String(
                rawType || "-"
            );

        const action =
            item.action ||
            item.Action ||
            item.ACTION ||
            item.aksi ||
            "";

        const reason =
            item.reason ||
            item.Reason ||
            item.REASON ||
            item.alasan ||
            "";

        return `
            <div class="recommendation-item">
                <div class="recommendation-field">
                    <strong>
                        ${escapeHTML(labels.type)}
                    </strong>
                    <span>
                        ${escapeHTML(displayedType)}
                    </span>
                </div>

                ${
                    action
                        ? `
                            <div class="recommendation-field">
                                <strong>
                                    ${escapeHTML(labels.action)}
                                </strong>
                                <span>
                                    ${escapeHTML(
                                        renderValue(action)
                                    )}
                                </span>
                            </div>
                        `
                        : ""
                }

                ${
                    reason
                        ? `
                            <div class="recommendation-field">
                                <strong>
                                    ${escapeHTML(labels.reason)}
                                </strong>
                                <span>
                                    ${escapeHTML(
                                        renderValue(reason)
                                    )}
                                </span>
                            </div>
                        `
                        : ""
                }
            </div>
        `;
    }

    let html = "";

    if (Array.isArray(value)) {

        html = value
            .map(
                renderRecommendationItem
            )
            .join("");

    } else if (
        typeof value === "object"
    ) {

        /*
         * Backend normally returns:
         * recommendations: [
         *   {
         *      type,
         *      action,
         *      reason
         *   }
         * ]
         *
         * Support a single object as a fallback.
         */
        html =
            renderRecommendationItem(
                value
            );
    }

    /*
     * Legacy/fallback formats.
     */
    if (!html) {

        const legacyItems = [
            [
                "Amplifikasi",
                [
                    "amplification",
                    "amplifikasi"
                ]
            ],
            [
                "Klarifikasi",
                [
                    "clarification",
                    "klarifikasi"
                ]
            ],
            [
                "Counter Narrative",
                [
                    "counter_narrative",
                    "counterNarrative"
                ]
            ],
            [
                "Engagement Media",
                [
                    "media_engagement",
                    "engagement_media"
                ]
            ],
            [
                "Monitoring Lanjutan",
                [
                    "monitoring",
                    "continued_monitoring",
                    "monitoring_lanjutan",
                    "follow_up_monitoring"
                ]
            ]
        ];

        legacyItems.forEach(
            function (item) {

                const found =
                    field(
                        value,
                        item[1]
                    );

                if (
                    found !== null &&
                    found !== undefined
                ) {

                    html += `
                        <div class="recommendation-item">
                            <div class="recommendation-field">
                                <strong>
                                    ${escapeHTML(
                                        labels.recommendation
                                    )}
                                </strong>
                                <span>
                                    ${escapeHTML(
                                        currentLanguage === "id"
                                            ? item[0]
                                            : (
                                                item[0] === "Amplifikasi"
                                                    ? "Amplification"
                                                    : item[0]
                                            )
                                    )}
                                </span>
                            </div>

                            <div class="recommendation-field">
                                <span>
                                    ${escapeHTML(
                                        renderValue(found)
                                    )}
                                </span>
                            </div>
                        </div>
                    `;
                }
            }
        );
    }

    if (!html) {
        html =
            renderObject(
                value
            );
    }

    return `
        <article class="
            analysis-card
            full-width
        ">
            <h3>
                ${escapeHTML(
                    labels.recommendation
                )}
            </h3>

            <div class="
                recommendations
            ">
                ${html}
            </div>
        </article>
    `;
}
'''

text = text[:start] + new_func + text[end:]

# Also make sure the rendered language block is selected from currentLanguage.
# This is already present in the current script, so only validate it.
if "function getLanguageData(" not in text:
    raise RuntimeError("getLanguageData() not found")

# Remove old event reattachment if present; event delegation is safer.
text = text.replace(
    """
    attachResultEvents();
""",
    ""
)

# Update footer/version comment if present.
text = text.replace(
    "AI Video Summarizer — V2",
    "AI Video Summarizer — V3"
)

out.write_text(text, encoding="utf-8")

print(f"Created: {out}")
print("Fixed recommendation rendering:")
print("- Type is now translated EN/ID.")
print("- Action is rendered from the selected language block.")
print("- Reason is rendered from the selected language block.")
print("- Supports amplification, clarification, counter narrative, media engagement, and monitoring.")
print("- Keeps recommendation strategy/type unchanged between languages.")
print("- Removed legacy attachResultEvents() call from renderAI().")
