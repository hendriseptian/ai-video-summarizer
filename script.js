// ============================================================
// AI VIDEO SUMMARIZER
// PROFESSIONAL REPORT + PDF EXPORT
// ============================================================

const API_URL =
    "https://ai-video-summarizer.hendriseptian25.workers.dev/analyze";

let currentLanguage = "en";
let currentAIData = null;
let currentVideoData = null;
let currentTranscriptData = null;


// ============================================================
// INITIALIZATION
// ============================================================

document.addEventListener("DOMContentLoaded", function () {
    const analyzeButton = document.getElementById("analyzeButton");

    if (analyzeButton) {
        analyzeButton.addEventListener("click", analyzeVideo);
    }

    injectProfessionalUI();
});


// ============================================================
// MAIN ANALYZE FUNCTION
// ============================================================

async function analyzeVideo() {
    const videoUrlElement = document.getElementById("videoUrl");
    const analyzeButton = document.getElementById("analyzeButton");
    const statusElement = document.getElementById("status");

    if (!videoUrlElement) {
        return;
    }

    const videoUrl = videoUrlElement.value.trim();

    if (!videoUrl) {
        showStatus(
            "Please enter a YouTube video URL.",
            "error"
        );
        return;
    }

    if (!isValidYouTubeUrl(videoUrl)) {
        showStatus(
            "Please enter a valid YouTube URL.",
            "error"
        );
        return;
    }

    if (analyzeButton) {
        analyzeButton.disabled = true;
        analyzeButton.innerText = "ANALYZING...";
    }

    showStatus(
        "Analyzing video transcript. Please wait...",
        "loading"
    );

    clearResults();

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

        let data = null;

        try {
            data = await response.json();
        } catch (jsonError) {
            throw new Error(
                "Server returned an invalid response."
            );
        }

        if (!response.ok) {
            const message =
                data?.message ||
                data?.error ||
                `Server error: ${response.status}`;

            throw new Error(message);
        }

        if (!data) {
            throw new Error("No data returned by server.");
        }

        if (data.status === "error") {
            throw new Error(
                data.message ||
                data.error ||
                "Analysis failed."
            );
        }

        currentVideoData = data;
        currentAIData = data.ai || data.analysis || null;
        currentTranscriptData = getTranscriptData(data);

        if (!currentAIData) {
            throw new Error(
                "AI analysis data was not found in the server response."
            );
        }

        renderAll();

        showStatus(
            "Analysis completed successfully.",
            "success"
        );

    } catch (error) {
        console.error("Analyze error:", error);

        showStatus(
            error.message ||
            "An error occurred while analyzing the video.",
            "error"
        );

        renderError(error.message);

    } finally {
        if (analyzeButton) {
            analyzeButton.disabled = false;
            analyzeButton.innerText = "ANALYZE";
        }
    }
}


// ============================================================
// VALIDATE YOUTUBE URL
// ============================================================

function isValidYouTubeUrl(url) {
    try {
        const parsed = new URL(url);

        const hostname =
            parsed.hostname.toLowerCase();

        return (
            hostname.includes("youtube.com") ||
            hostname.includes("youtu.be")
        );

    } catch (error) {
        return false;
    }
}


// ============================================================
// TRANSCRIPT DATA NORMALIZATION
// ============================================================

function getTranscriptData(data) {

    // Current backend structure
    if (
        data &&
        data.transcript &&
        typeof data.transcript === "object" &&
        !Array.isArray(data.transcript)
    ) {
        return {
            title:
                data.transcript.title ||
                data.title ||
                "Untitled Video",

            language:
                data.transcript.language ||
                data.language ||
                "unknown",

            transcript:
                Array.isArray(data.transcript.transcript)
                    ? data.transcript.transcript
                    : []
        };
    }

    // Fallback structure
    if (
        data &&
        Array.isArray(data.transcript)
    ) {
        return {
            title:
                data.title ||
                "Untitled Video",

            language:
                data.language ||
                "unknown",

            transcript:
                data.transcript
        };
    }

    return {
        title:
            data?.title ||
            "Untitled Video",

        language:
            data?.language ||
            "unknown",

        transcript: []
    };
}


// ============================================================
// RENDER ALL
// ============================================================

function renderAll() {

    renderVideoInformation();

    renderAnalysis();

    renderTranscript();

    addExportButton();
}


// ============================================================
// VIDEO INFORMATION
// ============================================================

function renderVideoInformation() {

    const element =
        document.getElementById("videoInfo");

    if (!element) {
        return;
    }

    const transcriptData =
        currentTranscriptData || {};

    const title =
        transcriptData.title ||
        currentVideoData?.title ||
        "Untitled Video";

    const language =
        transcriptData.language ||
        currentVideoData?.language ||
        "Unknown";

    const segments =
        transcriptData.transcript?.length || 0;

    const processing =
        currentVideoData?.processing || {};

    const totalChunks =
        processing.total_chunks ??
        "-";

    const transcriptCharacters =
        processing.transcript_characters ??
        "-";

    const transcriptHash =
        processing.transcript_hash ??
        "-";

    element.innerHTML = `
        <div class="video-info-grid">

            ${infoItem(
                "TITLE",
                escapeHtml(title)
            )}

            ${infoItem(
                "LANGUAGE",
                escapeHtml(language.toUpperCase())
            )}

            ${infoItem(
                "TRANSCRIPT SEGMENTS",
                formatNumber(segments)
            )}

            ${infoItem(
                "ANALYSIS MODE",
                escapeHtml(
                    processing.mode ||
                    "AI Analysis"
                )
            )}

            ${infoItem(
                "PROCESSING CHUNKS",
                formatNumber(totalChunks)
            )}

            ${infoItem(
                "TRANSCRIPT CHARACTERS",
                formatNumber(transcriptCharacters)
            )}

        </div>

        ${
            transcriptHash
                ? `
                    <div class="hash-container">
                        <span>TRANSCRIPT HASH:</span>
                        <code>${escapeHtml(
                            transcriptHash
                        )}</code>
                    </div>
                `
                : ""
        }
    `;
}


// ============================================================
// ANALYSIS RENDER
// ============================================================

function renderAnalysis() {

    const analysisContainer =
        document.getElementById(
            "professionalAnalysis"
        );

    if (!analysisContainer) {
        return;
    }

    const languageData =
        getLanguageData();

    if (!languageData) {
        analysisContainer.innerHTML = `
            <div class="analysis-empty">
                No analysis data available.
            </div>
        `;

        return;
    }

    analysisContainer.innerHTML = `

        ${renderLanguageSelector()}

        <section class="report-section">

            <div class="section-number">
                01
            </div>

            <div class="section-content">

                <h2>
                    EXECUTIVE SUMMARY
                </h2>

                <div class="summary-box">
                    ${formatProfessionalText(
                        languageData.summary
                    )}
                </div>

            </div>

        </section>


        <section class="report-section">

            <div class="section-number">
                02
            </div>

            <div class="section-content">

                <h2>
                    KEY POINTS
                </h2>

                ${renderList(
                    languageData.key_points
                )}

            </div>

        </section>


        <section class="report-section">

            <div class="section-number">
                03
            </div>

            <div class="section-content">

                <h2>
                    CRITICAL ANALYSIS
                </h2>

                ${renderAnalysisList(
                    languageData.critical_analysis
                )}

            </div>

        </section>


        <section class="report-section">

            <div class="section-number">
                04
            </div>

            <div class="section-content">

                <h2>
                    IMPLICATIONS
                </h2>

                ${renderList(
                    languageData.implications
                )}

            </div>

        </section>


        <section class="report-section">

            <div class="section-number">
                05
            </div>

            <div class="section-content">

                <h2>
                    KEY TAKEAWAYS
                </h2>

                ${renderList(
                    languageData.takeaways
                )}

            </div>

        </section>

    `;
}


// ============================================================
// LANGUAGE SELECTOR
// ============================================================

function renderLanguageSelector() {

    return `
        <div class="language-selector-container">

            <label for="languageSelector">
                REPORT LANGUAGE
            </label>

            <select
                id="languageSelector"
                onchange="changeLanguage(this.value)"
            >

                <option
                    value="en"
                    ${currentLanguage === "en" ? "selected" : ""}
                >
                    ENGLISH
                </option>

                <option
                    value="id"
                    ${currentLanguage === "id" ? "selected" : ""}
                >
                    INDONESIAN
                </option>

            </select>

        </div>
    `;
}


// ============================================================
// CHANGE LANGUAGE
// ============================================================

function changeLanguage(language) {

    if (
        language !== "en" &&
        language !== "id"
    ) {
        return;
    }

    currentLanguage = language;

    renderAnalysis();

    addExportButton();
}


// ============================================================
// GET CURRENT LANGUAGE DATA
// ============================================================

function getLanguageData() {

    if (!currentAIData) {
        return null;
    }

    if (
        currentAIData[currentLanguage]
    ) {
        return currentAIData[currentLanguage];
    }

    // fallback
    if (currentAIData.en) {
        return currentAIData.en;
    }

    if (currentAIData.id) {
        return currentAIData.id;
    }

    return currentAIData;
}


// ============================================================
// RENDER LIST
// ============================================================

function renderList(items) {

    if (!Array.isArray(items)) {

        if (
            typeof items === "string" &&
            items.trim()
        ) {
            return `
                <div class="analysis-text">
                    ${formatProfessionalText(
                        items
                    )}
                </div>
            `;
        }

        return `
            <div class="analysis-empty">
                No information available.
            </div>
        `;
    }

    if (items.length === 0) {
        return `
            <div class="analysis-empty">
                No information available.
            </div>
        `;
    }

    return `
        <ol class="professional-list">

            ${items.map(
                (item, index) => `
                    <li>
                        <div class="list-number">
                            ${String(index + 1).padStart(
                                2,
                                "0"
                            )}
                        </div>

                        <div class="list-content">
                            ${formatProfessionalText(
                                normalizeAIValue(item)
                            )}
                        </div>
                    </li>
                `
            ).join("")}

        </ol>
    `;
}


// ============================================================
// RENDER CRITICAL ANALYSIS
// ============================================================

function renderAnalysisList(items) {

    if (!Array.isArray(items)) {
        return renderList(items);
    }

    if (items.length === 0) {
        return `
            <div class="analysis-empty">
                No critical analysis available.
            </div>
        `;
    }

    return `
        <div class="critical-analysis-list">

            ${items.map(
                (item, index) => `

                    <article class="critical-item">

                        <div class="critical-number">
                            ${String(index + 1).padStart(
                                2,
                                "0"
                            )}
                        </div>

                        <div class="critical-content">

                            ${formatProfessionalText(
                                normalizeAIValue(item)
                            )}

                        </div>

                    </article>

                `
            ).join("")}

        </div>
    `;
}


// ============================================================
// NORMALIZE AI VALUE
// ============================================================

function normalizeAIValue(value) {

    if (value === null || value === undefined) {
        return "";
    }

    if (typeof value === "string") {
        return value;
    }

    if (typeof value === "object") {

        // Handle old accidental object format
        if (
            value.issue ||
            value.reason ||
            value.evidence ||
            value.observation
        ) {

            const parts = [];

            if (value.issue) {
                parts.push(
                    String(value.issue)
                );
            }

            if (value.reason) {
                parts.push(
                    String(value.reason)
                );
            }

            if (value.evidence) {
                parts.push(
                    String(value.evidence)
                );
            }

            if (value.observation) {
                parts.push(
                    String(value.observation)
                );
            }

            return parts.join(" ");
        }

        return Object.values(value)
            .map(item => String(item))
            .join(" ");
    }

    return String(value);
}


// ============================================================
// FORMAT PROFESSIONAL TEXT
// ============================================================

function formatProfessionalText(text) {

    if (!text) {
        return "";
    }

    let output =
        escapeHtml(
            String(text)
        );

    // Bold markdown
    output = output.replace(
        /\*\*(.*?)\*\*/g,
        "<strong>$1</strong>"
    );

    // Convert line breaks
    output =
        output.replace(
            /\n/g,
            "<br>"
        );

    return output;
}


// ============================================================
// TRANSCRIPT RENDER
// ============================================================

function renderTranscript() {

    const element =
        document.getElementById(
            "transcript"
        );

    if (!element) {
        return;
    }

    const transcript =
        currentTranscriptData?.transcript || [];

    if (
        !Array.isArray(transcript) ||
        transcript.length === 0
    ) {
        element.innerHTML = `
            <div class="transcript-empty">
                Transcript is not available.
            </div>
        `;

        return;
    }

    element.innerHTML = `
        <div class="transcript-wrapper">

            <div class="transcript-header">

                <span>
                    SOURCE MATERIAL
                </span>

                <span>
                    ${formatNumber(
                        transcript.length
                    )} SEGMENTS
                </span>

            </div>

            <div class="transcript-scroll">

                ${transcript.map(
                    (segment, index) => {

                        const start =
                            Number(
                                segment.start || 0
                            );

                        const text =
                            segment.text ||
                            "";

                        return `
                            <div class="transcript-row">

                                <div class="transcript-index">
                                    ${String(
                                        index + 1
                                    ).padStart(
                                        3,
                                        "0"
                                    )}
                                </div>

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
                    }
                ).join("")}

            </div>

        </div>
    `;
}


// ============================================================
// ADD EXPORT PDF BUTTON
// ============================================================

function addExportButton() {

    const analysisCard =
        document.querySelector(
            ".result-card"
        );

    if (!analysisCard) {
        return;
    }

    let exportContainer =
        document.getElementById(
            "exportContainer"
        );

    if (!exportContainer) {

        exportContainer =
            document.createElement("div");

        exportContainer.id =
            "exportContainer";

        exportContainer.className =
            "export-container";

        analysisCard.appendChild(
            exportContainer
        );
    }

    exportContainer.innerHTML = `
        <button
            id="exportPdfButton"
            class="export-pdf-button"
            type="button"
            onclick="exportPDF()"
        >
            EXPORT PDF
        </button>

        <span class="export-language">
            ${currentLanguage.toUpperCase()}
        </span>
    `;
}


// ============================================================
// LOAD PDF LIBRARIES
// ============================================================

async function loadPDFLibraries() {

    if (
        window.jspdf &&
        window.jspdf.jsPDF &&
        window.autoTable
    ) {
        return;
    }

    await loadScript(
        "https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js"
    );

    await loadScript(
        "https://cdnjs.cloudflare.com/ajax/libs/jspdf-autotable/3.8.4/jspdf.plugin.autotable.min.js"
    );

    if (
        !window.jspdf ||
        !window.jspdf.jsPDF
    ) {
        throw new Error(
            "jsPDF library could not be loaded."
        );
    }
}


// ============================================================
// DYNAMIC SCRIPT LOADER
// ============================================================

function loadScript(src) {

    return new Promise(
        (resolve, reject) => {

            const existing =
                document.querySelector(
                    `script[src="${src}"]`
                );

            if (existing) {

                if (
                    existing.dataset.loaded ===
                    "true"
                ) {
                    resolve();
                    return;
                }

                existing.addEventListener(
                    "load",
                    () => resolve()
                );

                existing.addEventListener(
                    "error",
                    () =>
                        reject(
                            new Error(
                                "Failed to load PDF library."
                            )
                        )
                );

                return;
            }

            const script =
                document.createElement(
                    "script"
                );

            script.src = src;

            script.async = true;

            script.onload = function () {

                script.dataset.loaded =
                    "true";

                resolve();
            };

            script.onerror = function () {

                reject(
                    new Error(
                        "Failed to load external PDF library."
                    )
                );
            };

            document.head.appendChild(
                script
            );
        }
    );
}


// ============================================================
// EXPORT PDF
// ============================================================

async function exportPDF() {

    if (!currentVideoData) {

        showStatus(
            "Please analyze a video first.",
            "error"
        );

        return;
    }

    const button =
        document.getElementById(
            "exportPdfButton"
        );

    if (button) {

        button.disabled = true;

        button.innerText =
            "GENERATING PDF...";
    }

    showStatus(
        "Generating professional PDF report...",
        "loading"
    );

    try {

        await loadPDFLibraries();

        const jsPDF =
            window.jspdf.jsPDF;

        const doc =
            new jsPDF({
                orientation: "portrait",
                unit: "mm",
                format: "a4"
            });

        configurePDFDocument(doc);

        addPDFCover(doc);

        addPDFExecutiveSummary(doc);

        addPDFKeyPoints(doc);

        addPDFCriticalAnalysis(doc);

        addPDFImplications(doc);

        addPDFTakeaways(doc);

        addPDFTranscript(doc);

        addPDFFooter(doc);

        const title =
            currentTranscriptData?.title ||
            "Video";

        const filename =
            "AI_Video_Analysis_Report_" +
            sanitizeFilename(title) +
            ".pdf";

        doc.save(filename);

        showStatus(
            "PDF report generated successfully.",
            "success"
        );

    } catch (error) {

        console.error(
            "PDF export error:",
            error
        );

        showStatus(
            "Failed to generate PDF: " +
            error.message,
            "error"
        );

    } finally {

        if (button) {

            button.disabled = false;

            button.innerText =
                "EXPORT PDF";
        }
    }
}


// ============================================================
// PDF CONFIGURATION
// ============================================================

function configurePDFDocument(doc) {

    doc.setProperties({
        title:
            "AI Video Analysis Report",

        subject:
            "Professional AI Video Analysis",

        author:
            "AI Video Summarizer",

        creator:
            "AI Video Summarizer",

        keywords:
            "video analysis, AI, transcript, summary"
    });
}


// ============================================================
// PDF COVER / VIDEO INFORMATION
// ============================================================

function addPDFCover(doc) {

    const margin = 18;

    const pageWidth =
        doc.internal.pageSize.getWidth();

    const title =
        currentTranscriptData?.title ||
        "Untitled Video";

    const language =
        currentLanguage === "id"
            ? "INDONESIAN"
            : "ENGLISH";

    // Header
    doc.setFont(
        "helvetica",
        "bold"
    );

    doc.setFontSize(10);

    doc.text(
        "AI VIDEO SUMMARIZER",
        margin,
        18
    );

    doc.setFont(
        "helvetica",
        "normal"
    );

    doc.setFontSize(8);

    doc.text(
        "PROFESSIONAL CONTENT ANALYSIS REPORT",
        margin,
        24
    );

    // Divider
    doc.setLineWidth(0.4);

    doc.line(
        margin,
        29,
        pageWidth - margin,
        29
    );

    // Main title
    doc.setFont(
        "helvetica",
        "bold"
    );

    doc.setFontSize(20);

    const titleLines =
        doc.splitTextToSize(
            title,
            pageWidth - margin * 2
        );

    doc.text(
        titleLines,
        margin,
        48
    );

    let y =
        48 +
        titleLines.length * 9;

    doc.setFont(
        "helvetica",
        "normal"
    );

    doc.setFontSize(10);

    doc.text(
        "REPORT LANGUAGE: " +
        language,
        margin,
        y + 5
    );

    // Information block
    y += 22;

    doc.setFont(
        "helvetica",
        "bold"
    );

    doc.setFontSize(12);

    doc.text(
        "VIDEO INFORMATION",
        margin,
        y
    );

    y += 9;

    const processing =
        currentVideoData?.processing || {};

    const infoRows = [
        [
            "Title",
            title
        ],
        [
            "Transcript Language",
            String(
                currentTranscriptData?.language ||
                "Unknown"
            ).toUpperCase()
        ],
        [
            "Transcript Segments",
            String(
                currentTranscriptData?.transcript?.length ||
                0
            )
        ],
        [
            "Analysis Mode",
            processing.mode ||
            "AI Analysis"
        ],
        [
            "Processing Chunks",
            String(
                processing.total_chunks ??
                "-"
            )
        ],
        [
            "Transcript Characters",
            String(
                processing.transcript_characters ??
                "-"
            )
        ],
        [
            "Report Language",
            language
        ]
    ];

    doc.autoTable({
        startY: y,
        head: [
            [
                "FIELD",
                "VALUE"
            ]
        ],
        body: infoRows,
        margin: {
            left: margin,
            right: margin
        },
        theme: "grid",
        styles: {
            font: "helvetica",
            fontSize: 8,
            cellPadding: 3,
            overflow: "linebreak"
        },
        headStyles: {
            fontStyle: "bold"
        },
        columnStyles: {
            0: {
                cellWidth: 45
            },
            1: {
                cellWidth:
                    pageWidth -
                    margin * 2 -
                    45
            }
        }
    });

    // Source URL
    let finalY =
        doc.lastAutoTable.finalY + 15;

    doc.setFont(
        "helvetica",
        "bold"
    );

    doc.setFontSize(9);

    doc.text(
        "SOURCE URL",
        margin,
        finalY
    );

    finalY += 5;

    doc.setFont(
        "helvetica",
        "normal"
    );

    doc.setFontSize(7);

    const url =
        document.getElementById(
            "videoUrl"
        )?.value ||
        "";

    const urlLines =
        doc.splitTextToSize(
            url,
            pageWidth - margin * 2
        );

    doc.text(
        urlLines,
        margin,
        finalY
    );

    // Report generated label
    finalY +=
        urlLines.length * 3.5 +
        10;

    doc.setFontSize(8);

    doc.text(
        "Generated by AI Video Summarizer",
        margin,
        finalY
    );

    addPageBreak(doc);
}


// ============================================================
// PDF EXECUTIVE SUMMARY
// ============================================================

function addPDFExecutiveSummary(doc) {

    const data =
        getLanguageData();

    if (!data) {
        return;
    }

    addPDFSectionTitle(
        doc,
        "01",
        currentLanguage === "id"
            ? "RINGKASAN EKSEKUTIF"
            : "EXECUTIVE SUMMARY"
    );

    addPDFParagraph(
        doc,
        normalizeAIValue(
            data.summary
        )
    );
}


// ============================================================
// PDF KEY POINTS
// ============================================================

function addPDFKeyPoints(doc) {

    const data =
        getLanguageData();

    if (!data) {
        return;
    }

    addPDFSectionTitle(
        doc,
        "02",
        currentLanguage === "id"
            ? "POIN UTAMA"
            : "KEY POINTS"
    );

    addPDFNumberedList(
        doc,
        data.key_points
    );
}


// ============================================================
// PDF CRITICAL ANALYSIS
// ============================================================

function addPDFCriticalAnalysis(doc) {

    const data =
        getLanguageData();

    if (!data) {
        return;
    }

    addPDFSectionTitle(
        doc,
        "03",
        currentLanguage === "id"
            ? "ANALISIS KRITIS"
            : "CRITICAL ANALYSIS"
    );

    addPDFNumberedList(
        doc,
        data.critical_analysis
    );
}


// ============================================================
// PDF IMPLICATIONS
// ============================================================

function addPDFImplications(doc) {

    const data =
        getLanguageData();

    if (!data) {
        return;
    }

    addPDFSectionTitle(
        doc,
        "04",
        currentLanguage === "id"
            ? "IMPLIKASI"
            : "IMPLICATIONS"
    );

    addPDFNumberedList(
        doc,
        data.implications
    );
}


// ============================================================
// PDF TAKEAWAYS
// ============================================================

function addPDFTakeaways(doc) {

    const data =
        getLanguageData();

    if (!data) {
        return;
    }

    addPDFSectionTitle(
        doc,
        "05",
        currentLanguage === "id"
            ? "KESIMPULAN UTAMA"
            : "KEY TAKEAWAYS"
    );

    addPDFNumberedList(
        doc,
        data.takeaways
    );
}


// ============================================================
// PDF TRANSCRIPT
// ============================================================

function addPDFTranscript(doc) {

    const transcript =
        currentTranscriptData?.transcript || [];

    if (
        !Array.isArray(transcript) ||
        transcript.length === 0
    ) {
        return;
    }

    addPageBreak(doc);

    addPDFSectionTitle(
        doc,
        "06",
        currentLanguage === "id"
            ? "MATERI SUMBER / TRANSKRIP"
            : "SOURCE MATERIAL / TRANSCRIPT"
    );

    const rows =
        transcript.map(
            (segment, index) => {

                return [
                    String(
                        index + 1
                    ).padStart(
                        3,
                        "0"
                    ),

                    formatTimestamp(
                        Number(
                            segment.start || 0
                        )
                    ),

                    segment.text ||
                    ""
                ];
            }
        );

    doc.autoTable({

        head: [
            [
                "NO.",
                "TIME",
                "TRANSCRIPT"
            ]
        ],

        body: rows,

        margin: {
            left: 15,
            right: 15,
            top: 35,
            bottom: 20
        },

        theme: "grid",

        styles: {
            font:
                "helvetica",

            fontSize:
                7,

            cellPadding:
                2.5,

            overflow:
                "linebreak",

            valign:
                "top"
        },

        headStyles: {
            fontStyle:
                "bold"
        },

        columnStyles: {
            0: {
                cellWidth:
                    12,

                halign:
                    "center"
            },

            1: {
                cellWidth:
                    20,

                halign:
                    "center"
            },

            2: {
                cellWidth:
                    "auto"
            }
        },

        pageBreak:
            "auto",

        showHead:
            "everyPage",

        didDrawPage:
            function () {

                const pageWidth =
                    doc.internal.pageSize.getWidth();

                doc.setFont(
                    "helvetica",
                    "bold"
                );

                doc.setFontSize(8);

                doc.text(
                    currentLanguage === "id"
                        ? "MATERI SUMBER / TRANSKRIP"
                        : "SOURCE MATERIAL / TRANSCRIPT",
                    15,
                    15
                );

                doc.setLineWidth(
                    0.3
                );

                doc.line(
                    15,
                    18,
                    pageWidth - 15,
                    18
                );
            }
    });
}


// ============================================================
// PDF SECTION TITLE
// ============================================================

function addPDFSectionTitle(
    doc,
    number,
    title
) {

    ensurePDFSpace(
        doc,
        35
    );

    const margin = 18;

    const pageWidth =
        doc.internal.pageSize.getWidth();

    let y =
        getPDFY(doc);

    doc.setFont(
        "helvetica",
        "bold"
    );

    doc.setFontSize(9);

    doc.text(
        number,
        margin,
        y
    );

    doc.setFontSize(14);

    doc.text(
        title,
        margin + 12,
        y
    );

    doc.setLineWidth(
        0.3
    );

    doc.line(
        margin,
        y + 4,
        pageWidth - margin,
        y + 4
    );

    doc.lastAutoTable = {
        finalY:
            y + 12
    };
}


// ============================================================
// PDF PARAGRAPH
// ============================================================

function addPDFParagraph(
    doc,
    text
) {

    if (!text) {
        return;
    }

    const margin = 18;

    const pageWidth =
        doc.internal.pageSize.getWidth();

    const usableWidth =
        pageWidth -
        margin * 2;

    const lines =
        doc.splitTextToSize(
            String(text),
            usableWidth
        );

    const lineHeight = 5;

    ensurePDFSpace(
        doc,
        lines.length *
            lineHeight +
            10
    );

    const y =
        getPDFY(doc);

    doc.setFont(
        "helvetica",
        "normal"
    );

    doc.setFontSize(9);

    doc.text(
        lines,
        margin,
        y
    );

    doc.lastAutoTable = {
        finalY:
            y +
            lines.length *
                lineHeight +
            8
    };
}


// ============================================================
// PDF NUMBERED LIST
// ============================================================

function addPDFNumberedList(
    doc,
    items
) {

    if (!Array.isArray(items)) {

        addPDFParagraph(
            doc,
            normalizeAIValue(items)
        );

        return;
    }

    if (items.length === 0) {

        addPDFParagraph(
            doc,
            currentLanguage === "id"
                ? "Tidak ada informasi."
                : "No information available."
        );

        return;
    }

    const margin = 18;

    const pageWidth =
        doc.internal.pageSize.getWidth();

    const usableWidth =
        pageWidth -
        margin * 2 -
        10;

    const lineHeight = 4.5;

    items.forEach(
        function (item, index) {

            const text =
                normalizeAIValue(item);

            if (!text) {
                return;
            }

            const lines =
                doc.splitTextToSize(
                    text,
                    usableWidth
                );

            const requiredHeight =
                lines.length *
                    lineHeight +
                8;

            ensurePDFSpace(
                doc,
                requiredHeight
            );

            let y =
                getPDFY(doc);

            doc.setFont(
                "helvetica",
                "bold"
            );

            doc.setFontSize(9);

            doc.text(
                String(
                    index + 1
                ).padStart(
                    2,
                    "0"
                ),
                margin,
                y
            );

            doc.setFont(
                "helvetica",
                "normal"
            );

            doc.setFontSize(8.5);

            doc.text(
                lines,
                margin + 9,
                y
            );

            doc.lastAutoTable = {
                finalY:
                    y +
                    lines.length *
                        lineHeight +
                    5
            };
        }
    );
}


// ============================================================
// PDF PAGE BREAK
// ============================================================

function addPageBreak(doc) {

    doc.addPage();

    doc.lastAutoTable = {
        finalY: 25
    };
}


// ============================================================
// PDF CURRENT Y POSITION
// ============================================================

function getPDFY(doc) {

    if (
        doc.lastAutoTable &&
        typeof doc.lastAutoTable.finalY ===
            "number"
    ) {
        return (
            doc.lastAutoTable.finalY +
            7
        );
    }

    return 35;
}


// ============================================================
// ENSURE PDF SPACE
// ============================================================

function ensurePDFSpace(
    doc,
    requiredHeight
) {

    const pageHeight =
        doc.internal.pageSize.getHeight();

    const marginBottom = 20;

    const y =
        getPDFY(doc);

    if (
        y +
            requiredHeight >
        pageHeight -
            marginBottom
    ) {

        doc.addPage();

        doc.lastAutoTable = {
            finalY: 25
        };
    }
}


// ============================================================
// PDF FOOTER
// ============================================================

function addPDFFooter(doc) {

    const pageCount =
        doc.internal.pageSize.getNumberOfPages();

    const pageWidth =
        doc.internal.pageSize.getWidth();

    const pageHeight =
        doc.internal.pageSize.getHeight();

    for (
        let page = 1;
        page <= pageCount;
        page++
    ) {

        doc.setPage(
            page
        );

        doc.setFont(
            "helvetica",
            "normal"
        );

        doc.setFontSize(
            7
        );

        doc.setLineWidth(
            0.2
        );

        doc.line(
            15,
            pageHeight - 12,
            pageWidth - 15,
            pageHeight - 12
        );

        doc.text(
            "AI Video Summarizer",
            15,
            pageHeight - 7
        );

        doc.text(
            "Page " +
                page +
                " of " +
                pageCount,
            pageWidth - 15,
            pageHeight - 7,
            {
                align:
                    "right"
            }
        );
    }
}


// ============================================================
// STATUS
// ============================================================

function showStatus(
    message,
    type
) {

    const element =
        document.getElementById(
            "status"
        );

    if (!element) {
        return;
    }

    element.className =
        "status " +
        type;

    element.innerText =
        message;
}


// ============================================================
// CLEAR RESULTS
// ============================================================

function clearResults() {

    const videoInfo =
        document.getElementById(
            "videoInfo"
        );

    if (videoInfo) {
        videoInfo.innerHTML =
            "<p>Analyzing video...</p>";
    }

    const transcript =
        document.getElementById(
            "transcript"
        );

    if (transcript) {
        transcript.innerHTML =
            "<p>Loading transcript...</p>";
    }

    const analysis =
        document.getElementById(
            "professionalAnalysis"
        );

    if (analysis) {
        analysis.innerHTML = "";
    }

    const exportContainer =
        document.getElementById(
            "exportContainer"
        );

    if (exportContainer) {
        exportContainer.remove();
    }
}


// ============================================================
// ERROR UI
// ============================================================

function renderError(
    message
) {

    const analysis =
        document.getElementById(
            "professionalAnalysis"
        );

    if (!analysis) {
        return;
    }

    analysis.innerHTML = `
        <div class="analysis-error">

            <div class="error-title">
                ANALYSIS FAILED
            </div>

            <div class="error-message">
                ${escapeHtml(
                    message ||
                    "Unknown error."
                )}
            </div>

        </div>
    `;
}


// ============================================================
// INFO ITEM
// ============================================================

function infoItem(
    label,
    value
) {

    return `
        <div class="info-item">

            <div class="info-label">
                ${label}
            </div>

            <div class="info-value">
                ${value}
            </div>

        </div>
    `;
}


// ============================================================
// FORMAT NUMBER
// ============================================================

function formatNumber(
    value
) {

    if (
        value === null ||
        value === undefined ||
        value === ""
    ) {
        return "-";
    }

    const number =
        Number(value);

    if (
        Number.isNaN(number)
    ) {
        return String(value);
    }

    return number.toLocaleString(
        "en-US"
    );
}


// ============================================================
// FORMAT TIMESTAMP
// ============================================================

function formatTimestamp(
    seconds
) {

    seconds =
        Number(seconds);

    if (
        !Number.isFinite(seconds) ||
        seconds < 0
    ) {
        seconds = 0;
    }

    const totalSeconds =
        Math.floor(seconds);

    const hours =
        Math.floor(
            totalSeconds / 3600
        );

    const minutes =
        Math.floor(
            (totalSeconds % 3600) /
            60
        );

    const secs =
        totalSeconds % 60;

    if (hours > 0) {

        return (
            String(hours).padStart(2, "0") +
            ":" +
            String(minutes).padStart(2, "0") +
            ":" +
            String(secs).padStart(2, "0")
        );

    }

    return (
        String(minutes).padStart(2, "0") +
        ":" +
        String(secs).padStart(2, "0")
    );
}


// ============================================================
// SANITIZE FILENAME
// ============================================================

function sanitizeFilename(
    filename
) {

    return String(filename)
        .replace(
            /[<>:"/\\|?*\x00-\x1F]/g,
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


// ============================================================
// ESCAPE HTML
// ============================================================

function escapeHtml(
    value
) {

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


// ============================================================
// PROFESSIONAL UI INJECTION
// ============================================================

function injectProfessionalUI() {

    injectStyles();

    const resultCard =
        document.querySelector(
            ".result-card"
        );

    if (!resultCard) {
        return;
    }

    const originalVideoInfo =
        document.getElementById(
            "videoInfo"
        );

    if (
        !document.getElementById(
            "professionalAnalysis"
        )
    ) {

        const analysisWrapper =
            document.createElement(
                "div"
            );

        analysisWrapper.id =
            "professionalAnalysis";

        analysisWrapper.className =
            "professional-analysis";

        const heading =
            document.createElement(
                "div"
            );

        heading.className =
            "analysis-heading";

        heading.innerHTML = `
            <div>
                <span class="analysis-kicker">
                    PROFESSIONAL REPORT
                </span>

                <h2>
                    CONTENT ANALYSIS
                </h2>
            </div>
        `;

        resultCard.appendChild(
            heading
        );

        resultCard.appendChild(
            analysisWrapper
        );
    }
}


// ============================================================
// PROFESSIONAL CSS
// ============================================================

function injectStyles() {

    if (
        document.getElementById(
            "professionalReportStyles"
        )
    ) {
        return;
    }

    const style =
        document.createElement(
            "style"
        );

    style.id =
        "professionalReportStyles";

    style.textContent = `

        .professional-analysis {
            margin-top: 25px;
        }

        .analysis-heading {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 20px 0;
            border-top: 1px solid #d9dee5;
            border-bottom: 1px solid #d9dee5;
            margin-top: 20px;
        }

        .analysis-kicker {
            display: block;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 2px;
            color: #6b7280;
            margin-bottom: 5px;
        }

        .analysis-heading h2 {
            margin: 0;
            font-size: 24px;
            letter-spacing: 0.5px;
        }

        .language-selector-container {
            display: flex;
            justify-content: flex-end;
            align-items: center;
            gap: 10px;
            margin: 20px 0;
        }

        .language-selector-container label {
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 1px;
            color: #6b7280;
        }

        .language-selector-container select {
            min-width: 130px;
            padding: 9px 12px;
            border: 1px solid #cfd5dd;
            border-radius: 5px;
            background: #ffffff;
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
        }

        .report-section {
            display: flex;
            gap: 18px;
            padding: 25px 0;
            border-bottom: 1px solid #e3e6ea;
        }

        .section-number {
            min-width: 38px;
            font-size: 12px;
            font-weight: 700;
            color: #6b7280;
            letter-spacing: 1px;
        }

        .section-content {
            flex: 1;
        }

        .section-content h2 {
            margin: 0 0 16px 0;
            font-size: 17px;
            letter-spacing: 0.6px;
        }

        .summary-box {
            padding: 18px;
            border-left: 3px solid #374151;
            background: #f7f8fa;
            line-height: 1.75;
            font-size: 14px;
        }

        .analysis-text {
            line-height: 1.75;
            font-size: 14px;
        }

        .professional-list {
            margin: 0;
            padding: 0;
            list-style: none;
        }

        .professional-list li {
            display: flex;
            gap: 15px;
            margin-bottom: 15px;
        }

        .list-number {
            min-width: 32px;
            font-size: 12px;
            font-weight: 700;
            color: #6b7280;
        }

        .list-content {
            flex: 1;
            line-height: 1.7;
            font-size: 14px;
        }

        .critical-analysis-list {
            display: flex;
            flex-direction: column;
            gap: 14px;
        }

        .critical-item {
            display: flex;
            gap: 15px;
            padding: 15px;
            border: 1px solid #e0e4e8;
            border-radius: 5px;
            background: #ffffff;
        }

        .critical-number {
            min-width: 32px;
            font-size: 12px;
            font-weight: 700;
            color: #6b7280;
        }

        .critical-content {
            flex: 1;
            line-height: 1.7;
            font-size: 14px;
        }

        .info-item {
            padding: 12px 14px;
            border: 1px solid #e2e6eb;
            border-radius: 5px;
            background: #ffffff;
        }

        .video-info-grid {
            display: grid;
            grid-template-columns: repeat(
                auto-fit,
                minmax(180px, 1fr)
            );
            gap: 10px;
        }

        .info-label {
            font-size: 9px;
            font-weight: 700;
            color: #737b87;
            letter-spacing: 1px;
            margin-bottom: 6px;
        }

        .info-value {
            font-size: 13px;
            font-weight: 600;
            line-height: 1.4;
            word-break: break-word;
        }

        .hash-container {
            margin-top: 10px;
            padding: 10px 12px;
            background: #f6f7f9;
            border-radius: 4px;
            font-size: 10px;
        }

        .hash-container span {
            font-weight: 700;
            margin-right: 8px;
        }

        .hash-container code {
            word-break: break-all;
        }

        .transcript-wrapper {
            margin-top: 10px;
        }

        .transcript-header {
            display: flex;
            justify-content: space-between;
            padding: 12px 15px;
            background: #f1f3f5;
            border: 1px solid #dfe3e8;
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 1px;
        }

        .transcript-scroll {
            max-height: 550px;
            overflow-y: auto;
            border-left: 1px solid #dfe3e8;
            border-right: 1px solid #dfe3e8;
            border-bottom: 1px solid #dfe3e8;
        }

        .transcript-row {
            display: grid;
            grid-template-columns: 42px 70px 1fr;
            gap: 10px;
            padding: 10px 12px;
            border-bottom: 1px solid #eceff2;
            font-size: 12px;
        }

        .transcript-row:last-child {
            border-bottom: none;
        }

        .transcript-index {
            color: #9aa1aa;
            font-size: 10px;
        }

        .transcript-time {
            font-weight: 700;
            color: #4b5563;
            font-family: monospace;
        }

        .transcript-text {
            line-height: 1.6;
        }

        .transcript-empty,
        .analysis-empty {
            padding: 20px;
            color: #737b87;
            background: #f8f9fa;
            border-radius: 5px;
        }

        .analysis-error {
            padding: 20px;
            border: 1px solid #e0b4b4;
            background: #fff6f6;
            border-radius: 5px;
        }

        .error-title {
            font-weight: 700;
            margin-bottom: 8px;
        }

        .error-message {
            line-height: 1.6;
            font-size: 13px;
        }

        .export-container {
            display: flex;
            align-items: center;
            justify-content: flex-end;
            gap: 10px;
            padding: 18px 0;
            border-top: 1px solid #dfe3e8;
            margin-top: 20px;
        }

        .export-pdf-button {
            border: none;
            padding: 11px 20px;
            border-radius: 5px;
            background: #1f2937;
            color: #ffffff;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 1px;
            cursor: pointer;
        }

        .export-pdf-button:hover {
            opacity: 0.88;
        }

        .export-pdf-button:disabled {
            opacity: 0.55;
            cursor: wait;
        }

        .export-language {
            font-size: 10px;
            font-weight: 700;
            color: #737b87;
            letter-spacing: 1px;
        }

        .status {
            margin-top: 10px;
            padding: 10px 12px;
            border-radius: 4px;
            font-size: 12px;
        }

        .status.loading {
            background: #f3f4f6;
            color: #374151;
        }

        .status.success {
            background: #f0fdf4;
            color: #166534;
        }

        .status.error {
            background: #fef2f2;
            color: #991b1b;
        }

        @media (max-width: 700px) {

            .report-section {
                flex-direction: column;
                gap: 8px;
            }

            .section-number {
                min-width: auto;
            }

            .transcript-row {
                grid-template-columns:
                    35px
                    65px
                    1fr;
            }

            .export-container {
                justify-content: flex-start;
                flex-wrap: wrap;
            }

            .analysis-heading {
                flex-direction: column;
                align-items: flex-start;
                gap: 10px;
            }
        }

    `;

    document.head.appendChild(
        style
    );
}


// ============================================================
// GLOBAL EXPORTS
// ============================================================

window.changeLanguage =
    changeLanguage;

window.exportPDF =
    exportPDF;

window.analyzeVideo =
    analyzeVideo;
