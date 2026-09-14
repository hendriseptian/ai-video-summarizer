/* ============================================================
   AI MEDIA MONITORING & ANALYSIS
   SCRIPT.JS
   V1 UI + V2 AI ANALYSIS
   ============================================================ */

const API_URL =
    "https://ai-video-summarizer.hendriseptian25.workers.dev/analyze";

let currentData = null;
let currentAI = null;
let currentLanguage = "en";

const videoUrlInput = document.getElementById("videoUrl");
const analyzeButton = document.getElementById("analyzeButton");
const statusBox = document.getElementById("status");
const videoInfoBox = document.getElementById("videoInfo");
const transcriptBox = document.getElementById("transcript");

/* ============================================================
   INITIALIZATION
   ============================================================ */

document.addEventListener("DOMContentLoaded", function () {

    if (analyzeButton) {
        analyzeButton.addEventListener(
            "click",
            analyzeVideo
        );
    }

    if (videoUrlInput) {
        videoUrlInput.addEventListener(
            "keydown",
            function (event) {

                if (event.key === "Enter") {
                    analyzeVideo();
                }

            }
        );
    }

    prepareAIResultArea();

});


/* ============================================================
   PREPARE AI RESULT AREA
   ============================================================ */

function prepareAIResultArea() {

    let aiResult =
        document.getElementById("aiResult");

    if (!aiResult) {

        aiResult =
            document.createElement("div");

        aiResult.id = "aiResult";

        const transcriptCard =
            document.querySelector(
                ".transcript-card"
            );

        const main =
            document.querySelector("main");

        if (transcriptCard && main) {

            main.insertBefore(
                aiResult,
                transcriptCard
            );

        } else if (main) {

            main.appendChild(aiResult);

        }

    }

}


/* ============================================================
   ANALYZE VIDEO
   ============================================================ */

async function analyzeVideo() {

    const url =
        videoUrlInput
            ? videoUrlInput.value.trim()
            : "";

    if (!url) {

        showStatus(
            "Please enter a YouTube URL.",
            "error"
        );

        return;
    }

    if (!isValidYouTubeUrl(url)) {

        showStatus(
            "Please enter a valid YouTube URL.",
            "error"
        );

        return;
    }

    setLoading(true);

    showStatus(
        "Analyzing video. Please wait...",
        "loading"
    );

    if (videoInfoBox) {

        videoInfoBox.innerHTML = `
            <p>Loading video information...</p>
        `;

    }

    if (transcriptBox) {

        transcriptBox.innerHTML = `
            <p>Loading transcript...</p>
        `;

    }

    const aiResult =
        document.getElementById("aiResult");

    if (aiResult) {
        aiResult.innerHTML = "";
    }

    try {

        const response =
            await fetch(
                API_URL,
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({
                        url: url
                    })
                }
            );

        const rawText =
            await response.text();

        let data;

        try {

            data =
                JSON.parse(rawText);

        } catch (error) {

            console.error(
                "Invalid JSON:",
                rawText
            );

            throw new Error(
                "Server returned invalid JSON."
            );

        }

        if (!response.ok) {

            throw new Error(
                getErrorMessage(
                    data,
                    response.status
                )
            );

        }

        currentData = data;

        currentAI =
            extractAIData(data);

        if (!currentAI) {

            console.error(
                "Complete server response:",
                data
            );

            throw new Error(
                "AI analysis result was not found in server response."
            );

        }

        renderVideoInformation(data);

        renderAIAnalysis(currentAI);

        renderTranscript(data);

        showStatus(
            "Analysis completed successfully.",
            "success"
        );

    } catch (error) {

        console.error(
            "Analysis error:",
            error
        );

        showStatus(
            error.message ||
                "Failed to analyze video.",
            "error"
        );

        if (videoInfoBox) {

            videoInfoBox.innerHTML = `
                <div class="error-box">
                    ${escapeHTML(
                        error.message ||
                        "Failed to analyze video."
                    )}
                </div>
            `;

        }

        if (transcriptBox) {

            transcriptBox.innerHTML = `
                <p>Transcript unavailable.</p>
            `;

        }

    } finally {

        setLoading(false);

    }

}


/* ============================================================
   YOUTUBE VALIDATION
   ============================================================ */

function isValidYouTubeUrl(url) {

    try {

        const parsed =
            new URL(url);

        const host =
            parsed.hostname
                .toLowerCase()
                .replace(/^www\./, "");

        return (
            host === "youtube.com" ||
            host === "m.youtube.com" ||
            host === "youtu.be"
        );

    } catch {

        return false;

    }

}


/* ============================================================
   STATUS
   ============================================================ */

function showStatus(
    message,
    type
) {

    if (!statusBox) {
        return;
    }

    statusBox.className =
        type || "";

    statusBox.textContent =
        message || "";

}


/* ============================================================
   LOADING
   ============================================================ */

function setLoading(isLoading) {

    if (!analyzeButton) {
        return;
    }

    if (isLoading) {

        analyzeButton.disabled =
            true;

        analyzeButton.dataset.oldText =
            analyzeButton.textContent;

        analyzeButton.innerHTML = `
            <span class="loading-container">
                <span class="loading-spinner"></span>
                ANALYZING...
            </span>
        `;

    } else {

        analyzeButton.disabled =
            false;

        analyzeButton.textContent =
            analyzeButton.dataset.oldText ||
            "ANALYZE";

    }

}


/* ============================================================
   ERROR MESSAGE
   ============================================================ */

function getErrorMessage(
    data,
    status
) {

    if (!data) {
        return `Server error (${status}).`;
    }

    if (
        typeof data.detail ===
        "string"
    ) {
        return data.detail;
    }

    if (
        typeof data.error ===
        "string"
    ) {
        return data.error;
    }

    if (
        typeof data.message ===
        "string"
    ) {
        return data.message;
    }

    return `Server error (${status}).`;

}


/* ============================================================
   EXTRACT AI DATA
   ============================================================ */

function extractAIData(data) {

    if (
        !data ||
        typeof data !== "object"
    ) {
        return null;
    }

    const candidates = [

        data.ai,

        data.analysis,

        data.result,

        data.ai_result,

        data.aiAnalysis,

        data.video_analysis,

        data.videoAnalysis

    ];

    for (
        const candidate
        of candidates
    ) {

        if (
            candidate &&
            typeof candidate ===
                "object"
        ) {

            return candidate;

        }

    }

    if (
        data.summary ||
        data.key_points ||
        data.keyPoints ||
        data.sentiment ||
        data.main_issue ||
        data.mainIssue
    ) {

        return data;

    }

    return recursiveFindAI(
        data
    );

}


/* ============================================================
   RECURSIVE AI SEARCH
   ============================================================ */

function recursiveFindAI(
    object,
    depth = 0
) {

    if (
        !object ||
        typeof object !== "object"
    ) {
        return null;
    }

    if (depth > 10) {
        return null;
    }

    if (
        object.summary ||
        object.key_points ||
        object.keyPoints ||
        object.sentiment ||
        object.main_issue ||
        object.mainIssue ||
        object.media_analysis ||
        object.mediaAnalysis
    ) {

        return object;

    }

    for (
        const key of Object.keys(object)
    ) {

        const value =
            object[key];

        if (
            value &&
            typeof value ===
                "object"
        ) {

            const found =
                recursiveFindAI(
                    value,
                    depth + 1
                );

            if (found) {
                return found;
            }

        }

    }

    return null;

}


/* ============================================================
   LANGUAGE
   ============================================================ */

function getLanguageValue(value) {

    if (
        value === null ||
        value === undefined
    ) {
        return "";
    }

    if (
        typeof value === "string"
    ) {
        return value;
    }

    if (
        Array.isArray(value)
    ) {
        return value;
    }

    if (
        typeof value !== "object"
    ) {
        return String(value);
    }

    if (
        currentLanguage === "id" &&
        value.id !== undefined
    ) {
        return value.id;
    }

    if (
        currentLanguage === "en" &&
        value.en !== undefined
    ) {
        return value.en;
    }

    if (
        value.en !== undefined
    ) {
        return value.en;
    }

    if (
        value.id !== undefined
    ) {
        return value.id;
    }

    return value;

}


/* ============================================================
   GET FIELD
   ============================================================ */

function getField(
    object,
    ...keys
) {

    if (
        !object ||
        typeof object !== "object"
    ) {
        return null;
    }

    for (
        const key of keys
    ) {

        if (
            object[key] !== undefined &&
            object[key] !== null
        ) {

            return object[key];

        }

    }

    return null;

}


/* ============================================================
   VIDEO INFORMATION
   ============================================================ */

function renderVideoInformation(
    data
) {

    if (!videoInfoBox) {
        return;
    }

    const video =
        data.video ||
        data.video_info ||
        data.videoInfo ||
        {};

    const transcript =
        data.transcript ||
        {};

    const title =
        transcript.title ||
        video.title ||
        data.title ||
        "Untitled Video";

    const language =
        transcript.language ||
        video.language ||
        data.language ||
        "-";

    const videoId =
        video.id ||
        data.video_id ||
        data.videoId ||
        extractYouTubeId(
            video.url ||
            data.url ||
            videoUrlInput.value
        );

    const url =
        video.url ||
        data.url ||
        videoUrlInput.value;

    const station =
        data.station ||
        video.station ||
        "";

    const source =
        data.source ||
        video.source ||
        "";

    const publicationDate =
        data.publication_date ||
        data.publicationDate ||
        video.publication_date ||
        "";

    let html = `
        <div class="meta-grid">

            <div class="meta-item">
                <strong>Title</strong>
                <span>
                    ${escapeHTML(title)}
                </span>
            </div>

            <div class="meta-item">
                <strong>Video ID</strong>
                <span>
                    ${escapeHTML(videoId || "-")}
                </span>
            </div>

            <div class="meta-item">
                <strong>Language</strong>
                <span>
                    ${escapeHTML(language)}
                </span>
            </div>

            <div class="meta-item">
                <strong>URL</strong>
                <span>
                    ${escapeHTML(url)}
                </span>
            </div>
    `;

    if (station) {

        html += `
            <div class="meta-item">
                <strong>Station</strong>
                <span>
                    ${escapeHTML(station)}
                </span>
            </div>
        `;

    }

    if (source) {

        html += `
            <div class="meta-item">
                <strong>Source</strong>
                <span>
                    ${escapeHTML(source)}
                </span>
            </div>
        `;

    }

    if (publicationDate) {

        html += `
            <div class="meta-item">
                <strong>Publication Date</strong>
                <span>
                    ${escapeHTML(
                        publicationDate
                    )}
                </span>
            </div>
        `;

    }

    html += `
        </div>
    `;

    videoInfoBox.innerHTML =
        html;

}


/* ============================================================
   AI ANALYSIS
   ============================================================ */

function renderAIAnalysis(
    ai
) {

    const aiResult =
        document.getElementById(
            "aiResult"
        );

    if (!aiResult) {
        return;
    }

    const summary =
        getField(
            ai,
            "summary",
            "executive_summary"
        );

    const sentiment =
        getField(
            ai,
            "sentiment"
        );

    const mainIssue =
        getField(
            ai,
            "main_issue",
            "mainIssue",
            "isu_utama"
        );

    const keyPoints =
        getField(
            ai,
            "key_points",
            "keyPoints"
        );

    const mediaAnalysis =
        getField(
            ai,
            "media_analysis",
            "mediaAnalysis",
            "analisis_media"
        );

    const communicationRisk =
        getField(
            ai,
            "communication_risk",
            "communicationRisk",
            "risiko_komunikasi"
        );

    const recommendations =
        getField(
            ai,
            "recommendations",
            "recommendation",
            "rekomendasi"
        );

    const criticalAnalysis =
        getField(
            ai,
            "critical_analysis",
            "criticalAnalysis"
        );

    const implications =
        getField(
            ai,
            "implications",
            "implication"
        );

    const takeaways =
        getField(
            ai,
            "takeaways",
            "key_takeaways"
        );

    aiResult.innerHTML = `

        <div class="result-toolbar">

            <div class="toolbar-actions">

                <button
                    type="button"
                    id="languageEn"
                    class="lang-btn ${
                        currentLanguage === "en"
                            ? "active"
                            : ""
                    }">
                    EN
                </button>

                <button
                    type="button"
                    id="languageId"
                    class="lang-btn ${
                        currentLanguage === "id"
                            ? "active"
                            : ""
                    }">
                    ID
                </button>

                <button
                    type="button"
                    id="exportPdfButton"
                    class="export-btn">
                    Export PDF
                </button>

            </div>

        </div>


        <div class="analysis-grid">

            ${createSummaryCard(
                summary
            )}

            ${createSentimentCard(
                sentiment
            )}

            ${createIssueCard(
                mainIssue
            )}

            ${createKeyPointsCard(
                keyPoints
            )}

            ${createMediaAnalysisCard(
                mediaAnalysis
            )}

            ${createRiskCard(
                communicationRisk
            )}

            ${createRecommendationsCard(
                recommendations
            )}

            ${createTextCard(
                "Critical Analysis",
                criticalAnalysis
            )}

            ${createTextCard(
                "Implications",
                implications
            )}

            ${createTakeawaysCard(
                takeaways
            )}

        </div>

    `;

    attachResultEvents();

}


/* ============================================================
   SUMMARY
   ============================================================ */

function createSummaryCard(
    value
) {

    if (!value) {
        return "";
    }

    return `
        <article class="analysis-card full-width">

            <h3>Summary</h3>

            <div class="summary-text">
                ${renderText(value)}
            </div>

        </article>
    `;

}


/* ============================================================
   SENTIMENT
   ============================================================ */

function createSentimentCard(
    value
) {

    if (!value) {
        return "";
    }

    let text =
        getLanguageValue(value);

    if (
        typeof text === "object"
    ) {

        text =
            text.label ||
            text.value ||
            text.result ||
            text.sentiment ||
            "";

    }

    text =
        String(text);

    const normalized =
        text.toLowerCase();

    let className =
        "sentiment-neutral";

    if (
        normalized.includes(
            "positive"
        ) ||
        normalized.includes(
            "positif"
        )
    ) {

        className =
            "sentiment-positive";

    } else if (
        normalized.includes(
            "negative"
        ) ||
        normalized.includes(
            "negatif"
        )
    ) {

        className =
            "sentiment-negative";

    }

    return `
        <article class="analysis-card">

            <h3>Sentiment</h3>

            <span class="
                sentiment-badge
                ${className}
            ">
                ${escapeHTML(text)}
            </span>

        </article>
    `;

}


/* ============================================================
   MAIN ISSUE
   ============================================================ */

function createIssueCard(
    value
) {

    if (!value) {
        return "";
    }

    return `
        <article class="analysis-card">

            <h3>Isu Utama</h3>

            <div class="main-issue">
                ${renderText(value)}
            </div>

        </article>
    `;

}


/* ============================================================
   KEY POINTS
   ============================================================ */

function createKeyPointsCard(
    value
) {

    if (!value) {
        return "";
    }

    const items =
        normalizeArray(value);

    return `
        <article class="analysis-card">

            <h3>Key Points</h3>

            <ul class="key-points-list">

                ${items
                    .map(
                        item => `
                            <li>
                                ${renderText(
                                    item
                                )}
                            </li>
                        `
                    )
                    .join("")}

            </ul>

        </article>
    `;

}


/* ============================================================
   MEDIA ANALYSIS
   ============================================================ */

function createMediaAnalysisCard(
    value
) {

    if (!value) {
        return "";
    }

    if (
        typeof value !== "object" ||
        Array.isArray(value)
    ) {

        return `
            <article class="
                analysis-card
                full-width
            ">

                <h3>Analisis Media</h3>

                ${renderText(value)}

            </article>
        `;

    }

    const fields = [

        [
            "Angle Pemberitaan",
            [
                "angle",
                "news_angle",
                "media_angle"
            ]
        ],

        [
            "Aktor / OPD yang Mendapat Sorotan",
            [
                "actors",
                "actors_opd",
                "highlighted_actors",
                "aktor",
                "opd"
            ]
        ],

        [
            "Posisi Pemprov Jawa Tengah",
            [
                "pemprov_position",
                "government_position",
                "position_of_pemprov"
            ]
        ],

        [
            "Potensi Pembentukan Opini Publik",
            [
                "public_opinion",
                "public_opinion_potential"
            ]
        ],

        [
            "Key Message",
            [
                "key_message",
                "key_messages",
                "message"
            ]

        ]

    ];

    let html = "";

    for (
        const [
            label,
            keys
        ] of fields
    ) {

        const field =
            getField(
                value,
                ...keys
            );

        if (
            field !== null &&
            field !== undefined
        ) {

            html += `
                <div class="
                    media-analysis-item
                ">

                    <strong>
                        ${label}
                    </strong>

                    ${renderText(
                        field
                    )}

                </div>
            `;

        }

    }

    if (!html) {
        html =
            renderObject(value);
    }

    return `
        <article class="
            analysis-card
            full-width
        ">

            <h3>Analisis Media</h3>

            <div class="
                media-analysis
            ">

                ${html}

            </div>

        </article>
    `;

}


/* ============================================================
   COMMUNICATION RISK
   ============================================================ */

function createRiskCard(
    value
) {

    if (!value) {
        return "";
    }

    let level = "";
    let reason = "";
    let escalation = "";

    if (
        typeof value === "object" &&
        !Array.isArray(value)
    ) {

        level =
            getField(
                value,
                "level",
                "risk_level",
                "risk",
                "tingkat"
            );

        reason =
            getField(
                value,
                "reason",
                "alasan"
            );

        escalation =
            getField(
                value,
                "escalation",
                "potential_escalation",
                "potensi_eskalasi"
            );

    } else {

        level = value;

    }

    let levelText =
        getLanguageValue(level);

    if (
        typeof levelText ===
        "object"
    ) {

        levelText =
            levelText.level ||
            levelText.value ||
            levelText.label ||
            "";

    }

    const normalized =
        String(levelText)
            .toLowerCase();

    let riskClass =
        "risk-low";

    if (
        normalized.includes(
            "high"
        ) ||
        normalized.includes(
            "tinggi"
        )
    ) {

        riskClass =
            "risk-high";

    } else if (
        normalized.includes(
            "medium"
        ) ||
        normalized.includes(
            "moderate"
        ) ||
        normalized.includes(
            "sedang"
        )
    ) {

        riskClass =
            "risk-medium";

    }

    return `
        <article class="analysis-card">

            <h3>Risiko Komunikasi</h3>

            <span class="
                risk-badge
                ${riskClass}
            ">
                ${escapeHTML(
                    String(
                        levelText || "-"
                    )
                )}
            </span>

            ${
                reason
                    ? `
                        <div
                            style="
                                margin-top:10px;
                            "
                        >
                            <strong>
                                Alasan
                            </strong>

                            ${renderText(
                                reason
                            )}
                        </div>
                    `
                    : ""
            }

            ${
                escalation
                    ? `
                        <div
                            style="
                                margin-top:10px;
                            "
                        >
                            <strong>
                                Potensi Eskalasi
                            </strong>

                            ${renderText(
                                escalation
                            )}
                        </div>
                    `
                    : ""
            }

        </article>
    `;

}


/* ============================================================
   RECOMMENDATIONS
   ============================================================ */

function createRecommendationsCard(
    value
) {

    if (!value) {
        return "";
    }

    if (
        typeof value !== "object" ||
        Array.isArray(value)
    ) {

        return `
            <article class="
                analysis-card
                full-width
            ">

                <h3>Rekomendasi</h3>

                ${renderText(value)}

            </article>
        `;

    }

    const fields = [

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
                "continued_monitoring",
                "monitoring_lanjutan",
                "follow_up_monitoring"
            ]
        ]

    ];

    let html = "";

    for (
        const [
            label,
            keys
        ] of fields
    ) {

        const field =
            getField(
                value,
                ...keys
            );

        if (
            field !== null &&
            field !== undefined
        ) {

            html += `
                <div class="
                    recommendation-item
                ">

                    <strong>
                        ${label}
                    </strong>

                    ${renderText(
                        field
                    )}

                </div>
            `;

        }

    }

    if (!html) {

        html = `
            <div class="
                recommendation-item
            ">

                ${renderObject(value)}

            </div>
        `;

    }

    return `
        <article class="
            analysis-card
            full-width
        ">

            <h3>Rekomendasi</h3>

            <div class="
                recommendations
            ">

                ${html}

            </div>

        </article>
    `;

}


/* ============================================================
   GENERIC TEXT CARD
   ============================================================ */

function createTextCard(
    title,
    value
) {

    if (!value) {
        return "";
    }

    return `
        <article class="analysis-card">

            <h3>
                ${escapeHTML(title)}
            </h3>

            ${renderText(value)}

        </article>
    `;

}


/* ============================================================
   TAKEAWAYS
   ============================================================ */

function createTakeawaysCard(
    value
) {

    if (!value) {
        return "";
    }

    return `
        <article class="
            analysis-card
            full-width
        ">

            <h3>Takeaways</h3>

            <div class="takeaways">
                ${renderText(value)}
            </div>

        </article>
    `;

}


/* ============================================================
   RESULT EVENTS
   ============================================================ */

function attachResultEvents() {

    const enButton =
        document.getElementById(
            "languageEn"
        );

    const idButton =
        document.getElementById(
            "languageId"
        );

    const exportButton =
        document.getElementById(
            "exportPdfButton"
        );

    if (enButton) {

        enButton.addEventListener(
            "click",
            function () {

                currentLanguage = "en";

                renderAIAnalysis(
                    currentAI
                );

            }
        );

    }

    if (idButton) {

        idButton.addEventListener(
            "click",
            function () {

                currentLanguage = "id";

                renderAIAnalysis(
                    currentAI
                );

            }
        );

    }

    if (exportButton) {

        exportButton.addEventListener(
            "click",
            exportPDF
        );

    }

}


/* ============================================================
   RENDER TEXT
   ============================================================ */

function renderText(
    value
) {

    value =
        getLanguageValue(value);

    if (
        value === null ||
        value === undefined
    ) {
        return "";
    }

    if (
        Array.isArray(value)
    ) {

        return `
            <ul>

                ${value
                    .map(
                        item => `
                            <li>
                                ${renderText(
                                    item
                                )}
                            </li>
                        `
                    )
                    .join("")}

            </ul>
        `;

    }

    if (
        typeof value === "object"
    ) {

        return renderObject(
            value
        );

    }

    const text =
        String(value);

    if (
        /^Inference:/i.test(text)
    ) {

        const clean =
            text.replace(
                /^Inference:\s*/i,
                ""
            );

        return `
            <div class="inference">

                <span class="
                    inference-label
                ">
                    Inference:
                </span>

                ${escapeHTML(clean)}

            </div>
        `;

    }

    return escapeHTML(
        text
    ).replace(
        /\n/g,
        "<br>"
    );

}


/* ============================================================
   RENDER OBJECT
   ============================================================ */

function renderObject(
    object
) {

    if (
        !object ||
        typeof object !== "object"
    ) {

        return renderText(
            object
        );

    }

    let html = "";

    for (
        const [
            key,
            value
        ] of Object.entries(object)
    ) {

        html += `
            <div class="
                media-analysis-item
            ">

                <strong>
                    ${escapeHTML(
                        formatLabel(key)
                    )}
                </strong>

                ${renderText(
                    value
                )}

            </div>
        `;

    }

    return html;

}


/* ============================================================
   NORMALIZE ARRAY
   ============================================================ */

function normalizeArray(
    value
) {

    if (
        Array.isArray(value)
    ) {
        return value;
    }

    if (
        typeof value === "object" &&
        value !== null
    ) {

        const possible =
            value.items ||
            value.points ||
            value.list ||
            value.values;

        if (
            Array.isArray(possible)
        ) {
            return possible;
        }

    }

    if (
        typeof value === "string"
    ) {

        return value
            .split(/\n+/)
            .map(
                item =>
                    item
                        .replace(
                            /^\s*[-•*]\s*/,
                            ""
                        )
                        .trim()
            )
            .filter(Boolean);

    }

    return [value];

}


/* ============================================================
   FORMAT LABEL
   ============================================================ */

function formatLabel(
    value
) {

    return String(value)
        .replace(
            /_/g,
            " "
        )
        .replace(
            /([a-z])([A-Z])/g,
            "$1 $2"
        )
        .replace(
            /\b\w/g,
            char =>
                char.toUpperCase()
        );

}


/* ============================================================
   TRANSCRIPT
   ============================================================ */

function renderTranscript(
    data
) {

    if (!transcriptBox) {
        return;
    }

    const transcriptData =
        data.transcript ||
        {};

    let segments =
        transcriptData.transcript ||
        transcriptData.segments ||
        data.transcript_segments ||
        data.segments ||
        [];

    if (
        typeof segments ===
        "string"
    ) {

        transcriptBox.innerHTML = `
            <div class="
                transcript-row
            ">

                <div class="
                    transcript-time
                ">
                    00:00
                </div>

                <div class="
                    transcript-text
                ">
                    ${escapeHTML(
                        segments
                    )}
                </div>

            </div>
        `;

        return;

    }

    if (
        !Array.isArray(segments) ||
        segments.length === 0
    ) {

        transcriptBox.innerHTML = `
            <p>
                Transcript unavailable.
            </p>
        `;

        return;

    }

    transcriptBox.innerHTML =
        segments
            .map(
                (
                    segment,
                    index
                ) => {

                    const text =
                        typeof segment ===
                        "string"
                            ? segment
                            : segment.text ||
                              segment.transcript ||
                              "";

                    const start =
                        typeof segment ===
                        "object"
                            ? segment.start
                            : index * 2;

                    return `
                        <div class="
                            transcript-row
                        ">

                            <div class="
                                transcript-time
                            ">
                                ${formatTimestamp(
                                    start
                                )}
                            </div>

                            <div class="
                                transcript-text
                            ">
                                ${escapeHTML(
                                    text
                                )}
                            </div>

                        </div>
                    `;

                }
            )
            .join("");

}


/* ============================================================
   TIMESTAMP
   ============================================================ */

function formatTimestamp(
    seconds
) {

    seconds =
        Math.max(
            0,
            Math.floor(
                Number(seconds) || 0
            )
        );

    const hours =
        Math.floor(
            seconds / 3600
        );

    const minutes =
        Math.floor(
            (seconds % 3600) / 60
        );

    const secs =
        seconds % 60;

    if (hours > 0) {

        return [
            String(hours)
                .padStart(2, "0"),

            String(minutes)
                .padStart(2, "0"),

            String(secs)
                .padStart(2, "0")

        ].join(":");

    }

    return [
        String(minutes)
            .padStart(2, "0"),

        String(secs)
            .padStart(2, "0")

    ].join(":");

}


/* ============================================================
   YOUTUBE ID
   ============================================================ */

function extractYouTubeId(
    url
) {

    if (!url) {
        return "";
    }

    try {

        const parsed =
            new URL(url);

        const host =
            parsed.hostname
                .toLowerCase();

        if (
            host.includes(
                "youtu.be"
            )
        ) {

            return parsed.pathname
                .replace(
                    "/",
                    ""
                )
                .trim();

        }

        if (
            host.includes(
                "youtube.com"
            )
        ) {

            return (
                parsed.searchParams
                    .get("v") || ""
            );

        }

    } catch {

        return "";

    }

    return "";

}


/* ============================================================
   ESCAPE HTML
   ============================================================ */

function escapeHTML(
    value
) {

    if (
        value === null ||
        value === undefined
    ) {
        return "";
    }

    return String(value)
        .replace(
            /&/g,
            "&amp;"
        )
        .replace(
            /</g,
            "&lt;"
        )
        .replace(
            />/g,
            "&gt;"
        )
        .replace(
            /"/g,
            "&quot;"
        )
        .replace(
            /'/g,
            "&#039;"
        );

}


/* ============================================================
   EXPORT PDF
   ============================================================ */

async function exportPDF() {

    if (!currentData || !currentAI) {

        showStatus(
            "No analysis available to export.",
            "error"
        );

        return;

    }

    if (
        !window.jspdf ||
        !window.jspdf.jsPDF
    ) {

        showStatus(
            "PDF library is not available.",
            "error"
        );

        return;

    }

    try {

        const {
            jsPDF
        } = window.jspdf;

        const pdf =
            new jsPDF({
                orientation:
                    "portrait",

                unit:
                    "mm",

                format:
                    "a4"
            });

        const transcript =
            currentData.transcript ||
            {};

        const title =
            transcript.title ||
            "AI Media Monitoring Analysis";

        let y = 18;

        pdf.setTextColor(
            23,
            32,
            51
        );

        pdf.setFontSize(17);

        pdf.setFont(
            "helvetica",
            "bold"
        );

        pdf.text(
            "AI Media Monitoring & Analysis",
            15,
            y
        );

        y += 8;

        pdf.setFontSize(11);

        pdf.setFont(
            "helvetica",
            "normal"
        );

        const titleLines =
            pdf.splitTextToSize(
                String(title),
                178
            );

        pdf.text(
            titleLines,
            15,
            y
        );

        y +=
            titleLines.length * 5 +
            5;

        pdf.setDrawColor(
            210,
            214,
            220
        );

        pdf.line(
            15,
            y,
            195,
            y
        );

        y += 8;

        const sections = [

            [
                "Summary",
                getField(
                    currentAI,
                    "summary",
                    "executive_summary"
                )
            ],

            [
                "Sentiment",
                getField(
                    currentAI,
                    "sentiment"
                )
            ],

            [
                "Isu Utama",
                getField(
                    currentAI,
                    "main_issue",
                    "mainIssue",
                    "isu_utama"
                )
            ],

            [
                "Key Points",
                getField(
                    currentAI,
                    "key_points",
                    "keyPoints"
                )
            ],

            [
                "Analisis Media",
                getField(
                    currentAI,
                    "media_analysis",
                    "mediaAnalysis",
                    "analisis_media"
                )
            ],

            [
                "Risiko Komunikasi",
                getField(
                    currentAI,
                    "communication_risk",
                    "communicationRisk",
                    "risiko_komunikasi"
                )
            ],

            [
                "Rekomendasi",
                getField(
                    currentAI,
                    "recommendations",
                    "recommendation",
                    "rekomendasi"
                )
            ],

            [
                "Critical Analysis",
                getField(
                    currentAI,
                    "critical_analysis",
                    "criticalAnalysis"
                )
            ],

            [
                "Implications",
                getField(
                    currentAI,
                    "implications",
                    "implication"
                )
            ],

            [
                "Takeaways",
                getField(
                    currentAI,
                    "takeaways",
                    "key_takeaways"
                )
            ]

        ];

        for (
            const [
                sectionTitle,
                value
            ] of sections
        ) {

            if (
                value === null ||
                value === undefined ||
                value === ""
            ) {
                continue;
            }

            y =
                addPDFSection(
                    pdf,
                    sectionTitle,
                    getLanguageValue(
                        value
                    ),
                    y
                );

        }

        const pageCount =
            pdf.internal
                .getNumberOfPages();

        for (
            let page = 1;
            page <= pageCount;
            page++
        ) {

            pdf.setPage(
                page
            );

            pdf.setFontSize(8);

            pdf.setFont(
                "helvetica",
                "normal"
            );

            pdf.setTextColor(
                130,
                130,
                130
            );

            pdf.text(
                `AI Media Monitoring & Analysis — Page ${page} of ${pageCount}`,
                15,
                287
            );

        }

        const fileName =
            sanitizeFileName(
                title
            );

        pdf.save(
            `${fileName}_AI_Analysis.pdf`
        );

        showStatus(
            "PDF exported successfully.",
            "success"
        );

    } catch (error) {

        console.error(
            "PDF error:",
            error
        );

        showStatus(
            "Failed to export PDF.",
            "error"
        );

    }

}


/* ============================================================
   PDF SECTION
   ============================================================ */

function addPDFSection(
    pdf,
    title,
    value,
    y
) {

    if (y > 270) {

        pdf.addPage();

        y = 18;

    }

    pdf.setTextColor(
        23,
        32,
        51
    );

    pdf.setFontSize(12);

    pdf.setFont(
        "helvetica",
        "bold"
    );

    pdf.text(
        title,
        15,
        y
    );

    y += 6;

    pdf.setFontSize(9);

    pdf.setFont(
        "helvetica",
        "normal"
    );

    pdf.setTextColor(
        71,
        84,
        103
    );

    const text =
        valueToPlainText(
            value
        );

    const lines =
        pdf.splitTextToSize(
            text,
            178
        );

    for (
        const line
        of lines
    ) {

        if (y > 278) {

            pdf.addPage();

            y = 18;

            pdf.setFontSize(9);

            pdf.setFont(
                "helvetica",
                "normal"
            );

            pdf.setTextColor(
                71,
                84,
                103
            );

        }

        pdf.text(
            line,
            15,
            y
        );

        y += 4.5;

    }

    return y + 5;

}


/* ============================================================
   VALUE TO PLAIN TEXT
   ============================================================ */

function valueToPlainText(
    value
) {

    if (
        value === null ||
        value === undefined
    ) {
        return "";
    }

    if (
        Array.isArray(value)
    ) {

        return value
            .map(
                item =>
                    "• " +
                    valueToPlainText(
                        item
                    )
            )
            .join("\n");

    }

    if (
        typeof value === "object"
    ) {

        return Object.entries(
            value
        )
        .map(
            ([
                key,
                item
            ]) =>
                `${formatLabel(key)}: ${valueToPlainText(item)}`
        )
        .join("\n");

    }

    return String(value);

}


/* ============================================================
   FILE NAME
   ============================================================ */

function sanitizeFileName(
    name
) {

    return String(
        name || "video"
    )
        .replace(
            /[<>:"/\\|?*]+/g,
            ""
        )
        .replace(
            /\s+/g,
            "_"
        )
        .substring(
            0,
            100
        );

}


/* ============================================================
   KEYBOARD SHORTCUT
   ============================================================ */

document.addEventListener(
    "keydown",
    function (event) {

        if (
            event.ctrlKey &&
            event.key === "Enter"
        ) {

            analyzeVideo();

        }

    }
);


/* ============================================================
   END OF SCRIPT
   ============================================================ */
