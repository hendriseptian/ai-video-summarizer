/* ============================================================
   AI MEDIA MONITORING & ANALYSIS
   SCRIPT.JS V1
   ============================================================ */

const API_URL =
    "https://ai-video-summarizer.hendriseptian25.workers.dev/analyze";

let currentData = null;
let currentLanguage = "en";

/* ============================================================
   DOM
   ============================================================ */

const videoUrlInput = document.getElementById("videoUrl");
const analyzeButton = document.getElementById("analyzeButton");
const statusBox = document.getElementById("status");
const videoInfoBox = document.getElementById("videoInfo");
const transcriptBox = document.getElementById("transcript");

/* ============================================================
   INITIALIZATION
   ============================================================ */

document.addEventListener("DOMContentLoaded", () => {
    if (analyzeButton) {
        analyzeButton.addEventListener("click", analyzeVideo);
    }

    if (videoUrlInput) {
        videoUrlInput.addEventListener("keydown", (event) => {
            if (event.key === "Enter") {
                analyzeVideo();
            }
        });
    }

    createDynamicResultArea();
});

/* ============================================================
   CREATE RESULT AREA
   ============================================================ */

function createDynamicResultArea() {
    const main = document.querySelector("main");

    if (!main) {
        return;
    }

    let result = document.getElementById("aiResult");

    if (!result) {
        result = document.createElement("section");
        result.id = "aiResult";
        main.insertBefore(
            result,
            document.querySelector(".transcript-card")
        );
    }

    result.innerHTML = "";
}

/* ============================================================
   ANALYZE VIDEO
   ============================================================ */

async function analyzeVideo() {
    const url = videoUrlInput.value.trim();

    if (!url) {
        showStatus("Please enter a YouTube URL.", "error");
        return;
    }

    if (!isValidYouTubeUrl(url)) {
        showStatus("Please enter a valid YouTube URL.", "error");
        return;
    }

    setLoading(true);

    showStatus(
        "Analyzing video transcript and generating AI media analysis...",
        "loading"
    );

    videoInfoBox.innerHTML = `
        <p>Processing video...</p>
    `;

    transcriptBox.innerHTML = `
        <p>Processing transcript...</p>
    `;

    const resultArea = document.getElementById("aiResult");

    if (resultArea) {
        resultArea.innerHTML = "";
    }

    try {
        const response = await fetch(API_URL, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                url: url
            })
        });

        const rawText = await response.text();

        let data = null;

        try {
            data = JSON.parse(rawText);
        } catch (parseError) {
            throw new Error(
                "Server returned an invalid JSON response."
            );
        }

        if (!response.ok) {
            throw new Error(
                getServerErrorMessage(data, response.status)
            );
        }

        currentData = data;

        const aiData = extractAIData(data);

        if (!aiData) {
            console.error("Server response:", data);

            throw new Error(
                "AI analysis result was not found in server response."
            );
        }

        renderVideoInformation(data);
        renderAIAnalysis(aiData);
        renderTranscript(data);

        showStatus(
            "Analysis completed successfully.",
            "success"
        );
    } catch (error) {
        console.error("Analysis error:", error);

        showStatus(
            error.message || "Failed to analyze video.",
            "error"
        );

        videoInfoBox.innerHTML = `
            <div class="error-box">
                ${escapeHTML(
                    error.message ||
                    "Failed to analyze video."
                )}
            </div>
        `;

        transcriptBox.innerHTML = `
            <p>Transcript unavailable.</p>
        `;
    } finally {
        setLoading(false);
    }
}

/* ============================================================
   VALIDATE YOUTUBE URL
   ============================================================ */

function isValidYouTubeUrl(url) {
    try {
        const parsed = new URL(url);

        const host = parsed.hostname
            .toLowerCase()
            .replace("www.", "");

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

function showStatus(message, type = "") {
    if (!statusBox) {
        return;
    }

    statusBox.className = type;
    statusBox.textContent = message;
}

/* ============================================================
   LOADING
   ============================================================ */

function setLoading(isLoading) {
    if (!analyzeButton) {
        return;
    }

    analyzeButton.disabled = isLoading;

    if (isLoading) {
        analyzeButton.dataset.originalText =
            analyzeButton.textContent;

        analyzeButton.innerHTML = `
            <span class="loading-container">
                <span class="loading-spinner"></span>
                ANALYZING
            </span>
        `;
    } else {
        analyzeButton.textContent =
            analyzeButton.dataset.originalText ||
            "ANALYZE";
    }
}

/* ============================================================
   SERVER ERROR
   ============================================================ */

function getServerErrorMessage(data, statusCode) {
    if (!data) {
        return `Server error (${statusCode}).`;
    }

    if (typeof data.detail === "string") {
        return data.detail;
    }

    if (typeof data.error === "string") {
        return data.error;
    }

    if (typeof data.message === "string") {
        return data.message;
    }

    if (data.detail && typeof data.detail === "object") {
        return JSON.stringify(data.detail);
    }

    return `Server error (${statusCode}).`;
}

/* ============================================================
   EXTRACT AI DATA
   ============================================================ */

function extractAIData(data) {
    if (!data || typeof data !== "object") {
        return null;
    }

    const directCandidates = [
        data.ai,
        data.analysis,
        data.result,
        data.ai_result,
        data.aiAnalysis,
        data.video_analysis,
        data.videoAnalysis
    ];

    for (const candidate of directCandidates) {
        if (
            candidate &&
            typeof candidate === "object"
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

    return recursiveFindAI(data);
}

/* ============================================================
   RECURSIVE AI SEARCH
   ============================================================ */

function recursiveFindAI(object, depth = 0) {
    if (!object || typeof object !== "object") {
        return null;
    }

    if (depth > 8) {
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

    for (const key of Object.keys(object)) {
        const value = object[key];

        if (
            value &&
            typeof value === "object"
        ) {
            const found = recursiveFindAI(
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
   LANGUAGE DATA
   ============================================================ */

function getLanguageData(value) {
    if (
        value === null ||
        value === undefined
    ) {
        return "";
    }

    if (typeof value === "string") {
        return value;
    }

    if (Array.isArray(value)) {
        return value;
    }

    if (typeof value !== "object") {
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
   FIND FIELD
   ============================================================ */

function getField(object, ...keys) {
    if (
        !object ||
        typeof object !== "object"
    ) {
        return null;
    }

    for (const key of keys) {
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
   RENDER VIDEO INFORMATION
   ============================================================ */

function renderVideoInformation(data) {
    const video =
        data.video ||
        data.video_info ||
        data.videoInfo ||
        {};

    const transcript =
        data.transcript || {};

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

    videoInfoBox.innerHTML = `
        <div class="info-item">
            <strong>Title</strong>
            <span>${escapeHTML(title)}</span>
        </div>

        <div class="info-item">
            <strong>Video ID</strong>
            <span>${escapeHTML(videoId || "-")}</span>
        </div>

        <div class="info-item">
            <strong>Language</strong>
            <span>${escapeHTML(language)}</span>
        </div>

        <div class="info-item">
            <strong>URL</strong>
            <span>${escapeHTML(url)}</span>
        </div>
    `;
}

/* ============================================================
   RENDER AI ANALYSIS
   ============================================================ */

function renderAIAnalysis(ai) {
    const resultArea =
        document.getElementById("aiResult");

    if (!resultArea) {
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

    resultArea.innerHTML = `
        ${createToolbar()}

        <div class="analysis-grid">

            ${createSummaryCard(summary)}

            ${createSentimentCard(sentiment)}

            ${createIssueCard(mainIssue)}

            ${createKeyPointsCard(keyPoints)}

            ${createMediaAnalysisCard(mediaAnalysis)}

            ${createRiskCard(communicationRisk)}

            ${createRecommendationsCard(recommendations)}

            ${createTextCard(
                "Critical Analysis",
                criticalAnalysis
            )}

            ${createTextCard(
                "Implications",
                implications
            )}

            ${createTakeawaysCard(takeaways)}

        </div>
    `;

    attachToolbarEvents();
}

/* ============================================================
   TOOLBAR
   ============================================================ */

function createToolbar() {
    return `
        <div class="result-toolbar">

            <button
                type="button"
                id="languageEn"
                class="language-button">
                EN
            </button>

            <button
                type="button"
                id="languageId"
                class="language-button">
                ID
            </button>

            <button
                type="button"
                id="exportPdfButton">
                Export PDF
            </button>

        </div>
    `;
}

/* ============================================================
   TOOLBAR EVENTS
   ============================================================ */

function attachToolbarEvents() {
    const enButton =
        document.getElementById("languageEn");

    const idButton =
        document.getElementById("languageId");

    const exportButton =
        document.getElementById(
            "exportPdfButton"
        );

    if (enButton) {
        enButton.addEventListener(
            "click",
            () => {
                currentLanguage = "en";

                const ai =
                    extractAIData(currentData);

                if (ai) {
                    renderAIAnalysis(ai);
                }
            }
        );
    }

    if (idButton) {
        idButton.addEventListener(
            "click",
            () => {
                currentLanguage = "id";

                const ai =
                    extractAIData(currentData);

                if (ai) {
                    renderAIAnalysis(ai);
                }
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
   SUMMARY CARD
   ============================================================ */

function createSummaryCard(value) {
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
   SENTIMENT CARD
   ============================================================ */

function createSentimentCard(value) {
    if (!value) {
        return "";
    }

    let label = getLanguageData(value);

    if (
        typeof label === "object"
    ) {
        label =
            label.label ||
            label.value ||
            label.result ||
            label.sentiment ||
            JSON.stringify(label);
    }

    label = String(label);

    const normalized =
        label.toLowerCase();

    let className =
        "sentiment-neutral";

    if (
        normalized.includes("positive") ||
        normalized.includes("positif")
    ) {
        className =
            "sentiment-positive";
    } else if (
        normalized.includes("negative") ||
        normalized.includes("negatif")
    ) {
        className =
            "sentiment-negative";
    }

    return `
        <article class="analysis-card">
            <h3>Sentiment</h3>

            <span class="sentiment-badge ${className}">
                ${escapeHTML(label)}
            </span>
        </article>
    `;
}

/* ============================================================
   MAIN ISSUE CARD
   ============================================================ */

function createIssueCard(value) {
    if (!value) {
        return "";
    }

    return `
        <article class="analysis-card">
            <h3>Main Issue</h3>

            <div class="main-issue">
                ${renderText(value)}
            </div>
        </article>
    `;
}

/* ============================================================
   KEY POINTS CARD
   ============================================================ */

function createKeyPointsCard(value) {
    if (!value) {
        return "";
    }

    const items =
        normalizeArray(value);

    if (!items.length) {
        return `
            <article class="analysis-card">
                <h3>Key Points</h3>
                ${renderText(value)}
            </article>
        `;
    }

    return `
        <article class="analysis-card">
            <h3>Key Points</h3>

            <ul class="key-points-list">
                ${items
                    .map(
                        item => `
                            <li>
                                ${renderText(item)}
                            </li>
                        `
                    )
                    .join("")}
            </ul>
        </article>
    `;
}

/* ============================================================
   MEDIA ANALYSIS CARD
   ============================================================ */

function createMediaAnalysisCard(value) {
    if (!value) {
        return "";
    }

    if (
        typeof value !== "object" ||
        Array.isArray(value)
    ) {
        return `
            <article class="analysis-card full-width">
                <h3>Media Analysis</h3>
                ${renderText(value)}
            </article>
        `;
    }

    const labels = [
        ["Angle Pemberitaan", [
            "angle",
            "news_angle",
            "media_angle"
        ]],

        ["Aktor / OPD yang Disorot", [
            "actors",
            "actors_opd",
            "highlighted_actors",
            "aktor",
            "opd"
        ]],

        ["Posisi Pemprov Jawa Tengah", [
            "pemprov_position",
            "government_position",
            "position_of_pemprov"
        ]],

        ["Potensi Pembentukan Opini Publik", [
            "public_opinion",
            "public_opinion_potential"
        ]],

        ["Key Message", [
            "key_message",
            "key_messages",
            "message"
        ]]
    ];

    let content = "";

    for (const [label, keys] of labels) {
        const field =
            getField(value, ...keys);

        if (
            field !== null &&
            field !== undefined
        ) {
            content += `
                <div class="media-analysis-item">
                    <strong>${label}</strong>
                    ${renderText(field)}
                </div>
            `;
        }
    }

    if (!content) {
        content = renderObject(value);
    }

    return `
        <article class="analysis-card full-width">
            <h3>Media Analysis</h3>

            <div class="media-analysis">
                ${content}
            </div>
        </article>
    `;
}

/* ============================================================
   COMMUNICATION RISK CARD
   ============================================================ */

function createRiskCard(value) {
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
        getLanguageData(level);

    if (
        typeof levelText === "object"
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
        normalized.includes("high") ||
        normalized.includes("tinggi")
    ) {
        riskClass = "risk-high";
    } else if (
        normalized.includes("medium") ||
        normalized.includes("moderate") ||
        normalized.includes("sedang")
    ) {
        riskClass = "risk-medium";
    }

    return `
        <article class="analysis-card">
            <h3>Communication Risk</h3>

            <span class="risk-badge ${riskClass}">
                ${escapeHTML(
                    String(levelText || "-")
                )}
            </span>

            ${
                reason
                    ? `
                        <div style="margin-top:12px;">
                            <strong>Reason</strong>
                            ${renderText(reason)}
                        </div>
                    `
                    : ""
            }

            ${
                escalation
                    ? `
                        <div style="margin-top:12px;">
                            <strong>Potential Escalation</strong>
                            ${renderText(escalation)}
                        </div>
                    `
                    : ""
            }
        </article>
    `;
}

/* ============================================================
   RECOMMENDATIONS CARD
   ============================================================ */

function createRecommendationsCard(value) {
    if (!value) {
        return "";
    }

    if (
        typeof value !== "object" ||
        Array.isArray(value)
    ) {
        return `
            <article class="analysis-card">
                <h3>Recommendations</h3>
                ${renderText(value)}
            </article>
        `;
    }

    const mapping = [
        ["Amplifikasi", [
            "amplification",
            "amplifikasi"
        ]],

        ["Klarifikasi", [
            "clarification",
            "klarifikasi"
        ]],

        ["Counter Narrative", [
            "counter_narrative",
            "counterNarrative"
        ]],

        ["Engagement Media", [
            "media_engagement",
            "engagement_media"
        ]],

        ["Monitoring Lanjutan", [
            "continued_monitoring",
            "monitoring_lanjutan",
            "follow_up_monitoring"
        ]]
    ];

    let items = "";

    for (const [label, keys] of mapping) {
        const valueItem =
            getField(value, ...keys);

        if (
            valueItem !== null &&
            valueItem !== undefined
        ) {
            items += `
                <div class="recommendation-item">
                    <strong>${label}</strong>
                    ${renderText(valueItem)}
                </div>
            `;
        }
    }

    if (!items) {
        items = `
            <div class="recommendation-item">
                ${renderObject(value)}
            </div>
        `;
    }

    return `
        <article class="analysis-card full-width">
            <h3>Recommendations</h3>

            <div class="recommendations">
                ${items}
            </div>
        </article>
    `;
}

/* ============================================================
   GENERIC TEXT CARD
   ============================================================ */

function createTextCard(title, value) {
    if (!value) {
        return "";
    }

    return `
        <article class="analysis-card">
            <h3>${title}</h3>

            ${renderText(value)}
        </article>
    `;
}

/* ============================================================
   TAKEAWAYS
   ============================================================ */

function createTakeawaysCard(value) {
    if (!value) {
        return "";
    }

    return `
        <article class="analysis-card full-width">
            <h3>Takeaways</h3>

            <div class="takeaways">
                ${renderText(value)}
            </div>
        </article>
    `;
}

/* ============================================================
   RENDER TEXT
   ============================================================ */

function renderText(value) {
    value = getLanguageData(value);

    if (
        value === null ||
        value === undefined
    ) {
        return "";
    }

    if (Array.isArray(value)) {
        return `
            <ul>
                ${value
                    .map(
                        item => `
                            <li>
                                ${renderText(item)}
                            </li>
                        `
                    )
                    .join("")}
            </ul>
        `;
    }

    if (typeof value === "object") {
        return renderObject(value);
    }

    const text =
        String(value);

    if (
        text.startsWith("Inference:")
    ) {
        return `
            <div class="inference">
                <span class="inference-label">
                    Inference:
                </span>
                ${escapeHTML(
                    text
                        .replace(
                            /^Inference:\s*/i,
                            ""
                        )
                )}
            </div>
        `;
    }

    return escapeHTML(text)
        .replace(/\n/g, "<br>");
}

/* ============================================================
   RENDER OBJECT
   ============================================================ */

function renderObject(object) {
    if (
        !object ||
        typeof object !== "object"
    ) {
        return renderText(object);
    }

    let html = "";

    for (const [key, value] of Object.entries(object)) {
        const label =
            formatLabel(key);

        html += `
            <div class="media-analysis-item">
                <strong>${escapeHTML(label)}</strong>
                ${renderText(value)}
            </div>
        `;
    }

    return html;
}

/* ============================================================
   FORMAT LABEL
   ============================================================ */

function formatLabel(value) {
    return String(value)
        .replace(/_/g, " ")
        .replace(/([a-z])([A-Z])/g, "$1 $2")
        .replace(/\b\w/g, char =>
            char.toUpperCase()
        );
}

/* ============================================================
   NORMALIZE ARRAY
   ============================================================ */

function normalizeArray(value) {
    if (Array.isArray(value)) {
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

        if (Array.isArray(possible)) {
            return possible;
        }
    }

    if (typeof value === "string") {
        return value
            .split(/\n+/)
            .map(item =>
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
   TRANSCRIPT
   ============================================================ */

function renderTranscript(data) {
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
        typeof segments === "string"
    ) {
        transcriptBox.innerHTML = `
            <div class="transcript-row">
                <div class="transcript-text">
                    ${escapeHTML(segments)}
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
            <p>Transcript unavailable.</p>
        `;

        return;
    }

    transcriptBox.innerHTML =
        segments
            .map((segment, index) => {
                const text =
                    typeof segment === "string"
                        ? segment
                        : segment.text ||
                          segment.transcript ||
                          "";

                const start =
                    typeof segment === "object"
                        ? segment.start
                        : null;

                return `
                    <div class="transcript-row">

                        <div class="transcript-time">
                            ${formatTimestamp(
                                start,
                                index
                            )}
                        </div>

                        <div class="transcript-text">
                            ${escapeHTML(text)}
                        </div>

                    </div>
                `;
            })
            .join("");
}

/* ============================================================
   TIMESTAMP
   ============================================================ */

function formatTimestamp(seconds, fallbackIndex) {
    if (
        seconds === null ||
        seconds === undefined ||
        Number.isNaN(Number(seconds))
    ) {
        return formatSeconds(
            fallbackIndex * 2
        );
    }

    return formatSeconds(
        Number(seconds)
    );
}

function formatSeconds(totalSeconds) {
    totalSeconds =
        Math.max(
            0,
            Math.floor(
                Number(totalSeconds) || 0
            )
        );

    const hours =
        Math.floor(
            totalSeconds / 3600
        );

    const minutes =
        Math.floor(
            (totalSeconds % 3600) / 60
        );

    const seconds =
        totalSeconds % 60;

    if (hours > 0) {
        return [
            String(hours).padStart(2, "0"),
            String(minutes).padStart(2, "0"),
            String(seconds).padStart(2, "0")
        ].join(":");
    }

    return [
        String(minutes).padStart(2, "0"),
        String(seconds).padStart(2, "0")
    ].join(":");
}

/* ============================================================
   YOUTUBE ID
   ============================================================ */

function extractYouTubeId(url) {
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
            host.includes("youtu.be")
        ) {
            return parsed.pathname
                .replace("/", "")
                .trim();
        }

        if (
            host.includes("youtube.com")
        ) {
            return (
                parsed.searchParams
                    .get("v") || ""
            );
        }

        return "";
    } catch {
        return "";
    }
}

/* ============================================================
   ESCAPE HTML
   ============================================================ */

function escapeHTML(value) {
    if (
        value === null ||
        value === undefined
    ) {
        return "";
    }

    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

/* ============================================================
   EXPORT PDF
   ============================================================ */

async function exportPDF() {
    if (!currentData) {
        showStatus(
            "No analysis available to export.",
            "error"
        );

        return;
    }

    if (
        typeof window.jspdf ===
        "undefined"
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
                orientation: "portrait",
                unit: "mm",
                format: "a4"
            });

        const ai =
            extractAIData(
                currentData
            );

        const transcript =
            currentData.transcript ||
            {};

        const title =
            transcript.title ||
            "AI Media Monitoring Analysis";

        let y = 18;

        /* Header */

        pdf.setFontSize(17);
        pdf.setFont("helvetica", "bold");

        pdf.text(
            "AI Media Monitoring & Analysis",
            15,
            y
        );

        y += 9;

        pdf.setFontSize(11);
        pdf.setFont("helvetica", "normal");

        pdf.text(
            truncatePDFText(
                title,
                95
            ),
            15,
            y
        );

        y += 8;

        pdf.setDrawColor(210, 214, 220);

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
                    ai,
                    "summary",
                    "executive_summary"
                )
            ],

            [
                "Sentiment",
                getField(
                    ai,
                    "sentiment"
                )
            ],

            [
                "Main Issue",
                getField(
                    ai,
                    "main_issue",
                    "mainIssue",
                    "isu_utama"
                )
            ],

            [
                "Key Points",
                getField(
                    ai,
                    "key_points",
                    "keyPoints"
                )
            ],

            [
                "Media Analysis",
                getField(
                    ai,
                    "media_analysis",
                    "mediaAnalysis",
                    "analisis_media"
                )
            ],

            [
                "Communication Risk",
                getField(
                    ai,
                    "communication_risk",
                    "communicationRisk",
                    "risiko_komunikasi"
                )
            ],

            [
                "Recommendations",
                getField(
                    ai,
                    "recommendations",
                    "recommendation",
                    "rekomendasi"
                )
            ],

            [
                "Critical Analysis",
                getField(
                    ai,
                    "critical_analysis",
                    "criticalAnalysis"
                )
            ],

            [
                "Implications",
                getField(
                    ai,
                    "implications",
                    "implication"
                )
            ],

            [
                "Takeaways",
                getField(
                    ai,
                    "takeaways",
                    "key_takeaways"
                )
            ]
        ];

        for (const [
            sectionTitle,
            value
        ] of sections) {
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
                    value,
                    y
                );

            if (y > 270) {
                pdf.addPage();
                y = 18;
            }
        }

        /* Footer */

        const pageCount =
            pdf.internal
                .getNumberOfPages();

        for (
            let page = 1;
            page <= pageCount;
            page++
        ) {
            pdf.setPage(page);

            pdf.setFontSize(8);
            pdf.setFont(
                "helvetica",
                "normal"
            );

            pdf.setTextColor(
                120,
                120,
                120
            );

            pdf.text(
                `AI Media Monitoring & Analysis — Page ${page} of ${pageCount}`,
                15,
                287
            );
        }

        const safeName =
            sanitizeFileName(
                title
            );

        pdf.save(
            `${safeName}_AI_Analysis.pdf`
        );

        showStatus(
            "PDF exported successfully.",
            "success"
        );
    } catch (error) {
        console.error(
            "PDF export error:",
            error
        );

        showStatus(
            "Failed to export PDF.",
            "error"
        );
    }
}

/* ============================================================
   ADD PDF SECTION
   ============================================================ */

function addPDFSection(
    pdf,
    title,
    value,
    y
) {
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

    const text =
        plainTextFromValue(
            getLanguageData(value)
        );

    const lines =
        pdf.splitTextToSize(
            text,
            178
        );

    for (const line of lines) {
        if (y > 278) {
            pdf.addPage();
            y = 18;

            pdf.setFontSize(9);
            pdf.setFont(
                "helvetica",
                "normal"
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
   PLAIN TEXT FROM VALUE
   ============================================================ */

function plainTextFromValue(value) {
    if (
        value === null ||
        value === undefined
    ) {
        return "";
    }

    if (Array.isArray(value)) {
        return value
            .map(
                item =>
                    "• " +
                    plainTextFromValue(
                        item
                    )
            )
            .join("\n");
    }

    if (
        typeof value === "object"
    ) {
        return Object.entries(value)
            .map(
                ([key, item]) =>
                    `${formatLabel(key)}: ${plainTextFromValue(item)}`
            )
            .join("\n");
    }

    return String(value);
}

/* ============================================================
   TRUNCATE PDF TEXT
   ============================================================ */

function truncatePDFText(
    text,
    maxLength
) {
    text = String(text || "");

    if (
        text.length <= maxLength
    ) {
        return text;
    }

    return (
        text.substring(
            0,
            maxLength - 3
        ) + "..."
    );
}

/* ============================================================
   SANITIZE FILE NAME
   ============================================================ */

function sanitizeFileName(name) {
    return String(name || "video")
        .replace(/[<>:"/\\|?*]+/g, "")
        .replace(/\s+/g, "_")
        .substring(0, 100);
}

/* ============================================================
   OPTIONAL KEYBOARD SHORTCUT
   ============================================================ */

document.addEventListener(
    "keydown",
    event => {
        if (
            event.ctrlKey &&
            event.key === "Enter"
        ) {
            analyzeVideo();
        }
    }
);

/* ============================================================
   END
   ============================================================ */
