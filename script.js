const API_URL =
    "https://ai-video-summarizer.hendriseptian25.workers.dev/analyze";

let currentLanguage = "en";
let currentAIData = null;
let currentVideoData = null;
let currentTranscriptData = null;
let currentRawResponse = null;


/* ============================================================
   INITIALIZE
   ============================================================ */

document.addEventListener("DOMContentLoaded", () => {
    initializeApplication();
});


function initializeApplication() {

    const analyzeButton =
        document.getElementById("analyzeButton");

    const videoUrlInput =
        document.getElementById("videoUrl");

    if (!analyzeButton || !videoUrlInput) {

        console.error(
            "Required HTML elements were not found."
        );

        return;
    }

    analyzeButton.addEventListener(
        "click",
        analyzeVideo
    );

    videoUrlInput.addEventListener(
        "keydown",
        (event) => {

            if (event.key === "Enter") {
                analyzeVideo();
            }

        }
    );

    createLanguageSelector();
}


/* ============================================================
   ANALYZE VIDEO
   ============================================================ */

async function analyzeVideo() {

    const videoUrlInput =
        document.getElementById("videoUrl");

    const analyzeButton =
        document.getElementById("analyzeButton");

    if (!videoUrlInput || !analyzeButton) {
        return;
    }

    const videoUrl =
        videoUrlInput.value.trim();


    if (!videoUrl) {

        showStatus(
            "YouTube URL is required.",
            "error"
        );

        return;
    }


    if (!isYouTubeUrl(videoUrl)) {

        showStatus(
            "Please enter a valid YouTube URL.",
            "error"
        );

        return;
    }


    setLoadingState(true);

    clearPreviousResults();


    showStatus(
        "Analyzing video. Please wait...",
        "loading"
    );


    try {

        console.log(
            "========================================"
        );

        console.log(
            "AI VIDEO SUMMARIZER"
        );

        console.log(
            "Sending request to:",
            API_URL
        );

        console.log(
            "Video URL:",
            videoUrl
        );


        const response =
            await fetch(
                API_URL,
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json",

                        "Accept":
                            "application/json"
                    },

                    body: JSON.stringify({
                        video_url:
                            videoUrl
                    })
                }
            );


        const rawText =
            await response.text();


        console.log(
            "HTTP STATUS:",
            response.status
        );

        console.log(
            "RAW RESPONSE:",
            rawText
        );


        let data;


        try {

            data =
                JSON.parse(rawText);

        } catch (jsonError) {

            console.error(
                "JSON PARSE ERROR:",
                jsonError
            );

            throw new Error(
                "Server returned invalid JSON."
            );
        }


        console.log(
            "PARSED RESPONSE:",
            data
        );


        if (!response.ok) {

            const errorMessage =
                data?.detail ||
                data?.error ||
                data?.message ||
                `Server error: ${response.status}`;

            throw new Error(
                errorMessage
            );
        }


        /*
         * SAVE COMPLETE RESPONSE
         */

        currentRawResponse =
            data;


        /*
         * UNWRAP RESPONSE
         */

        const normalizedData =
            unwrapResponse(data);


        console.log(
            "NORMALIZED RESPONSE:",
            normalizedData
        );


        /*
         * EXTRACT DATA
         */

        currentVideoData =
            normalizedData;


        currentAIData =
            extractAIData(
                normalizedData
            );


        currentTranscriptData =
            getTranscriptData(
                normalizedData
            );


        console.log(
            "========================================"
        );

        console.log(
            "EXTRACTED AI DATA:",
            currentAIData
        );

        console.log(
            "EXTRACTED TRANSCRIPT:",
            currentTranscriptData
        );


        /*
         * VALIDATE AI
         */

        if (!currentAIData) {

            const keys =
                getResponseKeys(
                    data
                );


            console.error(
                "AI DATA NOT FOUND."
            );

            console.error(
                "Response keys:",
                keys
            );


            throw new Error(
                "AI analysis result was not found. " +
                "Response keys received: " +
                keys.join(", ")
            );
        }


        /*
         * RENDER
         */

        renderVideoInformation(
            normalizedData
        );


        renderAnalysis(
            currentLanguage
        );


        renderTranscript(
            currentTranscriptData
        );


        updateLanguageSelector();


        showStatus(
            "Analysis completed successfully.",
            "success"
        );


    } catch (error) {

        console.error(
            "========================================"
        );

        console.error(
            "ANALYSIS ERROR"
        );

        console.error(
            error
        );


        showStatus(
            error.message ||
            "Failed to analyze video.",
            "error"
        );


        renderErrorResult(
            error.message ||
            "An unexpected error occurred."
        );


    } finally {

        setLoadingState(false);
    }
}


/* ============================================================
   UNWRAP RESPONSE
   ============================================================ */

function unwrapResponse(data) {

    if (!data) {
        return null;
    }


    /*
     * Direct response
     */

    if (
        data.ai ||
        data.transcript ||
        data.video
    ) {

        return data;
    }


    /*
     * Common wrappers
     */

    if (
        data.data &&
        typeof data.data === "object"
    ) {

        if (
            data.data.ai ||
            data.data.transcript ||
            data.data.video
        ) {

            return data.data;
        }
    }


    if (
        data.result &&
        typeof data.result === "object"
    ) {

        if (
            data.result.ai ||
            data.result.transcript ||
            data.result.video
        ) {

            return data.result;
        }
    }


    if (
        data.response &&
        typeof data.response === "object"
    ) {

        if (
            data.response.ai ||
            data.response.transcript ||
            data.response.video
        ) {

            return data.response;
        }
    }


    return data;
}


/* ============================================================
   EXTRACT AI DATA
   ============================================================ */

function extractAIData(data) {

    if (!data) {
        return null;
    }


    /*
     * DIRECT BACKEND FORMAT
     *
     * data.ai
     */

    if (
        data.ai &&
        typeof data.ai === "object"
    ) {

        if (
            data.ai.en ||
            data.ai.id
        ) {

            return data.ai;
        }
    }


    /*
     * data.data.ai
     */

    if (
        data.data &&
        typeof data.data === "object"
    ) {

        if (
            data.data.ai &&
            typeof data.data.ai === "object"
        ) {

            if (
                data.data.ai.en ||
                data.data.ai.id
            ) {

                return data.data.ai;
            }
        }
    }


    /*
     * data.result.ai
     */

    if (
        data.result &&
        typeof data.result === "object"
    ) {

        if (
            data.result.ai &&
            typeof data.result.ai === "object"
        ) {

            if (
                data.result.ai.en ||
                data.result.ai.id
            ) {

                return data.result.ai;
            }
        }
    }


    /*
     * data.analysis
     */

    if (
        data.analysis &&
        typeof data.analysis === "object"
    ) {

        if (
            data.analysis.en ||
            data.analysis.id
        ) {

            return data.analysis;
        }
    }


    /*
     * data.result
     */

    if (
        data.result &&
        typeof data.result === "object"
    ) {

        if (
            data.result.en ||
            data.result.id
        ) {

            return data.result;
        }
    }


    /*
     * DIRECT EN / ID
     */

    if (
        data.en &&
        typeof data.en === "object"
    ) {

        return data;
    }


    /*
     * RECURSIVE SEARCH
     *
     * Search deeper if Cloudflare
     * wraps the response.
     */

    const found =
        findAIObject(
            data
        );


    if (found) {
        return found;
    }


    return null;
}


/* ============================================================
   RECURSIVE AI SEARCH
   ============================================================ */

function findAIObject(
    object,
    depth = 0
) {

    if (
        !object ||
        typeof object !== "object"
    ) {

        return null;
    }


    /*
     * Prevent infinite recursion
     */

    if (depth > 8) {
        return null;
    }


    /*
     * Detect EN / ID object
     */

    if (
        object.en &&
        typeof object.en === "object"
    ) {

        const en =
            object.en;

        const id =
            object.id;


        /*
         * Check whether this really
         * looks like our AI report.
         */

        if (
            en.summary ||
            en.key_points ||
            en.critical_analysis ||
            en.implications ||
            en.takeaways
        ) {

            return {
                en:
                    en,

                id:
                    id ||
                    null
            };
        }
    }


    /*
     * Search child objects
     */

    const keys =
        Object.keys(
            object
        );


    for (
        const key of keys
    ) {

        const value =
            object[key];


        if (
            value &&
            typeof value === "object"
        ) {

            const result =
                findAIObject(
                    value,
                    depth + 1
                );


            if (result) {
                return result;
            }
        }
    }


    return null;
}


/* ============================================================
   TRANSCRIPT
   ============================================================ */

function getTranscriptData(data) {

    if (!data) {
        return null;
    }


    /*
     * Direct transcript
     */

    if (
        data.transcript &&
        typeof data.transcript === "object"
    ) {

        return normalizeTranscriptObject(
            data.transcript
        );
    }


    /*
     * data.data.transcript
     */

    if (
        data.data &&
        data.data.transcript
    ) {

        return normalizeTranscriptObject(
            data.data.transcript
        );
    }


    /*
     * data.result.transcript
     */

    if (
        data.result &&
        data.result.transcript
    ) {

        return normalizeTranscriptObject(
            data.result.transcript
        );
    }


    /*
     * Recursive fallback
     */

    const transcript =
        findTranscriptObject(
            data
        );


    if (transcript) {
        return transcript;
    }


    return null;
}


/* ============================================================
   NORMALIZE TRANSCRIPT
   ============================================================ */

function normalizeTranscriptObject(
    object
) {

    if (!object) {
        return null;
    }


    let transcript =
        object.transcript;


    if (
        !Array.isArray(
            transcript
        )
    ) {

        if (
            typeof transcript ===
            "string"
        ) {

            transcript = [
                {
                    text:
                        transcript,

                    start:
                        0,

                    duration:
                        0
                }
            ];

        } else {

            transcript = [];
        }
    }


    return {

        title:
            object.title ||
            "Unknown Video",

        language:
            object.language ||
            "unknown",

        transcript:
            transcript
    };
}


/* ============================================================
   FIND TRANSCRIPT
   ============================================================ */

function findTranscriptObject(
    object,
    depth = 0
) {

    if (
        !object ||
        typeof object !== "object"
    ) {

        return null;
    }


    if (depth > 8) {
        return null;
    }


    if (
        Array.isArray(
            object.transcript
        )
    ) {

        return normalizeTranscriptObject(
            object
        );
    }


    for (
        const key of Object.keys(
            object
        )
    ) {

        const value =
            object[key];


        if (
            value &&
            typeof value === "object"
        ) {

            const result =
                findTranscriptObject(
                    value,
                    depth + 1
                );


            if (result) {
                return result;
            }
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

    const videoInfo =
        document.getElementById(
            "videoInfo"
        );


    if (!videoInfo) {
        return;
    }


    const transcriptData =
        getTranscriptData(
            data
        );


    const title =
        transcriptData?.title ||
        data?.title ||
        "Unknown Video";


    const language =
        transcriptData?.language ||
        data?.language ||
        "Unknown";


    const processing =
        data?.processing ||
        {};


    const totalSegments =
        processing.total_segments ??
        transcriptData?.transcript?.length ??
        0;


    const totalChunks =
        processing.total_chunks ??
        "-";


    const transcriptCharacters =
        processing.transcript_characters ??
        "-";


    const transcriptHash =
        processing.transcript_hash ||
        "-";


    videoInfo.innerHTML = `

        <div class="video-info-grid">

            <div class="info-item">

                <span class="info-label">
                    TITLE
                </span>

                <span class="info-value">
                    ${escapeHtml(title)}
                </span>

            </div>


            <div class="info-item">

                <span class="info-label">
                    LANGUAGE
                </span>

                <span class="info-value">
                    ${escapeHtml(
                        String(
                            language
                        ).toUpperCase()
                    )}
                </span>

            </div>


            <div class="info-item">

                <span class="info-label">
                    TRANSCRIPT SEGMENTS
                </span>

                <span class="info-value">
                    ${escapeHtml(
                        String(
                            totalSegments
                        )
                    )}
                </span>

            </div>


            <div class="info-item">

                <span class="info-label">
                    ANALYSIS CHUNKS
                </span>

                <span class="info-value">
                    ${escapeHtml(
                        String(
                            totalChunks
                        )
                    )}
                </span>

            </div>


            <div class="info-item">

                <span class="info-label">
                    TRANSCRIPT CHARACTERS
                </span>

                <span class="info-value">
                    ${escapeHtml(
                        String(
                            transcriptCharacters
                        )
                    )}
                </span>

            </div>


            <div class="info-item">

                <span class="info-label">
                    TRANSCRIPT HASH
                </span>

                <span class="info-value info-hash">
                    ${escapeHtml(
                        String(
                            transcriptHash
                        )
                    )}
                </span>

            </div>

        </div>
    `;
}


/* ============================================================
   LANGUAGE SELECTOR
   ============================================================ */

function createLanguageSelector() {

    const resultCard =
        document.querySelector(
            ".result-card"
        );


    if (!resultCard) {
        return;
    }


    if (
        document.getElementById(
            "languageSelectorContainer"
        )
    ) {

        return;
    }


    const container =
        document.createElement(
            "div"
        );


    container.id =
        "languageSelectorContainer";


    container.innerHTML = `

        <div class="language-selector-wrapper">

            <label
                for="languageSelector"
            >
                REPORT LANGUAGE
            </label>


            <select
                id="languageSelector"
            >

                <option value="en">
                    English
                </option>

                <option value="id">
                    Bahasa Indonesia
                </option>

            </select>

        </div>
    `;


    resultCard.appendChild(
        container
    );


    const selector =
        document.getElementById(
            "languageSelector"
        );


    if (selector) {

        selector.addEventListener(
            "change",
            handleLanguageChange
        );
    }
}


/* ============================================================
   LANGUAGE CHANGE
   ============================================================ */

function handleLanguageChange(
    event
) {

    const language =
        event.target.value;


    if (
        language !== "en" &&
        language !== "id"
    ) {

        return;
    }


    currentLanguage =
        language;


    if (currentAIData) {

        renderAnalysis(
            currentLanguage
        );
    }
}


/* ============================================================
   UPDATE LANGUAGE SELECTOR
   ============================================================ */

function updateLanguageSelector() {

    const selector =
        document.getElementById(
            "languageSelector"
        );


    if (!selector) {
        return;
    }


    const hasEnglish =
        !!currentAIData?.en;


    const hasIndonesian =
        !!currentAIData?.id;


    const englishOption =
        selector.querySelector(
            'option[value="en"]'
        );


    const indonesianOption =
        selector.querySelector(
            'option[value="id"]'
        );


    if (englishOption) {

        englishOption.disabled =
            !hasEnglish;
    }


    if (indonesianOption) {

        indonesianOption.disabled =
            !hasIndonesian;
    }


    if (
        currentLanguage === "en" &&
        !hasEnglish &&
        hasIndonesian
    ) {

        currentLanguage =
            "id";

        selector.value =
            "id";
    }


    if (
        currentLanguage === "id" &&
        !hasIndonesian &&
        hasEnglish
    ) {

        currentLanguage =
            "en";

        selector.value =
            "en";
    }
}


/* ============================================================
   RENDER ANALYSIS
   ============================================================ */

function renderAnalysis(
    language
) {

    const report =
        currentAIData?.[language];


    if (!report) {

        renderMissingAnalysis();

        return;
    }


    const transcriptCard =
        document.querySelector(
            ".transcript-card"
        );


    if (!transcriptCard) {
        return;
    }


    let container =
        document.getElementById(
            "professionalAnalysis"
        );


    if (!container) {

        container =
            document.createElement(
                "div"
            );


        container.id =
            "professionalAnalysis";


        container.className =
            "professional-analysis";


        transcriptCard.parentNode.insertBefore(
            container,
            transcriptCard
        );
    }


    const summary =
        normalizeText(
            report.summary
        );


    const keyPoints =
        normalizeArray(
            report.key_points
        );


    const criticalAnalysis =
        normalizeArray(
            report.critical_analysis
        );


    const implications =
        normalizeArray(
            report.implications
        );


    const takeaways =
        normalizeArray(
            report.takeaways
        );


    container.innerHTML = `

        <div class="analysis-header">

            <div>

                <h2>
                    PROFESSIONAL CONTENT ANALYSIS
                </h2>

                <p class="analysis-language">
                    ${
                        language === "id"
                            ? "Bahasa Indonesia"
                            : "English"
                    }
                </p>

            </div>


            <button
                id="downloadPdfButton"
                class="pdf-button"
                type="button"
            >
                DOWNLOAD PDF
            </button>

        </div>


        <section class="analysis-section">

            <h3>
                EXECUTIVE SUMMARY
            </h3>

            <div class="summary-content">

                ${
                    formatParagraphs(
                        summary
                    )
                }

            </div>

        </section>


        <section class="analysis-section">

            <h3>
                KEY POINTS
            </h3>

            <div class="numbered-list">

                ${
                    renderNumberedList(
                        keyPoints
                    )
                }

            </div>

        </section>


        <section class="analysis-section">

            <h3>
                CRITICAL ANALYSIS
            </h3>

            <div class="numbered-list">

                ${
                    renderNumberedList(
                        criticalAnalysis
                    )
                }

            </div>

        </section>


        <section class="analysis-section">

            <h3>
                IMPLICATIONS
            </h3>

            <div class="numbered-list">

                ${
                    renderNumberedList(
                        implications
                    )
                }

            </div>

        </section>


        <section class="analysis-section">

            <h3>
                KEY TAKEAWAYS
            </h3>

            <div class="takeaway-list">

                ${
                    renderBulletList(
                        takeaways
                    )
                }

            </div>

        </section>
    `;


    const pdfButton =
        document.getElementById(
            "downloadPdfButton"
        );


    if (pdfButton) {

        pdfButton.addEventListener(
            "click",
            generatePdf
        );
    }
}


/* ============================================================
   NUMBERED LIST
   ============================================================ */

function renderNumberedList(
    items
) {

    if (
        !items ||
        items.length === 0
    ) {

        return `
            <p class="empty-analysis">
                No information available.
            </p>
        `;
    }


    return items
        .map(
            (item, index) => {

                return `

                    <div class="analysis-item">

                        <div class="analysis-number">

                            ${
                                String(
                                    index + 1
                                ).padStart(
                                    2,
                                    "0"
                                )
                            }

                        </div>


                        <div class="analysis-text">

                            ${
                                formatParagraphs(
                                    item
                                )
                            }

                        </div>

                    </div>
                `;
            }
        )
        .join("");
}


/* ============================================================
   BULLET LIST
   ============================================================ */

function renderBulletList(
    items
) {

    if (
        !items ||
        items.length === 0
    ) {

        return `
            <p class="empty-analysis">
                No information available.
            </p>
        `;
    }


    return items
        .map(
            (item) => {

                return `

                    <div class="takeaway-item">

                        <span class="takeaway-marker">
                            •
                        </span>

                        <span>
                            ${
                                formatParagraphs(
                                    item
                                )
                            }
                        </span>

                    </div>
                `;
            }
        )
        .join("");
}


/* ============================================================
   TRANSCRIPT
   ============================================================ */

function renderTranscript(
    transcriptData
) {

    const transcriptElement =
        document.getElementById(
            "transcript"
        );


    if (!transcriptElement) {
        return;
    }


    if (
        !transcriptData ||
        !Array.isArray(
            transcriptData.transcript
        ) ||
        transcriptData.transcript.length === 0
    ) {

        transcriptElement.innerHTML = `

            <p>
                Transcript is not available.
            </p>

        `;

        return;
    }


    const rows =
        transcriptData.transcript
            .map(
                (
                    segment,
                    index
                ) => {

                    const start =
                        Number(
                            segment.start
                        ) || 0;


                    const text =
                        normalizeText(
                            segment.text
                        );


                    return `

                        <div
                            class="transcript-row"
                            data-index="${index}"
                        >

                            <div class="transcript-time">

                                ${
                                    formatTimestamp(
                                        start
                                    )
                                }

                            </div>


                            <div class="transcript-text">

                                ${
                                    escapeHtml(
                                        text
                                    )
                                }

                            </div>

                        </div>
                    `;
                }
            )
            .join("");


    transcriptElement.innerHTML = `

        <div class="transcript-toolbar">

            <span>

                ${
                    transcriptData
                        .transcript
                        .length
                }

                segments

            </span>

        </div>


        <div class="transcript-scroll">

            ${rows}

        </div>
    `;
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
                Number(
                    seconds
                ) || 0
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
            String(hours).padStart(
                2,
                "0"
            ),

            String(minutes).padStart(
                2,
                "0"
            ),

            String(secs).padStart(
                2,
                "0"
            )
        ].join(":");
    }


    return [
        String(minutes).padStart(
            2,
            "0"
        ),

        String(secs).padStart(
            2,
            "0"
        )
    ].join(":");
}


/* ============================================================
   NORMALIZE ARRAY
   ============================================================ */

function normalizeArray(
    value
) {

    if (!value) {
        return [];
    }


    if (Array.isArray(value)) {

        return value
            .map(
                (item) =>
                    normalizeText(
                        item
                    )
            )
            .filter(
                (item) =>
                    item.length > 0
            );
    }


    if (
        typeof value ===
        "string"
    ) {

        return value
            .split(/\n+/)
            .map(
                (item) =>
                    normalizeText(
                        item
                    )
            )
            .filter(
                (item) =>
                    item.length > 0
            );
    }


    return [
        normalizeText(
            value
        )
    ].filter(
        (item) =>
            item.length > 0
    );
}


/* ============================================================
   NORMALIZE TEXT
   ============================================================ */

function normalizeText(
    value
) {

    if (
        value === null ||
        value === undefined
    ) {

        return "";
    }


    if (
        typeof value ===
        "string"
    ) {

        return cleanAIFormatting(
            value
        );
    }


    if (
        typeof value ===
            "number" ||
        typeof value ===
            "boolean"
    ) {

        return String(
            value
        );
    }


    if (
        typeof value ===
        "object"
    ) {

        /*
         * Handle accidental AI object
         */

        if (
            value.issue ||
            value.reason
        ) {

            const issue =
                value.issue
                    ? String(
                        value.issue
                    )
                    : "";


            const reason =
                value.reason
                    ? String(
                        value.reason
                    )
                    : "";


            return cleanAIFormatting(
                `${issue} ${reason}`
            ).trim();
        }


        try {

            return cleanAIFormatting(
                JSON.stringify(
                    value
                )
            );

        } catch (error) {

            return String(
                value
            );
        }
    }


    return String(
        value
    );
}


/* ============================================================
   CLEAN AI FORMATTING
   ============================================================ */

function cleanAIFormatting(
    text
) {

    return String(
        text
    )
        .replace(
            /^\s*```(?:json|text|markdown)?\s*/i,
            ""
        )
        .replace(
            /\s*```\s*$/i,
            ""
        )
        .replace(
            /^\s*\*\*(\d+)\*\*\s*/gm,
            "$1. "
        )
        .trim();
}


/* ============================================================
   FORMAT PARAGRAPHS
   ============================================================ */

function formatParagraphs(
    text
) {

    const normalized =
        normalizeText(
            text
        );


    if (!normalized) {

        return `
            <p class="empty-analysis">
                No information available.
            </p>
        `;
    }


    return normalized
        .split(/\n{2,}/)
        .map(
            (paragraph) => {

                return `
                    <p>
                        ${
                            escapeHtml(
                                paragraph.trim()
                            )
                        }
                    </p>
                `;
            }
        )
        .join("");
}


/* ============================================================
   ESCAPE HTML
   ============================================================ */

function escapeHtml(
    value
) {

    return String(
        value
    )
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
   VALIDATE YOUTUBE URL
   ============================================================ */

function isYouTubeUrl(
    url
) {

    try {

        const parsed =
            new URL(
                url
            );


        const hostname =
            parsed.hostname.toLowerCase();


        return (
            hostname ===
                "youtube.com" ||

            hostname ===
                "www.youtube.com" ||

            hostname ===
                "m.youtube.com" ||

            hostname ===
                "youtu.be" ||

            hostname ===
                "www.youtu.be"
        );

    } catch (error) {

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

    const status =
        document.getElementById(
            "status"
        );


    if (!status) {
        return;
    }


    status.className =
        `status-${type}`;


    status.textContent =
        message;
}


/* ============================================================
   LOADING STATE
   ============================================================ */

function setLoadingState(
    loading
) {

    const button =
        document.getElementById(
            "analyzeButton"
        );


    if (!button) {
        return;
    }


    button.disabled =
        loading;


    if (loading) {

        button.dataset.originalText =
            button.textContent;


        button.textContent =
            "ANALYZING...";

    } else {

        button.textContent =
            button.dataset.originalText ||
            "ANALYZE";
    }
}


/* ============================================================
   CLEAR RESULTS
   ============================================================ */

function clearPreviousResults() {

    const videoInfo =
        document.getElementById(
            "videoInfo"
        );


    const transcript =
        document.getElementById(
            "transcript"
        );


    const analysis =
        document.getElementById(
            "professionalAnalysis"
        );


    if (videoInfo) {

        videoInfo.innerHTML = `
            <p>
                Analyzing video information...
            </p>
        `;
    }


    if (transcript) {

        transcript.innerHTML = `
            <p>
                Processing transcript...
            </p>
        `;
    }


    if (analysis) {

        analysis.remove();
    }


    currentAIData =
        null;

    currentVideoData =
        null;

    currentTranscriptData =
        null;
}


/* ============================================================
   ERROR RESULT
   ============================================================ */

function renderErrorResult(
    message
) {

    const videoInfo =
        document.getElementById(
            "videoInfo"
        );


    if (!videoInfo) {
        return;
    }


    videoInfo.innerHTML = `

        <div class="error-result">

            <strong>
                Analysis failed
            </strong>


            <p>
                ${
                    escapeHtml(
                        message
                    )
                }
            </p>

        </div>
    `;
}


/* ============================================================
   MISSING ANALYSIS
   ============================================================ */

function renderMissingAnalysis() {

    const transcriptCard =
        document.querySelector(
            ".transcript-card"
        );


    if (!transcriptCard) {
        return;
    }


    let container =
        document.getElementById(
            "professionalAnalysis"
        );


    if (!container) {

        container =
            document.createElement(
                "div"
            );


        container.id =
            "professionalAnalysis";


        container.className =
            "professional-analysis";


        transcriptCard.parentNode.insertBefore(
            container,
            transcriptCard
        );
    }


    container.innerHTML = `

        <section
            class="analysis-section"
        >

            <h2>
                PROFESSIONAL CONTENT ANALYSIS
            </h2>


            <p>
                Analysis is not available
                in the selected language.
            </p>

        </section>
    `;
}


/* ============================================================
   RESPONSE DEBUG
   ============================================================ */

function getResponseKeys(
    data
) {

    if (
        !data ||
        typeof data !== "object"
    ) {

        return [
            typeof data
        ];
    }


    return Object.keys(
        data
    );
}


/* ============================================================
   PDF
   ============================================================ */

async function generatePdf() {

    /*
     * PDF export can be added after
     * the API analysis is confirmed working.
     */

    alert(
        "PDF export is ready to be connected after the analysis result is confirmed."
    );
}


/* ============================================================
   CONSOLE
   ============================================================ */

console.log(
    "AI Video Summarizer V7.3 loaded."
);

console.log(
    "API:",
    API_URL
);
