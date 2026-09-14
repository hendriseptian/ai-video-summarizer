const API_URL =
    "https://ai-video-summarizer.hendriseptian25.workers.dev/analyze";

let currentLanguage = "en";
let currentAIData = null;
let currentVideoData = null;
let currentTranscriptData = null;

document.addEventListener("DOMContentLoaded", () => {
    initializeApplication();
});

function initializeApplication() {
    const analyzeButton = document.getElementById("analyzeButton");
    const videoUrlInput = document.getElementById("videoUrl");

    if (!analyzeButton || !videoUrlInput) {
        console.error("Required HTML elements were not found.");
        return;
    }

    analyzeButton.addEventListener("click", analyzeVideo);

    videoUrlInput.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
            analyzeVideo();
        }
    });

    createLanguageSelector();
    createPdfButton();
}

/* ============================================================
   MAIN ANALYSIS
   ============================================================ */

async function analyzeVideo() {
    const videoUrlInput = document.getElementById("videoUrl");
    const analyzeButton = document.getElementById("analyzeButton");
    const statusElement = document.getElementById("status");

    if (!videoUrlInput || !analyzeButton || !statusElement) {
        return;
    }

    const videoUrl = videoUrlInput.value.trim();

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
        const response = await fetch(API_URL, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                video_url: videoUrl
            })
        });

        const rawText = await response.text();

        let data;

        try {
            data = JSON.parse(rawText);
        } catch (jsonError) {
            throw new Error(
                "Server returned an invalid response."
            );
        }

        if (!response.ok) {
            const errorMessage =
                data?.detail ||
                data?.error ||
                data?.message ||
                `Server error: ${response.status}`;

            throw new Error(errorMessage);
        }

        if (!data) {
            throw new Error(
                "Empty response from analysis server."
            );
        }

        currentVideoData = data;
        currentAIData = extractAIData(data);
        currentTranscriptData = getTranscriptData(data);

        console.log("API RESPONSE:", data);
        console.log("AI DATA:", currentAIData);
        console.log("TRANSCRIPT DATA:", currentTranscriptData);
        
        if (!currentAIData) {
            throw new Error(
                "AI analysis result was not found in server response."
            );
        }

        renderVideoInformation(data);
        renderAnalysis(currentLanguage);
        renderTranscript(currentTranscriptData);

        updateLanguageSelector();

        showStatus(
            "Analysis completed successfully.",
            "success"
        );

    } catch (error) {
        console.error("Analysis error:", error);

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
   VALIDATE YOUTUBE URL
   ============================================================ */

function isYouTubeUrl(url) {
    try {
        const parsed = new URL(url);

        const hostname =
            parsed.hostname.toLowerCase();

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

/* ============================================================
   EXTRACT AI DATA
   ============================================================ */

function extractAIData(data) {
    if (!data || typeof data !== "object") {
        return null;
    }

    // ========================================================
    // CURRENT BACKEND RESPONSE
    // Backend returns:
    //
    // {
    //     "status": "success",
    //     "video": {...},
    //     "transcript": {...},
    //     "ai": {
    //         "en": {...},
    //         "id": {...}
    //     },
    //     "processing": {...}
    // }
    // ========================================================

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

    // ========================================================
    // BACKWARD COMPATIBILITY
    // ========================================================

    if (
        data.en &&
        typeof data.en === "object"
    ) {
        return data;
    }

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

    return null;
}

/* ============================================================
   TRANSCRIPT DATA
   ============================================================ */

function getTranscriptData(data) {
    if (!data) {
        return null;
    }

    let transcriptObject = null;

    if (
        data.transcript &&
        typeof data.transcript === "object"
    ) {
        transcriptObject = data.transcript;
    }

    if (
        data.result &&
        data.result.transcript &&
        typeof data.result.transcript === "object"
    ) {
        transcriptObject =
            data.result.transcript;
    }

    if (!transcriptObject) {
        return null;
    }

    let transcript =
        transcriptObject.transcript;

    if (!Array.isArray(transcript)) {
        if (typeof transcript === "string") {
            transcript = [
                {
                    text: transcript,
                    start: 0,
                    duration: 0
                }
            ];
        } else {
            transcript = [];
        }
    }

    return {
        title:
            transcriptObject.title ||
            data.title ||
            "Unknown Video",

        language:
            transcriptObject.language ||
            data.language ||
            "unknown",

        transcript: transcript
    };
}

/* ============================================================
   VIDEO INFORMATION
   ============================================================ */

function renderVideoInformation(data) {
    const videoInfo =
        document.getElementById("videoInfo");

    if (!videoInfo) {
        return;
    }

    const transcriptData =
        getTranscriptData(data);

    const title =
        transcriptData?.title ||
        data.title ||
        "Unknown Video";

    const language =
        transcriptData?.language ||
        data.language ||
        "Unknown";

    const processing =
        data.processing ||
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
                        String(language).toUpperCase()
                    )}
                </span>
            </div>

            <div class="info-item">
                <span class="info-label">
                    TRANSCRIPT SEGMENTS
                </span>
                <span class="info-value">
                    ${escapeHtml(
                        String(totalSegments)
                    )}
                </span>
            </div>

            <div class="info-item">
                <span class="info-label">
                    ANALYSIS CHUNKS
                </span>
                <span class="info-value">
                    ${escapeHtml(
                        String(totalChunks)
                    )}
                </span>
            </div>

            <div class="info-item">
                <span class="info-label">
                    TRANSCRIPT CHARACTERS
                </span>
                <span class="info-value">
                    ${escapeHtml(
                        String(transcriptCharacters)
                    )}
                </span>
            </div>

            <div class="info-item">
                <span class="info-label">
                    TRANSCRIPT HASH
                </span>
                <span class="info-value info-hash">
                    ${escapeHtml(
                        String(transcriptHash)
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
        document.querySelector(".result-card");

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
        document.createElement("div");

    container.id =
        "languageSelectorContainer";

    container.innerHTML = `
        <div class="language-selector-wrapper">

            <label for="languageSelector">
                REPORT LANGUAGE
            </label>

            <select id="languageSelector">
                <option value="en">
                    English
                </option>

                <option value="id">
                    Bahasa Indonesia
                </option>
            </select>

        </div>
    `;

    resultCard.appendChild(container);

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

function handleLanguageChange(event) {
    const selectedLanguage =
        event.target.value;

    if (
        selectedLanguage !== "en" &&
        selectedLanguage !== "id"
    ) {
        return;
    }

    currentLanguage =
        selectedLanguage;

    if (currentAIData) {
        renderAnalysis(currentLanguage);
    }
}

function updateLanguageSelector() {
    const selector =
        document.getElementById(
            "languageSelector"
        );

    if (!selector) {
        return;
    }

    const hasEnglish =
        currentAIData &&
        currentAIData.en;

    const hasIndonesian =
        currentAIData &&
        currentAIData.id;

    selector.disabled =
        !hasEnglish &&
        !hasIndonesian;

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
        currentLanguage = "id";
        selector.value = "id";
    }

    if (
        currentLanguage === "id" &&
        !hasIndonesian &&
        hasEnglish
    ) {
        currentLanguage = "en";
        selector.value = "en";
    }
}

/* ============================================================
   ANALYSIS RENDER
   ============================================================ */

function renderAnalysis(language) {
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

    let analysisContainer =
        document.getElementById(
            "professionalAnalysis"
        );

    if (!analysisContainer) {
        analysisContainer =
            document.createElement("div");

        analysisContainer.id =
            "professionalAnalysis";

        analysisContainer.className =
            "professional-analysis";

        transcriptCard.parentNode.insertBefore(
            analysisContainer,
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

    analysisContainer.innerHTML = `
        <div class="analysis-header">

            <div>
                <h2>
                    PROFESSIONAL CONTENT ANALYSIS
                </h2>

                <p class="analysis-language">
                    ${language === "id"
                        ? "Bahasa Indonesia"
                        : "English"}
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
                ${formatParagraphs(summary)}
            </div>

        </section>

        <section class="analysis-section">

            <h3>
                KEY POINTS
            </h3>

            <div class="numbered-list">
                ${renderNumberedList(
                    keyPoints
                )}
            </div>

        </section>

        <section class="analysis-section">

            <h3>
                CRITICAL ANALYSIS
            </h3>

            <div class="numbered-list">
                ${renderNumberedList(
                    criticalAnalysis
                )}
            </div>

        </section>

        <section class="analysis-section">

            <h3>
                IMPLICATIONS
            </h3>

            <div class="numbered-list">
                ${renderNumberedList(
                    implications
                )}
            </div>

        </section>

        <section class="analysis-section">

            <h3>
                KEY TAKEAWAYS
            </h3>

            <div class="takeaway-list">
                ${renderBulletList(
                    takeaways
                )}
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

function renderNumberedList(items) {
    if (!items || items.length === 0) {
        return `
            <p class="empty-analysis">
                No information available.
            </p>
        `;
    }

    return items
        .map((item, index) => {
            const text =
                normalizeText(item);

            return `
                <div class="analysis-item">

                    <div class="analysis-number">
                        ${String(
                            index + 1
                        ).padStart(2, "0")}
                    </div>

                    <div class="analysis-text">
                        ${formatParagraphs(
                            text
                        )}
                    </div>

                </div>
            `;
        })
        .join("");
}

/* ============================================================
   BULLET LIST
   ============================================================ */

function renderBulletList(items) {
    if (!items || items.length === 0) {
        return `
            <p class="empty-analysis">
                No information available.
            </p>
        `;
    }

    return items
        .map((item) => {
            return `
                <div class="takeaway-item">
                    <span class="takeaway-marker">
                        •
                    </span>

                    <span>
                        ${formatParagraphs(
                            normalizeText(item)
                        )}
                    </span>
                </div>
            `;
        })
        .join("");
}

/* ============================================================
   TRANSCRIPT
   ============================================================ */

function renderTranscript(transcriptData) {
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
            .map((segment, index) => {
                const start =
                    Number(segment.start) || 0;

                const duration =
                    Number(segment.duration) || 0;

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
                            ${formatTimestamp(
                                start
                            )}
                        </div>

                        <div class="transcript-text">
                            ${escapeHtml(
                                text
                            )}
                        </div>

                    </div>
                `;
            })
            .join("");

    transcriptElement.innerHTML = `
        <div class="transcript-toolbar">
            <span>
                ${transcriptData.transcript.length}
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

function formatTimestamp(seconds) {
    seconds =
        Math.max(
            0,
            Math.floor(
                Number(seconds) || 0
            )
        );

    const hours =
        Math.floor(seconds / 3600);

    const minutes =
        Math.floor(
            (seconds % 3600) / 60
        );

    const secs =
        seconds % 60;

    if (hours > 0) {
        return [
            String(hours).padStart(2, "0"),
            String(minutes).padStart(2, "0"),
            String(secs).padStart(2, "0")
        ].join(":");
    }

    return [
        String(minutes).padStart(2, "0"),
        String(secs).padStart(2, "0")
    ].join(":");
}

/* ============================================================
   PDF BUTTON
   ============================================================ */

function createPdfButton() {
    /*
     * PDF button is created inside the analysis section
     * after analysis is completed.
     */
}

/* ============================================================
   LOAD PDF LIBRARY
   ============================================================ */

async function loadPdfLibraries() {
    if (
        window.jspdf &&
        window.jspdf.jsPDF
    ) {
        return true;
    }

    await loadScript(
        "https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js"
    );

    await loadScript(
        "https://cdnjs.cloudflare.com/ajax/libs/jspdf-autotable/3.8.2/jspdf.plugin.autotable.min.js"
    );

    return (
        window.jspdf &&
        window.jspdf.jsPDF
    );
}

function loadScript(src) {
    return new Promise(
        (resolve, reject) => {
            const existing =
                document.querySelector(
                    `script[src="${src}"]`
                );

            if (existing) {
                existing.addEventListener(
                    "load",
                    resolve
                );

                existing.addEventListener(
                    "error",
                    reject
                );

                return;
            }

            const script =
                document.createElement(
                    "script"
                );

            script.src = src;
            script.async = true;

            script.onload =
                () => resolve();

            script.onerror =
                () =>
                    reject(
                        new Error(
                            "Failed to load PDF library."
                        )
                    );

            document.head.appendChild(
                script
            );
        }
    );
}

/* ============================================================
   GENERATE PDF
   ============================================================ */

async function generatePdf() {
    if (
        !currentAIData ||
        !currentVideoData
    ) {
        showStatus(
            "No analysis available for PDF export.",
            "error"
        );

        return;
    }

    const pdfButton =
        document.getElementById(
            "downloadPdfButton"
        );

    if (pdfButton) {
        pdfButton.disabled = true;
        pdfButton.textContent =
            "GENERATING PDF...";
    }

    try {
        const loaded =
            await loadPdfLibraries();

        if (!loaded) {
            throw new Error(
                "PDF library could not be loaded."
            );
        }

        const jsPDF =
            window.jspdf.jsPDF;

        const doc =
            new jsPDF({
                orientation: "portrait",
                unit: "mm",
                format: "a4"
            });

        const report =
            currentAIData[
                currentLanguage
            ];

        const transcriptData =
            currentTranscriptData;

        const title =
            transcriptData?.title ||
            currentVideoData?.title ||
            "AI Video Analysis";

        const margin = 18;

        let y = 20;

        /*
         * COVER / HEADER
         */

        doc.setFontSize(20);
        doc.setFont("helvetica", "bold");

        doc.text(
            "AI VIDEO ANALYSIS REPORT",
            margin,
            y
        );

        y += 12;

        doc.setFontSize(11);
        doc.setFont("helvetica", "normal");

        const titleLines =
            doc.splitTextToSize(
                String(title),
                174
            );

        doc.text(
            titleLines,
            margin,
            y
        );

        y +=
            titleLines.length * 6 +
            8;

        drawPdfLine(
            doc,
            margin,
            y,
            192,
            y
        );

        y += 10;

        /*
         * VIDEO INFORMATION
         */

        addPdfHeading(
            doc,
            "VIDEO INFORMATION",
            margin,
            y
        );

        y += 8;

        const infoRows = [
            [
                "Title",
                String(title)
            ],
            [
                "Language",
                String(
                    transcriptData?.language ||
                    currentVideoData?.language ||
                    "Unknown"
                ).toUpperCase()
            ],
            [
                "URL",
                getVideoUrl()
            ],
            [
                "Analysis Language",
                currentLanguage === "id"
                    ? "Bahasa Indonesia"
                    : "English"
            ]
        ];

        doc.autoTable({
            startY: y,
            head: [
                ["Field", "Value"]
            ],
            body: infoRows,
            margin: {
                left: margin,
                right: margin
            },
            theme: "grid",
            styles: {
                fontSize: 9,
                cellPadding: 3
            },
            headStyles: {
                fontStyle: "bold"
            }
        });

        y =
            doc.lastAutoTable.finalY +
            12;

        /*
         * EXECUTIVE SUMMARY
         */

        y = ensurePdfSpace(
            doc,
            y,
            40
        );

        addPdfHeading(
            doc,
            "EXECUTIVE SUMMARY",
            margin,
            y
        );

        y += 8;

        y =
            addPdfParagraph(
                doc,
                normalizeText(
                    report?.summary
                ),
                margin,
                y,
                174
            );

        y += 6;

        /*
         * KEY POINTS
         */

        y = ensurePdfSpace(
            doc,
            y,
            35
        );

        addPdfHeading(
            doc,
            "KEY POINTS",
            margin,
            y
        );

        y += 8;

        y =
            addPdfNumberedItems(
                doc,
                normalizeArray(
                    report?.key_points
                ),
                margin,
                y
            );

        /*
         * CRITICAL ANALYSIS
         */

        y = ensurePdfSpace(
            doc,
            y,
            35
        );

        addPdfHeading(
            doc,
            "CRITICAL ANALYSIS",
            margin,
            y
        );

        y += 8;

        y =
            addPdfNumberedItems(
                doc,
                normalizeArray(
                    report?.critical_analysis
                ),
                margin,
                y
            );

        /*
         * IMPLICATIONS
         */

        y = ensurePdfSpace(
            doc,
            y,
            35
        );

        addPdfHeading(
            doc,
            "IMPLICATIONS",
            margin,
            y
        );

        y += 8;

        y =
            addPdfNumberedItems(
                doc,
                normalizeArray(
                    report?.implications
                ),
                margin,
                y
            );

        /*
         * TAKEAWAYS
         */

        y = ensurePdfSpace(
            doc,
            y,
            35
        );

        addPdfHeading(
            doc,
            "KEY TAKEAWAYS",
            margin,
            y
        );

        y += 8;

        y =
            addPdfBulletItems(
                doc,
                normalizeArray(
                    report?.takeaways
                ),
                margin,
                y
            );

        /*
         * TRANSCRIPT
         */

        y = ensurePdfSpace(
            doc,
            y,
            45
        );

        addPdfHeading(
            doc,
            "SOURCE MATERIAL / TRANSCRIPT",
            margin,
            y
        );

        y += 8;

        const transcriptRows =
            Array.isArray(
                transcriptData?.transcript
            )
                ? transcriptData.transcript.map(
                      (segment) => [
                          formatTimestamp(
                              segment.start
                          ),
                          normalizeText(
                              segment.text
                          )
                      ]
                  )
                : [];

        if (
            transcriptRows.length > 0
        ) {
            doc.autoTable({
                startY: y,
                head: [
                    [
                        "TIME",
                        "TRANSCRIPT"
                    ]
                ],
                body: transcriptRows,
                margin: {
                    left: margin,
                    right: margin
                },
                theme: "grid",
                styles: {
                    fontSize: 7.5,
                    cellPadding: 2,
                    overflow: "linebreak",
                    valign: "top"
                },
                columnStyles: {
                    0: {
                        cellWidth: 22
                    },
                    1: {
                        cellWidth: 152
                    }
                },
                headStyles: {
                    fontStyle: "bold"
                }
            });
        } else {
            addPdfParagraph(
                doc,
                "Transcript is not available.",
                margin,
                y,
                174
            );
        }

        /*
         * FOOTER
         */

        addPdfFooter(
            doc
        );

        /*
         * FILE NAME
         */

        const filename =
            createPdfFilename(
                title,
                currentLanguage
            );

        doc.save(filename);

        showStatus(
            "PDF generated successfully.",
            "success"
        );

    } catch (error) {
        console.error(
            "PDF generation error:",
            error
        );

        showStatus(
            error.message ||
            "Failed to generate PDF.",
            "error"
        );

    } finally {
        if (pdfButton) {
            pdfButton.disabled = false;
            pdfButton.textContent =
                "DOWNLOAD PDF";
        }
    }
}

/* ============================================================
   PDF HELPERS
   ============================================================ */

function addPdfHeading(
    doc,
    text,
    x,
    y
) {
    doc.setFont(
        "helvetica",
        "bold"
    );

    doc.setFontSize(11);

    doc.text(
        String(text),
        x,
        y
    );
}

function addPdfParagraph(
    doc,
    text,
    x,
    y,
    width
) {
    if (!text) {
        return y;
    }

    doc.setFont(
        "helvetica",
        "normal"
    );

    doc.setFontSize(9);

    const lines =
        doc.splitTextToSize(
            String(text),
            width
        );

    doc.text(
        lines,
        x,
        y
    );

    return (
        y +
        lines.length * 4.5
    );
}

function addPdfNumberedItems(
    doc,
    items,
    x,
    y
) {
    if (
        !items ||
        items.length === 0
    ) {
        return addPdfParagraph(
            doc,
            "No information available.",
            x,
            y,
            174
        );
    }

    items.forEach(
        (item, index) => {
            y = ensurePdfSpace(
                doc,
                y,
                25
            );

            doc.setFont(
                "helvetica",
                "bold"
            );

            doc.setFontSize(9);

            const number =
                `${String(
                    index + 1
                ).padStart(2, "0")}.`;

            doc.text(
                number,
                x,
                y
            );

            const textX =
                x + 9;

            y =
                addPdfParagraph(
                    doc,
                    normalizeText(item),
                    textX,
                    y,
                    165
                );

            y += 4;
        }
    );

    return y;
}

function addPdfBulletItems(
    doc,
    items,
    x,
    y
) {
    if (
        !items ||
        items.length === 0
    ) {
        return addPdfParagraph(
            doc,
            "No information available.",
            x,
            y,
            174
        );
    }

    items.forEach(
        (item) => {
            y = ensurePdfSpace(
                doc,
                y,
                20
            );

            doc.setFont(
                "helvetica",
                "normal"
            );

            doc.setFontSize(9);

            doc.text(
                "•",
                x,
                y
            );

            y =
                addPdfParagraph(
                    doc,
                    normalizeText(item),
                    x + 6,
                    y,
                    168
                );

            y += 3;
        }
    );

    return y;
}

function ensurePdfSpace(
    doc,
    y,
    requiredSpace
) {
    const pageHeight =
        doc.internal.pageSize.height;

    if (
        y + requiredSpace >
        pageHeight - 20
    ) {
        doc.addPage();
        return 20;
    }

    return y;
}

function drawPdfLine(
    doc,
    x1,
    y1,
    x2,
    y2
) {
    doc.setLineWidth(0.3);

    doc.line(
        x1,
        y1,
        x2,
        y2
    );
}

function addPdfFooter(doc) {
    const pageCount =
        doc.internal.getNumberOfPages();

    for (
        let page = 1;
        page <= pageCount;
        page++
    ) {
        doc.setPage(page);

        const pageHeight =
            doc.internal.pageSize.height;

        doc.setFont(
            "helvetica",
            "normal"
        );

        doc.setFontSize(7);

        doc.text(
            "AI Video Summarizer",
            18,
            pageHeight - 10
        );

        doc.text(
            `Page ${page} of ${pageCount}`,
            192,
            pageHeight - 10,
            {
                align: "right"
            }
        );
    }
}

function createPdfFilename(
    title,
    language
) {
    let cleanTitle =
        String(title || "video")
            .replace(
                /[<>:"/\\|?*]+/g,
                ""
            )
            .replace(
                /\s+/g,
                " "
            )
            .trim();

    if (
        cleanTitle.length > 80
    ) {
        cleanTitle =
            cleanTitle.substring(
                0,
                80
            );
    }

    return (
        `AI_Video_Analysis_${cleanTitle}_${language.toUpperCase()}.pdf`
    );
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
   CLEAR PREVIOUS RESULTS
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
                ${escapeHtml(
                    message
                )}
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
        <section class="analysis-section">

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
   NORMALIZATION
   ============================================================ */

function normalizeArray(value) {
    if (!value) {
        return [];
    }

    if (Array.isArray(value)) {
        return value
            .map((item) => {
                return normalizeText(
                    item
                );
            })
            .filter(
                (item) => item.length > 0
            );
    }

    if (
        typeof value === "string"
    ) {
        return value
            .split(/\n+/)
            .map((item) =>
                normalizeText(item)
            )
            .filter(
                (item) =>
                    item.length > 0
            );
    }

    return [
        normalizeText(value)
    ].filter(
        (item) => item.length > 0
    );
}

function normalizeText(value) {
    if (
        value === null ||
        value === undefined
    ) {
        return "";
    }

    if (
        typeof value === "string"
    ) {
        return cleanAIFormatting(
            value
        );
    }

    if (
        typeof value === "number" ||
        typeof value === "boolean"
    ) {
        return String(value);
    }

    if (
        typeof value === "object"
    ) {
        /*
         * Protect the frontend from
         * accidentally displaying:
         *
         * {'issue': '...', 'reason': '...'}
         *
         * or:
         *
         * {"issue":"..."}
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

            if (
                issue &&
                reason
            ) {
                return cleanAIFormatting(
                    `${issue} ${reason}`
                );
            }

            return cleanAIFormatting(
                issue || reason
            );
        }

        try {
            return cleanAIFormatting(
                JSON.stringify(value)
            );
        } catch (error) {
            return String(value);
        }
    }

    return String(value);
}

function cleanAIFormatting(
    text
) {
    return String(text)
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
        .replace(
            /^\s*[-*]\s+/gm,
            ""
        )
        .trim();
}

/* ============================================================
   HTML FORMATTING
   ============================================================ */

function formatParagraphs(
    text
) {
    const normalized =
        normalizeText(text);

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
                        ${escapeHtml(
                            paragraph.trim()
                        )}
                    </p>
                `;
            }
        )
        .join("");
}

/* ============================================================
   ESCAPE HTML
   ============================================================ */

function escapeHtml(value) {
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
   VIDEO URL
   ============================================================ */

function getVideoUrl() {
    const input =
        document.getElementById(
            "videoUrl"
        );

    if (!input) {
        return "";
    }

    return input.value.trim();
}

/* ============================================================
   CONSOLE INFORMATION
   ============================================================ */

console.log(
    "AI Video Summarizer script loaded."
);
console.log(
    "API:",
    API_URL
);
