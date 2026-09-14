document.addEventListener(
    "DOMContentLoaded",
    () => {

        // ==================================================
        // ELEMENT
        // ==================================================

        const videoUrlInput =
            document.getElementById(
                "videoUrl"
            );

        const analyzeButton =
            document.getElementById(
                "analyzeButton"
            );

        const statusElement =
            document.getElementById(
                "status"
            );


        // ==================================================
        // API
        // ==================================================

        const API_URL =
            "https://ai-video-summarizer.hendriseptian25.workers.dev/analyze";


        // ==================================================
        // CURRENT DATA
        // ==================================================

        let currentLanguage =
            "en";

        let currentAIData =
            null;

        let currentVideoData =
            null;


        // ==================================================
        // FORMAT TIME
        // ==================================================

        function formatTime(
            seconds
        ) {

            seconds =
                Math.floor(
                    Number(
                        seconds
                    ) || 0
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

                    String(
                        hours
                    ).padStart(
                        2,
                        "0"
                    )

                    +

                    ":"

                    +

                    String(
                        minutes
                    ).padStart(
                        2,
                        "0"
                    )

                    +

                    ":"

                    +

                    String(
                        secs
                    ).padStart(
                        2,
                        "0"
                    )
                );

            }


            return (

                String(
                    minutes
                ).padStart(
                    2,
                    "0"
                )

                +

                ":"

                +

                String(
                    secs
                ).padStart(
                    2,
                    "0"
                )
            );
        }


        // ==================================================
        // ESCAPE HTML
        // ==================================================

        function escapeHTML(
            text
        ) {

            return String(
                text ?? ""
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


        // ==================================================
        // NORMALIZE ARRAY
        // ==================================================

        function normalizeArray(
            value
        ) {

            if (
                !Array.isArray(
                    value
                )
            ) {

                return [];

            }


            return value
                .map(
                    item =>
                        String(
                            item ?? ""
                        ).trim()
                )
                .filter(
                    item =>
                        item.length > 0
                );
        }


        // ==================================================
        // GET CURRENT LANGUAGE DATA
        // ==================================================

        function getLanguageData() {

            if (
                !currentAIData
            ) {

                return null;

            }


            return (

                currentAIData[
                    currentLanguage
                ]

                ||

                currentAIData.en

                ||

                currentAIData.id

                ||

                null
            );
        }


        // ==================================================
        // GET TRANSCRIPT DATA
        // ==================================================

        function getTranscriptData(
            data
        ) {

            if (
                !data
            ) {

                return {

                    title:
                        "",

                    language:
                        "",

                    segments:
                        []
                };

            }


            const raw =
                data.transcript;


            // ----------------------------------------------
            // NEW BACKEND FORMAT
            //
            // data.transcript.title
            // data.transcript.language
            // data.transcript.transcript
            // ----------------------------------------------

            if (
                raw
                &&
                !Array.isArray(
                    raw
                )
                &&
                Array.isArray(
                    raw.transcript
                )
            ) {

                return {

                    title:
                        raw.title
                        ||
                        data.title
                        ||
                        "Untitled Video",

                    language:
                        raw.language
                        ||
                        data.language
                        ||
                        "-",

                    segments:
                        raw.transcript
                };

            }


            // ----------------------------------------------
            // OLD / FALLBACK FORMAT
            //
            // data.transcript = []
            // ----------------------------------------------

            if (
                Array.isArray(
                    raw
                )
            ) {

                return {

                    title:
                        data.title
                        ||
                        "Untitled Video",

                    language:
                        data.language
                        ||
                        "-",

                    segments:
                        raw
                };

            }


            return {

                title:
                    data.title
                    ||
                    "Untitled Video",

                language:
                    data.language
                    ||
                    "-",

                segments:
                    []
            };
        }


        // ==================================================
        // LANGUAGE SELECTOR
        // ==================================================

        function createLanguageSelector() {

            return `

                <select
                    id="languageSelector"
                    aria-label="Analysis language"
                    style="
                        padding: 7px 10px;
                        border-radius: 7px;
                        border: 1px solid #c7cdd4;
                        background: #ffffff;
                        color: #20262e;
                        cursor: pointer;
                        font-size: 13px;
                        font-weight: 600;
                        outline: none;
                    "
                >

                    <option
                        value="en"
                        ${
                            currentLanguage === "en"
                                ? "selected"
                                : ""
                        }
                    >
                        EN
                    </option>

                    <option
                        value="id"
                        ${
                            currentLanguage === "id"
                                ? "selected"
                                : ""
                        }
                    >
                        ID
                    </option>

                </select>

            `;
        }


        // ==================================================
        // SECTION TITLE
        // ==================================================

        function sectionTitle(
            number,
            title,
            description
        ) {

            return `

                <div
                    style="
                        display: flex;
                        align-items: flex-start;
                        gap: 12px;
                        margin-bottom: 18px;
                    "
                >

                    <div
                        style="
                            min-width: 32px;
                            height: 32px;
                            border-radius: 7px;
                            background: #111827;
                            color: #ffffff;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            font-size: 12px;
                            font-weight: 700;
                        "
                    >
                        ${number}
                    </div>

                    <div>

                        <div
                            style="
                                font-size: 15px;
                                font-weight: 700;
                                color: #18212b;
                                letter-spacing: 0.1px;
                            "
                        >
                            ${title}
                        </div>

                        ${
                            description
                                ? `
                                    <div
                                        style="
                                            margin-top: 3px;
                                            font-size: 12px;
                                            color: #697586;
                                        "
                                    >
                                        ${description}
                                    </div>
                                `
                                : ""
                        }

                    </div>

                </div>

            `;
        }


        // ==================================================
        // CREATE LIST
        // ==================================================

        function createNumberedList(
            items,
            type
        ) {

            if (
                !items ||
                items.length === 0
            ) {

                return `

                    <div
                        style="
                            padding: 14px 16px;
                            background: #f8fafc;
                            border: 1px solid #e5e7eb;
                            border-radius: 8px;
                            color: #6b7280;
                            font-size: 13px;
                        "
                    >
                        No information available.
                    </div>

                `;
            }


            let html = "";


            items.forEach(
                (
                    item,
                    index
                ) => {

                    const number =
                        String(
                            index + 1
                        ).padStart(
                            2,
                            "0"
                        );


                    let background =
                        "#ffffff";

                    let border =
                        "#e5e7eb";


                    if (
                        type ===
                        "critical"
                    ) {

                        background =
                            "#fffaf5";

                        border =
                            "#f1dfc7";
                    }


                    if (
                        type ===
                        "implication"
                    ) {

                        background =
                            "#f8fafc";

                        border =
                            "#dfe5ec";
                    }


                    if (
                        type ===
                        "takeaway"
                    ) {

                        background =
                            "#f8fafc";

                        border =
                            "#dfe5ec";
                    }


                    html += `

                        <div
                            style="
                                display: flex;
                                gap: 14px;
                                padding: 14px 15px;
                                margin-bottom: 9px;
                                background: ${background};
                                border: 1px solid ${border};
                                border-radius: 8px;
                                box-sizing: border-box;
                            "
                        >

                            <div
                                style="
                                    min-width: 28px;
                                    color: #6b7280;
                                    font-size: 12px;
                                    font-weight: 700;
                                    padding-top: 1px;
                                "
                            >
                                ${number}
                            </div>

                            <div
                                style="
                                    flex: 1;
                                    color: #27313d;
                                    font-size: 13px;
                                    line-height: 1.65;
                                "
                            >
                                ${escapeHTML(item)}
                            </div>

                        </div>

                    `;
                }
            );


            return html;
        }


        // ==================================================
        // EXECUTIVE SUMMARY
        // ==================================================

        function createExecutiveSummary(
            ai
        ) {

            const summary =
                String(
                    ai.summary || ""
                ).trim();


            return `

                <section
                    style="
                        padding: 22px 22px 24px;
                        border-bottom: 1px solid #e5e7eb;
                    "
                >

                    ${sectionTitle(
                        "01",
                        "EXECUTIVE SUMMARY",
                        "Ringkasan analitis dari keseluruhan isi video"
                    )}


                    <div
                        style="
                            background: #f8fafc;
                            border-left: 3px solid #1f2937;
                            padding: 17px 18px;
                            border-radius: 0 8px 8px 0;
                        "
                    >

                        <div
                            style="
                                color: #27313d;
                                font-size: 14px;
                                line-height: 1.8;
                                white-space: pre-wrap;
                            "
                        >
                            ${escapeHTML(
                                summary ||
                                "Summary tidak tersedia."
                            )}
                        </div>

                    </div>

                </section>

            `;
        }


        // ==================================================
        // KEY POINTS
        // ==================================================

        function createKeyPoints(
            ai
        ) {

            const items =
                normalizeArray(
                    ai.key_points
                );


            return `

                <section
                    style="
                        padding: 22px;
                        border-bottom: 1px solid #e5e7eb;
                    "
                >

                    ${sectionTitle(
                        "02",
                        "KEY POINTS",
                        "Poin substantif yang paling relevan dari pembahasan"
                    )}


                    ${createNumberedList(
                        items,
                        "key"
                    )}

                </section>

            `;
        }


        // ==================================================
        // CRITICAL ANALYSIS
        // ==================================================

        function createCriticalAnalysis(
            ai
        ) {

            const items =
                normalizeArray(
                    ai.critical_analysis
                );


            return `

                <section
                    style="
                        padding: 22px;
                        border-bottom: 1px solid #e5e7eb;
                    "
                >

                    ${sectionTitle(
                        "03",
                        "CRITICAL ANALYSIS",
                        "Evaluasi terhadap klaim, bukti, asumsi, konsistensi dan konteks"
                    )}


                    ${createNumberedList(
                        items,
                        "critical"
                    )}

                </section>

            `;
        }


        // ==================================================
        // IMPLICATIONS
        // ==================================================

        function createImplications(
            ai
        ) {

            const items =
                normalizeArray(
                    ai.implications
                );


            return `

                <section
                    style="
                        padding: 22px;
                        border-bottom: 1px solid #e5e7eb;
                    "
                >

                    ${sectionTitle(
                        "04",
                        "IMPLICATIONS",
                        "Implikasi, risiko, peluang atau pertimbangan yang dapat ditarik dari isi video"
                    )}


                    ${createNumberedList(
                        items,
                        "implication"
                    )}

                </section>

            `;
        }


        // ==================================================
        // TAKEAWAYS
        // ==================================================

        function createTakeaways(
            ai
        ) {

            const items =
                normalizeArray(
                    ai.takeaways
                );


            return `

                <section
                    style="
                        padding: 22px;
                    "
                >

                    ${sectionTitle(
                        "05",
                        "KEY TAKEAWAYS",
                        "Kesimpulan utama yang perlu diperhatikan"
                    )}


                    ${createNumberedList(
                        items,
                        "takeaway"
                    )}

                </section>

            `;
        }


        // ==================================================
        // CREATE AI SUMMARY
        // ==================================================

        function createAISummaryHTML() {

            const ai =
                getLanguageData();


            if (
                !ai
            ) {

                return `

                    <div
                        id="aiSummaryContainer"
                        style="
                            margin-top: 25px;
                            background: #ffffff;
                            border: 1px solid #dfe3e8;
                            border-radius: 10px;
                            overflow: hidden;
                        "
                    >

                        <div
                            style="
                                padding: 20px;
                                color: #6b7280;
                            "
                        >
                            AI analysis tidak tersedia.
                        </div>

                    </div>

                `;
            }


            return `

                <div
                    id="aiSummaryContainer"
                    style="
                        margin-top: 25px;
                        background: #ffffff;
                        border: 1px solid #dfe3e8;
                        border-radius: 10px;
                        overflow: hidden;
                        box-shadow:
                            0 2px 8px rgba(
                                15,
                                23,
                                42,
                                0.04
                            );
                    "
                >

                    <!-- ================================= -->
                    <!-- HEADER -->
                    <!-- ================================= -->

                    <div
                        style="
                            display: flex;
                            justify-content: space-between;
                            align-items: center;
                            padding: 17px 20px;
                            background: #f8fafc;
                            border-bottom: 1px solid #e5e7eb;
                        "
                    >

                        <div
                            style="
                                display: flex;
                                align-items: center;
                                gap: 10px;
                            "
                        >

                            <div
                                style="
                                    width: 32px;
                                    height: 32px;
                                    border-radius: 7px;
                                    background: #111827;
                                    color: #ffffff;
                                    display: flex;
                                    align-items: center;
                                    justify-content: center;
                                    font-size: 15px;
                                "
                            >
                                AI
                            </div>

                            <div>

                                <div
                                    style="
                                        font-size: 15px;
                                        font-weight: 700;
                                        color: #18212b;
                                    "
                                >
                                    PROFESSIONAL CONTENT ANALYSIS
                                </div>

                                <div
                                    style="
                                        margin-top: 2px;
                                        font-size: 11px;
                                        color: #6b7280;
                                    "
                                >
                                    Evidence-based transcript analysis
                                </div>

                            </div>

                        </div>


                        ${createLanguageSelector()}

                    </div>


                    <!-- ================================= -->
                    <!-- SECTIONS -->
                    <!-- ================================= -->

                    ${createExecutiveSummary(ai)}

                    ${createKeyPoints(ai)}

                    ${createCriticalAnalysis(ai)}

                    ${createImplications(ai)}

                    ${createTakeaways(ai)}

                </div>

            `;
        }


        // ==================================================
        // UPDATE AI SUMMARY
        // ==================================================

        function updateAISummary() {

            if (
                !currentVideoData
            ) {

                return;

            }


            const oldContainer =
                document.getElementById(
                    "aiSummaryContainer"
                );


            if (
                !oldContainer
            ) {

                return;

            }


            const wrapper =
                document.createElement(
                    "div"
                );


            wrapper.innerHTML =
                createAISummaryHTML();


            const newContainer =
                wrapper.firstElementChild;


            if (
                !newContainer
            ) {

                return;

            }


            oldContainer.replaceWith(
                newContainer
            );
        }


        // ==================================================
        // VIDEO INFORMATION
        // ==================================================

        function createVideoInformation(
            data,
            transcriptData
        ) {

            const title =
                transcriptData.title
                ||
                data.title
                ||
                "Untitled Video";


            const language =
                transcriptData.language
                ||
                data.language
                ||
                "-";


            const channel =
                data.metadata
                &&
                data.metadata.channel
                    ? data.metadata.channel
                    : "";


            const videoId =
                data.video_id
                ||
                "";


            return `

                <div
                    style="
                        background: #ffffff;
                        border: 1px solid #dfe3e8;
                        border-radius: 10px;
                        padding: 20px;
                        margin-top: 25px;
                    "
                >

                    <div
                        style="
                            display: flex;
                            align-items: center;
                            justify-content: space-between;
                            gap: 15px;
                            margin-bottom: 17px;
                        "
                    >

                        <div
                            style="
                                font-size: 13px;
                                font-weight: 700;
                                color: #6b7280;
                                letter-spacing: 0.6px;
                            "
                        >
                            VIDEO INFORMATION
                        </div>

                        <div
                            style="
                                font-size: 11px;
                                color: #9ca3af;
                                font-family: monospace;
                            "
                        >
                            ${escapeHTML(videoId)}
                        </div>

                    </div>


                    <div
                        style="
                            font-size: 20px;
                            line-height: 1.4;
                            font-weight: 700;
                            color: #17202a;
                            margin-bottom: 16px;
                        "
                    >
                        ${escapeHTML(title)}
                    </div>


                    <div
                        style="
                            display: grid;
                            grid-template-columns:
                                repeat(
                                    auto-fit,
                                    minmax(
                                        160px,
                                        1fr
                                    )
                                );
                            gap: 10px;
                        "
                    >

                        <div
                            style="
                                padding: 11px 13px;
                                background: #f8fafc;
                                border: 1px solid #e5e7eb;
                                border-radius: 7px;
                            "
                        >

                            <div
                                style="
                                    font-size: 10px;
                                    text-transform: uppercase;
                                    color: #8a94a3;
                                    margin-bottom: 4px;
                                "
                            >
                                Transcript Language
                            </div>

                            <div
                                style="
                                    font-size: 13px;
                                    font-weight: 600;
                                    color: #26313d;
                                "
                            >
                                ${escapeHTML(language)}
                            </div>

                        </div>


                        <div
                            style="
                                padding: 11px 13px;
                                background: #f8fafc;
                                border: 1px solid #e5e7eb;
                                border-radius: 7px;
                            "
                        >

                            <div
                                style="
                                    font-size: 10px;
                                    text-transform: uppercase;
                                    color: #8a94a3;
                                    margin-bottom: 4px;
                                "
                            >
                                Channel
                            </div>

                            <div
                                style="
                                    font-size: 13px;
                                    font-weight: 600;
                                    color: #26313d;
                                "
                            >
                                ${
                                    escapeHTML(
                                        channel ||
                                        "-"
                                    )
                                }
                            </div>

                        </div>

                    </div>

                </div>

            `;
        }


        // ==================================================
        // TRANSCRIPT
        // ==================================================

        function createTranscriptHTML(
            segments
        ) {

            let html = `

                <div
                    style="
                        margin-top: 18px;
                        background: #ffffff;
                        border: 1px solid #dfe3e8;
                        border-radius: 10px;
                        overflow: hidden;
                    "
                >

                    <div
                        style="
                            padding: 17px 20px;
                            background: #f8fafc;
                            border-bottom: 1px solid #e5e7eb;
                        "
                    >

                        <div
                            style="
                                font-size: 15px;
                                font-weight: 700;
                                color: #18212b;
                            "
                        >
                            📝 TRANSCRIPT
                        </div>

                        <div
                            style="
                                margin-top: 3px;
                                font-size: 11px;
                                color: #6b7280;
                            "
                        >
                            Timestamped transcript from the source video
                        </div>

                    </div>


                    <div
                        style="
                            max-height: 600px;
                            overflow-y: auto;
                            padding: 5px 20px 10px;
                        "
                    >

            `;


            if (
                !segments
                ||
                segments.length === 0
            ) {

                html += `

                    <div
                        style="
                            padding: 25px 5px;
                            color: #6b7280;
                            font-size: 13px;
                        "
                    >
                        Transcript kosong.
                    </div>

                `;

            } else {

                segments.forEach(
                    (
                        segment
                    ) => {

                        const timestamp =
                            formatTime(
                                segment.start
                            );


                        const text =
                            segment.text
                            ||
                            "";


                        html += `

                            <div
                                style="
                                    display: grid;
                                    grid-template-columns:
                                        65px 1fr;
                                    gap: 15px;
                                    padding: 11px 0;
                                    border-bottom:
                                        1px solid #eef0f2;
                                "
                            >

                                <div
                                    style="
                                        font-family:
                                            ui-monospace,
                                            SFMono-Regular,
                                            Menlo,
                                            Monaco,
                                            Consolas,
                                            monospace;
                                        font-size: 11px;
                                        font-weight: 700;
                                        color: #667085;
                                        padding-top: 2px;
                                    "
                                >
                                    ${escapeHTML(
                                        timestamp
                                    )}
                                </div>


                                <div
                                    style="
                                        font-size: 13px;
                                        line-height: 1.7;
                                        color: #303945;
                                    "
                                >
                                    ${escapeHTML(
                                        text
                                    )}
                                </div>

                            </div>

                        `;
                    }
                );

            }


            html += `

                    </div>

                </div>

            `;


            return html;
        }


        // ==================================================
        // DISPLAY COMPLETE REPORT
        // ==================================================

        function displayTranscript(
            data
        ) {

            // ----------------------------------------------
            // SAVE DATA
            // ----------------------------------------------

            currentVideoData =
                data;


            currentAIData =
                data.summary
                ||
                null;


            // ----------------------------------------------
            // TRANSCRIPT
            // ----------------------------------------------

            const transcriptData =
                getTranscriptData(
                    data
                );


            const segments =
                transcriptData.segments;


            // ----------------------------------------------
            // START REPORT
            // ----------------------------------------------

            let html = `

                <div
                    style="
                        margin-top: 10px;
                    "
                >

                    ${createVideoInformation(
                        data,
                        transcriptData
                    )}

                    ${createAISummaryHTML()}

                    <div
                        style="
                            margin-top: 30px;
                        "
                    >

                        <div
                            style="
                                margin-bottom: 12px;
                                font-size: 13px;
                                font-weight: 700;
                                color: #6b7280;
                                letter-spacing: 0.5px;
                            "
                        >
                            SOURCE MATERIAL
                        </div>

                        ${createTranscriptHTML(
                            segments
                        )}

                    </div>

                </div>

            `;


            statusElement.innerHTML =
                html;
        }


        // ==================================================
        // LOADING DISPLAY
        // ==================================================

        function showLoading() {

            statusElement.innerHTML = `

                <div
                    style="
                        margin-top: 25px;
                        background: #ffffff;
                        border: 1px solid #dfe3e8;
                        border-radius: 10px;
                        padding: 25px;
                    "
                >

                    <div
                        style="
                            display: flex;
                            align-items: center;
                            gap: 12px;
                        "
                    >

                        <div
                            style="
                                width: 26px;
                                height: 26px;
                                border: 3px solid #e5e7eb;
                                border-top-color: #111827;
                                border-radius: 50%;
                                animation:
                                    spin 0.8s linear infinite;
                            "
                        ></div>

                        <div>

                            <div
                                style="
                                    font-size: 14px;
                                    font-weight: 700;
                                    color: #1f2937;
                                "
                            >
                                Analyzing video...
                            </div>

                            <div
                                style="
                                    margin-top: 3px;
                                    font-size: 12px;
                                    color: #6b7280;
                                "
                            >
                                Mengambil transcript dan melakukan
                                professional content analysis.
                            </div>

                        </div>

                    </div>

                </div>

                <style>
                    @keyframes spin {
                        from {
                            transform: rotate(0deg);
                        }

                        to {
                            transform: rotate(360deg);
                        }
                    }
                </style>

            `;
        }


        // ==================================================
        // ERROR DISPLAY
        // ==================================================

        function showAPIError(
            data
        ) {

            const message =
                data.message
                ||
                "Unknown error";


            const errorType =
                data.error_type
                ||
                "";


            const detail =
                data.error
                ||
                "";


            const httpStatus =
                data.http_status
                ||
                "";


            statusElement.innerHTML = `

                <div
                    style="
                        margin-top: 25px;
                        background: #ffffff;
                        border: 1px solid #e5b8b8;
                        border-radius: 10px;
                        overflow: hidden;
                    "
                >

                    <div
                        style="
                            padding: 16px 20px;
                            background: #fff5f5;
                            border-bottom: 1px solid #f0d4d4;
                        "
                    >

                        <div
                            style="
                                font-size: 14px;
                                font-weight: 700;
                                color: #b42318;
                            "
                        >
                            ANALYSIS FAILED
                        </div>

                    </div>


                    <div
                        style="
                            padding: 20px;
                        "
                    >

                        <div
                            style="
                                font-size: 13px;
                                line-height: 1.6;
                                color: #344054;
                            "
                        >

                            <strong>
                                Message:
                            </strong>

                            ${escapeHTML(
                                message
                            )}

                        </div>


                        ${
                            errorType
                                ? `
                                    <div
                                        style="
                                            margin-top: 10px;
                                            font-size: 12px;
                                            color: #667085;
                                        "
                                    >
                                        Error Type:
                                        <strong>
                                            ${escapeHTML(
                                                errorType
                                            )}
                                        </strong>
                                    </div>
                                `
                                : ""
                        }


                        ${
                            httpStatus
                                ? `
                                    <div
                                        style="
                                            margin-top: 5px;
                                            font-size: 12px;
                                            color: #667085;
                                        "
                                    >
                                        HTTP Status:
                                        <strong>
                                            ${escapeHTML(
                                                httpStatus
                                            )}
                                        </strong>
                                    </div>
                                `
                                : ""
                        }


                        ${
                            detail
                                ? `
                                    <details
                                        style="
                                            margin-top: 15px;
                                        "
                                    >

                                        <summary
                                            style="
                                                cursor: pointer;
                                                font-size: 12px;
                                                color: #667085;
                                            "
                                        >
                                            Technical details
                                        </summary>

                                        <pre
                                            style="
                                                margin-top: 10px;
                                                padding: 12px;
                                                background: #f8fafc;
                                                border: 1px solid #e5e7eb;
                                                border-radius: 7px;
                                                white-space: pre-wrap;
                                                word-break: break-word;
                                                font-size: 11px;
                                            "
                                        >${escapeHTML(
                                            detail
                                        )}</pre>

                                    </details>
                                `
                                : ""
                        }

                    </div>

                </div>

            `;
        }


        // ==================================================
        // LANGUAGE CHANGE
        // ==================================================

        statusElement.addEventListener(
            "change",
            (
                event
            ) => {

                if (
                    event.target
                    &&
                    event.target.id ===
                        "languageSelector"
                ) {

                    currentLanguage =
                        event.target.value;


                    updateAISummary();

                }

            }
        );


        // ==================================================
        // ANALYZE BUTTON
        // ==================================================

        analyzeButton.addEventListener(
            "click",
            async () => {

                const url =
                    videoUrlInput.value.trim();


                // ------------------------------------------
                // VALIDATION
                // ------------------------------------------

                if (
                    !url
                ) {

                    statusElement.innerHTML = `

                        <div
                            style="
                                margin-top: 25px;
                                background: #fff8f0;
                                border: 1px solid #f1d6b5;
                                border-radius: 10px;
                                padding: 18px 20px;
                                color: #8a4b08;
                                font-size: 13px;
                            "
                        >
                            Masukkan URL YouTube terlebih dahulu.
                        </div>

                    `;

                    return;
                }


                // ------------------------------------------
                // BUTTON STATE
                // ------------------------------------------

                analyzeButton.disabled =
                    true;


                analyzeButton.innerText =
                    "Analyzing...";


                // ------------------------------------------
                // LOADING
                // ------------------------------------------

                showLoading();


                try {

                    // ======================================
                    // API REQUEST
                    // ======================================

                    const response =
                        await fetch(
                            API_URL,
                            {

                                method:
                                    "POST",

                                headers: {

                                    "Content-Type":
                                        "application/json"

                                },

                                body:
                                    JSON.stringify(
                                        {
                                            url:
                                                url
                                        }
                                    )

                            }
                        );


                    // ======================================
                    // READ RESPONSE
                    // ======================================

                    let data;


                    try {

                        data =
                            await response.json();

                    } catch (
                        jsonError
                    ) {

                        throw new Error(
                            "Backend returned invalid JSON."
                        );

                    }


                    // ======================================
                    // ERROR CHECK
                    // ======================================

                    if (
                        !response.ok
                        ||
                        data.status !==
                            "success"
                    ) {

                        console.error(
                            "API Error:",
                            data
                        );


                        showAPIError(
                            data
                        );


                        return;
                    }


                    // ======================================
                    // RESET LANGUAGE
                    // ======================================

                    currentLanguage =
                        "en";


                    // ======================================
                    // DISPLAY REPORT
                    // ======================================

                    displayTranscript(
                        data
                    );


                } catch (
                    error
                ) {

                    console.error(
                        "Frontend Error:",
                        error
                    );


                    statusElement.innerHTML = `

                        <div
                            style="
                                margin-top: 25px;
                                background: #ffffff;
                                border: 1px solid #e5b8b8;
                                border-radius: 10px;
                                padding: 20px;
                            "
                        >

                            <div
                                style="
                                    color: #b42318;
                                    font-size: 14px;
                                    font-weight: 700;
                                    margin-bottom: 8px;
                                "
                            >
                                BACKEND CONNECTION ERROR
                            </div>

                            <div
                                style="
                                    color: #475467;
                                    font-size: 13px;
                                    line-height: 1.6;
                                "
                            >
                                ${escapeHTML(
                                    error.message
                                )}
                            </div>

                        </div>

                    `;

                } finally {

                    // --------------------------------------
                    // RESET BUTTON
                    // --------------------------------------

                    analyzeButton.disabled =
                        false;


                    analyzeButton.innerText =
                        "Analyze";

                }

            }
        );

    }
);
