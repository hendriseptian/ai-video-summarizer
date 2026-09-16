/* ============================================================
   AI VIDEO SUMMARIZER
   SCRIPT.JS - STABLE V3
   ============================================================ */


/* ============================================================
   CONFIGURATION
   ============================================================ */

const API_URL =
    "https://ai-video-summarizer.hendriseptian25.workers.dev/analyze";


/* ============================================================
   GLOBAL STATE
   ============================================================ */

let currentData = null;
let currentAIRoot = null;
let currentLanguage = "en";


/* ============================================================
   YOUTUBE URL VALIDATION
   ============================================================ */

function isValidYouTubeUrl(value) {

    if (!value) {
        return false;
    }

    try {

        const url = new URL(value.trim());

        const hostname =
            url.hostname.toLowerCase();

        return (
            hostname === "youtube.com" ||
            hostname === "www.youtube.com" ||
            hostname === "m.youtube.com" ||
            hostname === "youtu.be" ||
            hostname === "www.youtu.be"
        );

    } catch (error) {

        return false;

    }

}


/*
 * Compatibility alias.
 *
 * Some older code may still call isYouTubeUrl().
 * Keep this alias so old references cannot break
 * the application.
 */

function isYouTubeUrl(value) {

    return isValidYouTubeUrl(value);

}


/* ============================================================
   START APPLICATION
   ============================================================ */

window.addEventListener(
    "DOMContentLoaded",
    function () {

        const analyzeButton =
            document.getElementById(
                "analyzeButton"
            );

        const videoUrl =
            document.getElementById(
                "videoUrl"
            );

        const aiResult =
            document.getElementById(
                "aiResult"
            );


        /*
         * ANALYZE BUTTON
         */

        if (analyzeButton) {

            analyzeButton.onclick =
                function () {

                    analyzeVideo();

                };

        } else {

            console.error(
                "ANALYZE button not found."
            );

        }


        /*
         * ENTER KEY
         */

        if (videoUrl) {

            videoUrl.onkeydown =
                function (event) {

                    if (
                        event.key === "Enter"
                    ) {

                        event.preventDefault();

                        analyzeVideo();

                    }

                };

        }


        /*
         * IMPORTANT:
         *
         * Language buttons are generated dynamically
         * inside #aiResult.
         *
         * Therefore we DO NOT attach click handlers
         * directly to EN/ID buttons.
         *
         * We use ONE event listener on #aiResult.
         *
         * This makes EN / ID switching stable.
         */

        if (aiResult) {

            aiResult.onclick =
                function (event) {

                    const languageButton =
                        event.target.closest(
                            "[data-language]"
                        );

                    if (
                        languageButton &&
                        aiResult.contains(
                            languageButton
                        )
                    ) {

                        const language =
                            languageButton.dataset.language;

                        switchLanguage(
                            language
                        );

                        return;

                    }


                    const pdfButton =
                        event.target.closest(
                            "[data-action='export-pdf']"
                        );

                    if (
                        pdfButton &&
                        aiResult.contains(
                            pdfButton
                        )
                    ) {

                        exportPDF();

                    }

                };

        }

    }
);


/* ============================================================
   ANALYZE VIDEO
   ============================================================ */

async function analyzeVideo() {

    const videoUrlInput =
        document.getElementById(
            "videoUrl"
        );

    const analyzeButton =
        document.getElementById(
            "analyzeButton"
        );

    const status =
        document.getElementById(
            "status"
        );

    const videoInfo =
        document.getElementById(
            "videoInfo"
        );

    const transcript =
        document.getElementById(
            "transcript"
        );

    const aiResult =
        document.getElementById(
            "aiResult"
        );


    const url =
        videoUrlInput
            ? videoUrlInput.value.trim()
            : "";


    /* --------------------------------------------------------
       VALIDATION
       -------------------------------------------------------- */

    if (!url) {

        setStatus(
            status,
            "Please enter a YouTube URL.",
            "error"
        );

        return;

    }


    if (!isValidYouTubeUrl(url)) {

        setStatus(
            status,
            "Please enter a valid YouTube URL.",
            "error"
        );

        return;

    }


    /* --------------------------------------------------------
       LOADING
       -------------------------------------------------------- */

    if (analyzeButton) {

        analyzeButton.disabled = true;

        analyzeButton.dataset.oldText =
            analyzeButton.textContent;

        analyzeButton.textContent =
            "ANALYZING...";

    }


    setStatus(
        status,
        "Analyzing video. Please wait...",
        "loading"
    );


    if (videoInfo) {

        videoInfo.innerHTML = `
            <div class="empty-state">
                Loading video information...
            </div>
        `;

    }


    if (transcript) {

        transcript.innerHTML = `
            <div class="empty-state">
                Loading transcript...
            </div>
        `;

    }


    if (aiResult) {

        aiResult.innerHTML = "";

    }


    /*
     * Reset language.
     *
     * Every new analysis starts in EN.
     */

    currentLanguage = "en";

    currentData = null;
    currentAIRoot = null;


    /* --------------------------------------------------------
       API REQUEST
       -------------------------------------------------------- */

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


        const text =
            await response.text();


        let data;


        try {

            data =
                JSON.parse(text);

        } catch (error) {

            console.error(
                "Server response:",
                text
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


        /* ----------------------------------------------------
           SAVE RESPONSE
           ---------------------------------------------------- */

        currentData =
            data;


        currentAIRoot =
            findAIRoot(data);


        if (!currentAIRoot) {

            console.error(
                "AI data not found:",
                data
            );

            throw new Error(
                "AI analysis result was not found in server response."
            );

        }


        /*
         * Make sure EN exists.
         *
         * If EN is unavailable but ID exists,
         * automatically use ID.
         */

        if (
            currentAIRoot.en
        ) {

            currentLanguage = "en";

        } else if (
            currentAIRoot.id
        ) {

            currentLanguage = "id";

        }


        /* ----------------------------------------------------
           RENDER VIDEO INFORMATION
           ---------------------------------------------------- */

        renderVideoInfo(
            data
        );


        /* ----------------------------------------------------
           RENDER TRANSCRIPT
           ---------------------------------------------------- */

        renderTranscript(
            data
        );


        /* ----------------------------------------------------
           RENDER AI
           ---------------------------------------------------- */

        renderAI();


        /* ----------------------------------------------------
           SUCCESS
           ---------------------------------------------------- */

        setStatus(
            status,
            "Analysis completed successfully.",
            "success"
        );


    } catch (error) {

        console.error(
            "Analyze error:",
            error
        );


        setStatus(
            status,
            error.message ||
                "Failed to analyze video.",
            "error"
        );


        if (videoInfo) {

            videoInfo.innerHTML = `
                <div class="error-box">
                    ${escapeHTML(
                        error.message ||
                        "Failed to analyze video."
                    )}
                </div>
            `;

        }


    } finally {

        if (analyzeButton) {

            analyzeButton.disabled =
                false;

            analyzeButton.textContent =
                analyzeButton.dataset.oldText ||
                "ANALYZE";

        }

    }

}


/* ============================================================
   FIND AI ROOT
   ============================================================ */

function findAIRoot(data) {

    if (!data) {

        return null;

    }


    /*
     * Main V2 response:
     *
     * {
     *     status: "success",
     *     video: {...},
     *     transcript: {...},
     *     ai: {
     *         en: {...},
     *         id: {...}
     *     }
     * }
     */

    if (
        data.ai &&
        typeof data.ai === "object"
    ) {

        return data.ai;

    }


    if (
        data.analysis &&
        typeof data.analysis === "object"
    ) {

        return data.analysis;

    }


    if (
        data.result &&
        typeof data.result === "object"
    ) {

        /*
         * If result contains en/id directly,
         * return result.
         */

        if (
            data.result.en ||
            data.result.id
        ) {

            return data.result;

        }

    }


    if (
        data.ai_result &&
        typeof data.ai_result === "object"
    ) {

        return data.ai_result;

    }


    /*
     * Fallback:
     * data itself may already be the AI object.
     */

    if (
        data.summary ||
        data.key_points ||
        data.sentiment ||
        data.main_issue
    ) {

        return data;

    }


    return recursiveAI(
        data
    );

}


/* ============================================================
   RECURSIVE AI FINDER
   ============================================================ */

function recursiveAI(
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


    /*
     * Language structure
     */

    if (
        object.en ||
        object.id
    ) {

        return object;

    }


    /*
     * AI language block
     */

    if (
        object.summary ||
        object.key_points ||
        object.sentiment ||
        object.main_issue ||
        object.media_analysis
    ) {

        return object;

    }


    for (
        const key in object
    ) {

        if (
            !Object.prototype.hasOwnProperty.call(
                object,
                key
            )
        ) {

            continue;

        }


        const value =
            object[key];


        if (
            value &&
            typeof value === "object"
        ) {

            const result =
                recursiveAI(
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
   LANGUAGE DATA
   ============================================================ */

function getLanguageData(
    root
) {

    if (
        !root ||
        typeof root !== "object"
    ) {

        return null;

    }


    /*
     * Normal V2 structure:
     *
     * root.en
     * root.id
     */

    if (
        root.en ||
        root.id
    ) {

        if (
            currentLanguage === "id" &&
            root.id
        ) {

            return root.id;

        }


        if (
            currentLanguage === "en" &&
            root.en
        ) {

            return root.en;

        }


        /*
         * Fallback
         */

        return (
            root.en ||
            root.id ||
            null
        );

    }


    /*
     * Root is already one language block.
     */

    return root;

}


/* ============================================================
   LANGUAGE SWITCH
   ============================================================ */

function switchLanguage(
    language
) {

    /*
     * Ignore invalid language.
     */

    if (
        language !== "en" &&
        language !== "id"
    ) {

        return;

    }


    /*
     * Do nothing if there is no AI data.
     */

    if (!currentAIRoot) {

        return;

    }


    /*
     * Check requested language exists.
     */

    if (
        !currentAIRoot[language]
    ) {

        console.warn(
            "Language data not available:",
            language
        );

        return;

    }


    /*
     * THIS IS THE IMPORTANT PART.
     *
     * Only change state.
     *
     * DO NOT call API.
     */

    currentLanguage =
        language;


    /*
     * Re-render using the already
     * downloaded AI data.
     */

    renderAI();

}


/* ============================================================
   VIDEO INFORMATION
   ============================================================ */

function renderVideoInfo(
    data
) {

    const box =
        document.getElementById(
            "videoInfo"
        );


    if (!box) {

        return;

    }


    const video =
        data.video || {};


    const transcript =
        data.transcript || {};


    const title =
        video.title ||
        transcript.title ||
        data.title ||
        "Untitled Video";


    const language =
        transcript.language ||
        video.language ||
        data.language ||
        "-";


    const input =
        document.getElementById(
            "videoUrl"
        );


    const inputUrl =
        input
            ? input.value.trim()
            : "";


    const id =
        video.id ||
        data.video_id ||
        extractYouTubeId(
            video.url ||
            data.url ||
            inputUrl
        );


    const url =
        video.url ||
        data.url ||
        inputUrl;


    box.innerHTML = `

        <div class="meta-grid">

            <div class="meta-item">

                <strong>
                    Title
                </strong>

                <span>
                    ${escapeHTML(
                        title
                    )}
                </span>

            </div>


            <div class="meta-item">

                <strong>
                    Video ID
                </strong>

                <span>
                    ${escapeHTML(
                        id || "-"
                    )}
                </span>

            </div>


            <div class="meta-item">

                <strong>
                    Language
                </strong>

                <span>
                    ${escapeHTML(
                        language
                    )}
                </span>

            </div>


            <div class="meta-item">

                <strong>
                    URL
                </strong>

                <span>
                    ${escapeHTML(
                        url
                    )}
                </span>

            </div>

        </div>

    `;

}


/* ============================================================
   AI RESULT
   ============================================================ */

function renderAI() {

    const box =
        document.getElementById(
            "aiResult"
        );


    if (!box) {

        return;

    }


    if (
        !currentAIRoot ||
        typeof currentAIRoot !== "object"
    ) {

        box.innerHTML = `
            <div class="error-box">
                AI analysis data is empty.
            </div>
        `;

        return;

    }


    /*
     * Get ONLY the currently selected language.
     */

    const ai =
        getLanguageData(
            currentAIRoot
        );


    if (
        !ai ||
        typeof ai !== "object"
    ) {

        box.innerHTML = `
            <div class="error-box">
                AI analysis data is empty.
            </div>
        `;

        return;

    }


    const summary =
        field(
            ai,
            [
                "summary",
                "executive_summary"
            ]
        );


    const sentiment =
        field(
            ai,
            [
                "sentiment"
            ]
        );


    const mainIssue =
        field(
            ai,
            [
                "main_issue",
                "mainIssue",
                "isu_utama"
            ]
        );


    const keyPoints =
        field(
            ai,
            [
                "key_points",
                "keyPoints"
            ]
        );


    const mediaAnalysis =
        field(
            ai,
            [
                "media_analysis",
                "mediaAnalysis",
                "analisis_media"
            ]
        );


    const risk =
        field(
            ai,
            [
                "communication_risk",
                "communicationRisk",
                "risiko_komunikasi"
            ]
        );


    const recommendations =
        field(
            ai,
            [
                "recommendations",
                "recommendation",
                "rekomendasi"
            ]
        );


    const critical =
        field(
            ai,
            [
                "critical_analysis",
                "criticalAnalysis"
            ]
        );


    const implications =
        field(
            ai,
            [
                "implications",
                "implication"
            ]
        );


    const takeaways =
        field(
            ai,
            [
                "takeaways",
                "key_takeaways"
            ]
        );


    /*
     * IMPORTANT:
     *
     * EN/ID buttons use data-language.
     *
     * We DO NOT attach individual listeners here.
     *
     * The single listener is already attached
     * to #aiResult during DOMContentLoaded.
     */

    box.innerHTML = `

        <div class="result-toolbar">

            <div class="toolbar-actions">

                <button
                    id="languageEn"
                    class="lang-btn ${
                        currentLanguage === "en"
                            ? "active"
                            : ""
                    }"
                    type="button"
                    data-language="en">

                    EN

                </button>


                <button
                    id="languageId"
                    class="lang-btn ${
                        currentLanguage === "id"
                            ? "active"
                            : ""
                    }"
                    type="button"
                    data-language="id">

                    ID

                </button>


                <button
                    id="exportPdfButton"
                    class="export-btn"
                    type="button"
                    data-action="export-pdf">

                    Export PDF

                </button>

            </div>

        </div>


        <div class="analysis-grid">

            ${summaryCard(
                summary
            )}


            ${sentimentCard(
                sentiment
            )}


            ${issueCard(
                mainIssue
            )}


            ${keyPointCard(
                keyPoints
            )}


            ${mediaCard(
                mediaAnalysis
            )}


            ${riskCard(
                risk
            )}


            ${recommendationCard(
                recommendations
            )}


            ${textCard(
                "Critical Analysis",
                critical
            )}


            ${textCard(
                "Implications",
                implications
            )}


            ${textCard(
                "Takeaways",
                takeaways
            )}

        </div>

    `;

}


/* ============================================================
   FIELD
   ============================================================ */

function field(
    object,
    keys
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
   SUMMARY CARD
   ============================================================ */

function summaryCard(
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

            <h3>
                Summary
            </h3>

            <div class="summary-text">

                ${renderValue(
                    value
                )}

            </div>

        </article>

    `;

}


/* ============================================================
   SENTIMENT CARD
   ============================================================ */

function sentimentCard(
    value
) {

    if (!value) {

        return "";

    }


    let text =
        value;


    if (
        typeof value === "object"
    ) {

        text =
            value.label ||
            value.value ||
            value.result ||
            value.sentiment ||
            "";

    }


    text =
        String(text);


    const lower =
        text.toLowerCase();


    let css =
        "sentiment-neutral";


    if (
        lower.includes(
            "positive"
        ) ||
        lower.includes(
            "positif"
        )
    ) {

        css =
            "sentiment-positive";

    }


    if (
        lower.includes(
            "negative"
        ) ||
        lower.includes(
            "negatif"
        )
    ) {

        css =
            "sentiment-negative";

    }


    return `

        <article class="
            analysis-card
        ">

            <h3>
                Sentiment
            </h3>

            <span class="
                sentiment-badge
                ${css}
            ">

                ${escapeHTML(
                    text
                )}

            </span>

        </article>

    `;

}


/* ============================================================
   ISSUE CARD
   ============================================================ */

function issueCard(
    value
) {

    if (!value) {

        return "";

    }


    return `

        <article class="
            analysis-card
        ">

            <h3>
                Isu Utama
            </h3>

            <div class="main-issue">

                ${renderValue(
                    value
                )}

            </div>

        </article>

    `;

}


/* ============================================================
   KEY POINTS
   ============================================================ */

function keyPointCard(
    value
) {

    if (!value) {

        return "";

    }


    const items =
        normalizeList(
            value
        );


    return `

        <article class="
            analysis-card
        ">

            <h3>
                Key Points
            </h3>

            <ul class="
                key-points-list
            ">

                ${items
                    .map(
                        item => `
                            <li>
                                ${renderValue(
                                    item
                                )}
                            </li>
                        `
                    )
                    .join("")
                }

            </ul>

        </article>

    `;

}


/* ============================================================
   MEDIA ANALYSIS
   ============================================================ */

function mediaCard(
    value
) {

    if (!value) {

        return "";

    }


    /*
     * If media analysis is plain text.
     */

    if (
        typeof value !== "object" ||
        Array.isArray(value)
    ) {

        return `

            <article class="
                analysis-card
                full-width
            ">

                <h3>
                    Analisis Media
                </h3>

                ${renderValue(
                    value
                )}

            </article>

        `;

    }


    const items = [

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


    items.forEach(
        function (item) {

            const valueFound =
                field(
                    value,
                    item[1]
                );


            if (
                valueFound !== null
            ) {

                html += `

                    <div class="
                        media-analysis-item
                    ">

                        <strong>
                            ${item[0]}
                        </strong>

                        ${renderValue(
                            valueFound
                        )}

                    </div>

                `;

            }

        }
    );


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
                Analisis Media
            </h3>

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

function riskCard(
    value
) {

    if (!value) {

        return "";

    }


    let level =
        value;


    let reason =
        null;


    let escalation =
        null;


    if (
        typeof value === "object"
    ) {

        level =
            field(
                value,
                [
                    "level",
                    "risk_level",
                    "risk",
                    "tingkat"
                ]
            );


        reason =
            field(
                value,
                [
                    "reason",
                    "alasan"
                ]
            );


        escalation =
            field(
                value,
                [
                    "escalation",
                    "potential_escalation",
                    "potensi_eskalasi"
                ]
            );

    }


    const text =
        String(
            level || "-"
        );


    const lower =
        text.toLowerCase();


    let css =
        "risk-low";


    if (
        lower.includes(
            "high"
        ) ||
        lower.includes(
            "tinggi"
        )
    ) {

        css =
            "risk-high";

    } else if (
        lower.includes(
            "medium"
        ) ||
        lower.includes(
            "sedang"
        ) ||
        lower.includes(
            "moderate"
        )
    ) {

        css =
            "risk-medium";

    }


    return `

        <article class="
            analysis-card
        ">

            <h3>
                Risiko Komunikasi
            </h3>


            <span class="
                risk-badge
                ${css}
            ">

                ${escapeHTML(
                    text
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

                            ${renderValue(
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

                            ${renderValue(
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
   RECOMMENDATION
   ============================================================ */

function recommendationCard(
    value
) {

    if (!value) {

        return "";

    }


    if (
        Array.isArray(value)
    ) {

        return `

            <article class="
                analysis-card
                full-width
            ">

                <h3>
                    Rekomendasi
                </h3>

                <ul>

                    ${value
                        .map(
                            item => `
                                <li>
                                    ${renderValue(
                                        item
                                    )}
                                </li>
                            `
                        )
                        .join("")
                    }

                </ul>

            </article>

        `;

    }


    if (
        typeof value !== "object"
    ) {

        return `

            <article class="
                analysis-card
                full-width
            ">

                <h3>
                    Rekomendasi
                </h3>

                ${renderValue(
                    value
                )}

            </article>

        `;

    }


    const items = [

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


    items.forEach(
        function (item) {

            const found =
                field(
                    value,
                    item[1]
                );


            if (
                found !== null
            ) {

                html += `

                    <div class="
                        recommendation-item
                    ">

                        <strong>
                            ${item[0]}
                        </strong>

                        ${renderValue(
                            found
                        )}

                    </div>

                `;

            }

        }
    );


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
                Rekomendasi
            </h3>

            <div class="
                recommendations
            ">

                ${html}

            </div>

        </article>

    `;

}


/* ============================================================
   TEXT CARD
   ============================================================ */

function textCard(
    title,
    value
) {

    if (!value) {

        return "";

    }


    return `

        <article class="
            analysis-card
        ">

            <h3>
                ${escapeHTML(
                    title
                )}
            </h3>

            ${renderValue(
                value
            )}

        </article>

    `;

}


/* ============================================================
   RENDER VALUE
   ============================================================ */

function renderValue(
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

        return `

            <ul>

                ${value
                    .map(
                        item => `
                            <li>
                                ${renderValue(
                                    item
                                )}
                            </li>
                        `
                    )
                    .join("")
                }

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


    /*
     * Inference formatting.
     */

    if (
        /^Inference:/i.test(
            text
        )
    ) {

        return `

            <div class="inference">

                <span class="
                    inference-label
                ">

                    Inference:

                </span>

                ${escapeHTML(
                    text.replace(
                        /^Inference:\s*/i,
                        ""
                    )
                )}

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

        return "";

    }


    let html = "";


    Object.entries(
        object
    ).forEach(
        function ([
            key,
            value
        ]) {

            html += `

                <div class="
                    media-analysis-item
                ">

                    <strong>
                        ${escapeHTML(
                            formatLabel(
                                key
                            )
                        )}
                    </strong>

                    ${renderValue(
                        value
                    )}

                </div>

            `;

        }
    );


    return html;

}


/* ============================================================
   NORMALIZE LIST
   ============================================================ */

function normalizeList(
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

        const list =
            value.items ||
            value.points ||
            value.list ||
            value.values;


        if (
            Array.isArray(list)
        ) {

            return list;

        }

    }


    if (
        typeof value === "string"
    ) {

        return value
            .split("\n")
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
            function (char) {

                return char.toUpperCase();

            }
        );

}


/* ============================================================
   TRANSCRIPT
   ============================================================ */

function renderTranscript(
    data
) {

    const box =
        document.getElementById(
            "transcript"
        );


    if (!box) {

        return;

    }


    const transcript =
        data.transcript || {};


    const segments =
        transcript.transcript ||
        transcript.segments ||
        data.segments ||
        [];


    /*
     * Transcript returned as plain text.
     */

    if (
        typeof segments === "string"
    ) {

        box.innerHTML = `

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

        box.innerHTML = `
            <div class="empty-state">
                Transcript unavailable.
            </div>
        `;

        return;

    }


    box.innerHTML =
        segments
            .map(
                function (
                    segment,
                    index
                ) {

                    const text =
                        typeof segment === "string"
                            ? segment
                            : segment.text || "";


                    const start =
                        typeof segment === "object"
                            ? segment.start
                            : index * 2;


                    return `

                        <div class="
                            transcript-row
                        ">

                            <div class="
                                transcript-time
                            ">

                                ${formatTime(
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
   FORMAT TIME
   ============================================================ */

function formatTime(
    seconds
) {

    seconds =
        Math.floor(
            Number(seconds) || 0
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


    if (
        hours > 0
    ) {

        return (
            String(hours)
                .padStart(2, "0") +
            ":" +
            String(minutes)
                .padStart(2, "0") +
            ":" +
            String(secs)
                .padStart(2, "0")
        );

    }


    return (
        String(minutes)
            .padStart(2, "0") +
        ":" +
        String(secs)
            .padStart(2, "0")
    );

}


/* ============================================================
   EXPORT PDF
   ============================================================ */

function exportPDF() {

    if (
        !currentData ||
        !currentAIRoot
    ) {

        alert(
            "Please analyze a video first."
        );

        return;

    }


    if (
        !window.jspdf ||
        !window.jspdf.jsPDF
    ) {

        alert(
            "PDF library is not available."
        );

        return;

    }


    const {
        jsPDF
    } = window.jspdf;


    const pdf =
        new jsPDF();


    /*
     * IMPORTANT:
     *
     * PDF uses the SAME language currently
     * displayed on screen.
     */

    const ai =
        getLanguageData(
            currentAIRoot
        );


    const transcript =
        currentData.transcript ||
        {};


    const title =
        transcript.title ||
        currentData.video?.title ||
        "AI Video Analysis";


    let y = 18;


    pdf.setFontSize(
        18
    );


    pdf.setFont(
        "helvetica",
        "bold"
    );


    pdf.text(
        "AI Video Summarizer",
        15,
        y
    );


    y += 8;


    pdf.setFontSize(
        11
    );


    pdf.setFont(
        "helvetica",
        "normal"
    );


    const titleLines =
        pdf.splitTextToSize(
            String(title),
            180
        );


    pdf.text(
        titleLines,
        15,
        y
    );


    y +=
        titleLines.length * 5 +
        8;


    const sections = [

        [
            "Summary",
            field(
                ai,
                [
                    "summary",
                    "executive_summary"
                ]
            )
        ],

        [
            "Sentiment",
            field(
                ai,
                [
                    "sentiment"
                ]
            )
        ],

        [
            "Isu Utama",
            field(
                ai,
                [
                    "main_issue",
                    "mainIssue",
                    "isu_utama"
                ]
            )
        ],

        [
            "Key Points",
            field(
                ai,
                [
                    "key_points",
                    "keyPoints"
                ]
            )
        ],

        [
            "Analisis Media",
            field(
                ai,
                [
                    "media_analysis",
                    "mediaAnalysis",
                    "analisis_media"
                ]
            )
        ],

        [
            "Risiko Komunikasi",
            field(
                ai,
                [
                    "communication_risk",
                    "communicationRisk",
                    "risiko_komunikasi"
                ]
            )
        ],

        [
            "Rekomendasi",
            field(
                ai,
                [
                    "recommendations",
                    "recommendation",
                    "rekomendasi"
                ]
            )
        ],

        [
            "Critical Analysis",
            field(
                ai,
                [
                    "critical_analysis",
                    "criticalAnalysis"
                ]
            )
        ],

        [
            "Implications",
            field(
                ai,
                [
                    "implications",
                    "implication"
                ]
            )
        ],

        [
            "Takeaways",
            field(
                ai,
                [
                    "takeaways",
                    "key_takeaways"
                ]
            )
        ]

    ];


    sections.forEach(
        function (section) {

            if (
                section[1] === null ||
                section[1] === undefined
            ) {

                return;

            }


            if (
                y > 270
            ) {

                pdf.addPage();

                y = 18;

            }


            pdf.setFontSize(
                12
            );


            pdf.setFont(
                "helvetica",
                "bold"
            );


            pdf.text(
                section[0],
                15,
                y
            );


            y += 6;


            pdf.setFontSize(
                9
            );


            pdf.setFont(
                "helvetica",
                "normal"
            );


            const lines =
                pdf.splitTextToSize(
                    valueToText(
                        section[1]
                    ),
                    178
                );


            lines.forEach(
                function (line) {

                    if (
                        y > 278
                    ) {

                        pdf.addPage();

                        y = 18;

                    }


                    pdf.text(
                        line,
                        15,
                        y
                    );


                    y += 4.5;

                }
            );


            y += 5;

        }
    );


    /* --------------------------------------------------------
       PDF WATERMARK / FOOTER
       Applied to every page after all content is generated.
       This does not change the analysis data or consume AI
       neurons because it is handled entirely in the browser.
       -------------------------------------------------------- */

    const totalPages =
        pdf.internal.getNumberOfPages();

    for (
        let pageNumber = 1;
        pageNumber <= totalPages;
        pageNumber++
    ) {

        pdf.setPage(
            pageNumber
        );

        const pageWidth =
            pdf.internal.pageSize.getWidth();

        const pageHeight =
            pdf.internal.pageSize.getHeight();

        /* Light CONFIDENTIAL watermark */
        pdf.saveGraphicsState();

        pdf.setTextColor(
            225,
            225,
            225
        );

        pdf.setFont(
            "helvetica",
            "bold"
        );

        pdf.setFontSize(
            28
        );

        pdf.text(
            "CONFIDENTIAL",
            pageWidth / 2,
            pageHeight / 2,
            {
                align: "center",
                angle: 45
            }
        );

        pdf.restoreGraphicsState();

        /* Footer watermark */
        pdf.setDrawColor(
            205,
            205,
            205
        );

        pdf.setLineWidth(
            0.3
        );

        pdf.line(
            15,
            pageHeight - 20,
            pageWidth - 15,
            pageHeight - 20
        );

        pdf.setTextColor(
            110,
            110,
            110
        );

        pdf.setFont(
            "helvetica",
            "normal"
        );

        pdf.setFontSize(
            7.5
        );

        pdf.text(
            "AI Video Summarizer  •  CONFIDENTIAL",
            15,
            pageHeight - 14
        );

        pdf.text(
            "Generated for: hendri@company.com",
            15,
            pageHeight - 9.5
        );

        pdf.text(
            "Developed & Maintained by Hendri Septian",
            pageWidth - 15,
            pageHeight - 9.5,
            {
                align: "right"
            }
        );

        pdf.setTextColor(
            0,
            0,
            0
        );

    }


    pdf.save(
        sanitizeFileName(
            title
        ) +
        "_" +
        currentLanguage.toUpperCase() +
        "_AI_Analysis.pdf"
    );

}


/* ============================================================
   PDF TEXT
   ============================================================ */

function valueToText(
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
                    valueToText(
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
            function ([
                key,
                item
            ]) {

                return (
                    formatLabel(key) +
                    ": " +
                    valueToText(item)
                );

            }
        )
        .join("\n");

    }


    return String(value);

}


/* ============================================================
   STATUS
   ============================================================ */

function setStatus(
    element,
    message,
    type
) {

    if (!element) {

        return;

    }


    element.className =
        type || "";


    element.textContent =
        message || "";

}


/* ============================================================
   EXTRACT YOUTUBE ID
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


        const hostname =
            parsed.hostname
                .toLowerCase();


        /*
         * youtu.be/VIDEO_ID
         */

        if (
            hostname === "youtu.be" ||
            hostname === "www.youtu.be"
        ) {

            return parsed.pathname
                .replace(
                    /^\/+/,
                    ""
                )
                .split("/")[0];

        }


        /*
         * youtube.com/watch?v=VIDEO_ID
         */

        return (
            parsed.searchParams
                .get("v") ||
            ""
        );

    } catch {

        return "";

    }

}


/* ============================================================
   ERROR MESSAGE
   ============================================================ */

function getErrorMessage(
    data,
    status
) {

    if (
        data &&
        typeof data.detail ===
            "string"
    ) {

        return data.detail;

    }


    if (
        data &&
        typeof data.error ===
            "string"
    ) {

        return data.error;

    }


    if (
        data &&
        typeof data.message ===
            "string"
    ) {

        return data.message;

    }


    return (
        "Server error (" +
        status +
        ")."
    );

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
   SANITIZE FILE NAME
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
