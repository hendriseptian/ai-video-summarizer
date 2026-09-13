document.addEventListener("DOMContentLoaded", () => {

    const videoUrlInput =
        document.getElementById("videoUrl");

    const analyzeButton =
        document.getElementById("analyzeButton");

    const statusElement =
        document.getElementById("status");


    const API_URL =
        "https://ai-video-summarizer.hendriseptian25.workers.dev/analyze";


    // ==========================================
    // CURRENT LANGUAGE
    // ==========================================

    let currentLanguage = "en";

    let currentAIData = null;


    // ==========================================
    // FORMAT TIMESTAMP
    // ==========================================

    function formatTime(seconds) {

        seconds = Math.floor(
            Number(seconds) || 0
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


    // ==========================================
    // ESCAPE HTML
    // ==========================================

    function escapeHTML(text) {

        return String(text || "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }


    // ==========================================
    // GET LANGUAGE DATA
    // ==========================================

    function getLanguageData() {

        if (!currentAIData) {
            return null;
        }


        return (
            currentAIData[currentLanguage] ||
            currentAIData.en ||
            currentAIData.id ||
            null
        );
    }


    // ==========================================
    // DISPLAY AI SUMMARY
    // ==========================================

    function displayAISummary() {

        const ai =
            getLanguageData();


        if (!ai) {

            return `
                <div style="
                    margin-top: 25px;
                    padding: 20px;
                    border-radius: 12px;
                    background: #ffecec;
                    border: 1px solid #ffb5b5;
                ">
                    ❌ AI Summary tidak tersedia.
                </div>
            `;
        }


        const summary =
            ai.summary || "";


        const keyPoints =
            Array.isArray(ai.key_points)
                ? ai.key_points
                : [];


        const takeaways =
            ai.takeaways || "";


        // ======================================
        // LANGUAGE BUTTON
        // ======================================

        const languageButton =
            currentLanguage === "en"
                ? "🇬🇧 EN"
                : "🇮🇩 ID";


        let html = `

            <div style="
                margin-top: 25px;
                padding: 20px;
                border-radius: 12px;
                background: #eef6ff;
                border: 1px solid #cfe3ff;
                position: relative;
            ">


                <!-- LANGUAGE SELECTOR -->

                <div style="
                    position: absolute;
                    top: 15px;
                    right: 15px;
                ">

                    <select
                        id="languageSelector"
                        style="
                            padding: 7px 10px;
                            border-radius: 8px;
                            border: 1px solid #bbb;
                            background: white;
                            cursor: pointer;
                            font-size: 14px;
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
                            🇬🇧 EN
                        </option>

                        <option
                            value="id"
                            ${
                                currentLanguage === "id"
                                    ? "selected"
                                    : ""
                            }
                        >
                            🇮🇩 ID
                        </option>

                    </select>

                </div>


                <!-- SUMMARY -->

                <h2>
                    🤖 AI Summary
                </h2>


                <p style="
                    line-height: 1.7;
                    white-space: pre-wrap;
                    margin-top: 15px;
                ">
                    ${escapeHTML(summary)}
                </p>


                <!-- KEY POINTS -->

                <div style="
                    margin-top: 25px;
                    padding-top: 15px;
                    border-top: 1px solid #d5e5f5;
                ">

                    <h3>
                        📌 Key Points
                    </h3>

                    <ul style="
                        line-height: 1.8;
                        padding-left: 25px;
                    ">
        `;


        if (keyPoints.length > 0) {

            keyPoints.forEach(point => {

                html += `
                    <li>
                        ${escapeHTML(point)}
                    </li>
                `;
            });

        } else {

            html += `
                <li>
                    Key points tidak tersedia.
                </li>
            `;
        }


        html += `

                    </ul>

                </div>


                <!-- TAKEAWAYS -->

                <div style="
                    margin-top: 25px;
                    padding-top: 15px;
                    border-top: 1px solid #d5e5f5;
                ">

                    <h3>
                        💡 Takeaways
                    </h3>

                    <p style="
                        line-height: 1.7;
                        white-space: pre-wrap;
                    ">
                        ${escapeHTML(takeaways)}
                    </p>

                </div>

            </div>
        `;


        return html;
    }


    // ==========================================
    // DISPLAY TRANSCRIPT
    // ==========================================

    function displayTranscript(data) {

        const transcriptData =
            data.transcript;


        if (!transcriptData) {

            statusElement.innerHTML =
                "❌ Transcript tidak ditemukan.";

            return;
        }


        const title =
            transcriptData.title ||
            data.title ||
            "Untitled Video";


        const language =
            transcriptData.language ||
            data.language ||
            "-";


        const segments =
            transcriptData.transcript ||
            [];


        // Save AI data

        currentAIData =
            data.summary;


        let html = "";


        // ======================================
        // VIDEO INFORMATION
        // ======================================

        html += `

            <div style="
                margin-top: 25px;
                padding: 20px;
                border-radius: 12px;
                background: #f5f5f5;
            ">

                <h2>
                    ${escapeHTML(title)}
                </h2>

                <p>
                    <strong>Transcript Language:</strong>
                    ${escapeHTML(language)}
                </p>

        `;


        // ======================================
        // AI SUMMARY
        // ======================================

        html +=
            displayAISummary();


        // ======================================
        // TRANSCRIPT
        // ======================================

        html += `

                <div style="
                    margin-top: 30px;
                ">

                    <h2>
                        📝 Transcript
                    </h2>

        `;


        if (segments.length === 0) {

            html += `
                <p>
                    Transcript kosong.
                </p>
            `;

        } else {

            segments.forEach(segment => {

                const timestamp =
                    formatTime(segment.start);


                const text =
                    segment.text || "";


                html += `

                    <div style="
                        display: flex;
                        gap: 15px;
                        padding: 8px 0;
                        border-bottom: 1px solid #ddd;
                    ">

                        <span style="
                            min-width: 55px;
                            font-weight: bold;
                            color: #555;
                        ">
                            ${escapeHTML(timestamp)}
                        </span>

                        <span style="
                            line-height: 1.6;
                        ">
                            ${escapeHTML(text)}
                        </span>

                    </div>

                `;
            });
        }


        html += `

                </div>

            </div>

        `;


        statusElement.innerHTML =
            html;


        // ======================================
        // LANGUAGE SELECTOR EVENT
        // ======================================

        const languageSelector =
            document.getElementById(
                "languageSelector"
            );


        if (languageSelector) {

            languageSelector.addEventListener(
                "change",
                () => {

                    currentLanguage =
                        languageSelector.value;


                    updateAISummary();

                }
            );
        }
    }


    // ==========================================
    // UPDATE AI SUMMARY ONLY
    // ==========================================

    function updateAISummary() {

        const oldSummary =
            document.querySelector(
                "#aiSummaryContainer"
            );


        if (!oldSummary) {

            // Fallback:
            displayTranscriptFromCurrentData();

            return;
        }


        oldSummary.outerHTML =
            displayAISummary();
    }


    // ==========================================
    // ANALYZE BUTTON
    // ==========================================

    analyzeButton.addEventListener(
        "click",
        async () => {

            const url =
                videoUrlInput.value.trim();


            // ==================================
            // VALIDATION
            // ==================================

            if (!url) {

                statusElement.innerHTML =
                    "❌ Masukkan URL YouTube terlebih dahulu.";

                return;
            }


            // ==================================
            // LOADING
            // ==================================

            analyzeButton.disabled =
                true;

            analyzeButton.innerText =
                "Analyzing...";


            statusElement.innerHTML = `

                <div style="
                    margin-top: 25px;
                    padding: 20px;
                    border-radius: 12px;
                    background: #f5f5f5;
                ">

                    ⏳ Mengambil transcript
                    dan membuat AI summary...

                </div>

            `;


            try {

                // ==============================
                // CALL API
                // ==============================

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


                const data =
                    await response.json();


                // ==============================
                // ERROR
                // ==============================

                if (
                    !response.ok ||
                    data.status !== "success"
                ) {

                    console.error(
                        "API Error:",
                        data
                    );


                    statusElement.innerHTML = `

                        <div style="
                            margin-top: 25px;
                            padding: 20px;
                            border-radius: 12px;
                            background: #ffecec;
                            border: 1px solid #ffb5b5;
                        ">

                            ❌ Gagal menganalisis video.

                            <br><br>

                            ${escapeHTML(
                                data.message ||
                                "Unknown error"
                            )}

                        </div>

                    `;

                    return;
                }


                // ==============================
                // SUCCESS
                // ==============================

                currentLanguage = "en";

                displayTranscript(data);


            } catch (error) {

                console.error(error);


                statusElement.innerHTML = `

                    <div style="
                        margin-top: 25px;
                        padding: 20px;
                        border-radius: 12px;
                        background: #ffecec;
                        border: 1px solid #ffb5b5;
                    ">

                        ❌ Tidak dapat terhubung
                        ke backend.

                        <br><br>

                        ${escapeHTML(
                            error.message
                        )}

                    </div>

                `;

            } finally {

                analyzeButton.disabled =
                    false;

                analyzeButton.innerText =
                    "Analyze";
            }

        }
    );

});
