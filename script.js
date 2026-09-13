document.addEventListener("DOMContentLoaded", () => {

    const videoUrlInput = document.getElementById("videoUrl");
    const analyzeButton = document.getElementById("analyzeButton");
    const statusElement = document.getElementById("status");

    const API_URL =
        "https://ai-video-summarizer.hendriseptian25.workers.dev/analyze";


    // ==========================================
    // FORMAT TIMESTAMP
    // ==========================================

    function formatTime(seconds) {

        seconds = Math.floor(Number(seconds) || 0);

        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = seconds % 60;

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
    // PARSE AI SUMMARY
    // ==========================================

    function parseAISummary(summary) {

        const result = {
            summary: "",
            keyPoints: [],
            takeaways: ""
        };

        if (!summary) {
            return result;
        }


        // --------------------------------------
        // SUMMARY
        // --------------------------------------

        const summaryMatch =
            summary.match(
                /SUMMARY:\s*([\s\S]*?)(?=\n\s*KEY POINTS:|$)/i
            );

        if (summaryMatch) {

            result.summary =
                summaryMatch[1].trim();
        }


        // --------------------------------------
        // KEY POINTS
        // --------------------------------------

        const keyPointsMatch =
            summary.match(
                /KEY POINTS:\s*([\s\S]*?)(?=\n\s*TAKEAWAYS:|$)/i
            );

        if (keyPointsMatch) {

            result.keyPoints =
                keyPointsMatch[1]
                    .split("\n")
                    .map(point =>
                        point
                            .replace(/^\s*[-•*]\s*/, "")
                            .trim()
                    )
                    .filter(point => point.length > 0);
        }


        // --------------------------------------
        // TAKEAWAYS
        // --------------------------------------

        const takeawaysMatch =
            summary.match(
                /TAKEAWAYS:\s*([\s\S]*)/i
            );

        if (takeawaysMatch) {

            result.takeaways =
                takeawaysMatch[1].trim();
        }


        return result;
    }


    // ==========================================
    // DISPLAY AI SUMMARY
    // ==========================================

    function displayAISummary(summary) {

        const ai =
            parseAISummary(summary);


        let html = "";


        // ======================================
        // AI SUMMARY
        // ======================================

        html += `
            <div style="
                margin-top: 25px;
                padding: 20px;
                border-radius: 12px;
                background: #eef6ff;
                border: 1px solid #cfe3ff;
            ">

                <h2>
                    🤖 AI Summary
                </h2>

                <p style="
                    line-height: 1.7;
                    white-space: pre-wrap;
                ">
                    ${escapeHTML(
                        ai.summary ||
                        "Summary tidak tersedia."
                    )}
                </p>

            </div>
        `;


        // ======================================
        // KEY POINTS
        // ======================================

        html += `
            <div style="
                margin-top: 20px;
                padding: 20px;
                border-radius: 12px;
                background: #f7f7f7;
                border: 1px solid #ddd;
            ">

                <h2>
                    📌 Key Points
                </h2>

                <ul style="
                    line-height: 1.8;
                    padding-left: 25px;
                ">
        `;


        if (ai.keyPoints.length > 0) {

            ai.keyPoints.forEach(point => {

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
        `;


        // ======================================
        // TAKEAWAYS
        // ======================================

        html += `
            <div style="
                margin-top: 20px;
                padding: 20px;
                border-radius: 12px;
                background: #fff8e8;
                border: 1px solid #f0dfad;
            ">

                <h2>
                    💡 Takeaways
                </h2>

                <p style="
                    line-height: 1.7;
                    white-space: pre-wrap;
                ">
                    ${escapeHTML(
                        ai.takeaways ||
                        "Takeaways tidak tersedia."
                    )}
                </p>

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
                    <strong>Language:</strong>
                    ${escapeHTML(language)}
                </p>

                <hr>
        `;


        // ======================================
        // AI SUMMARY
        // ======================================

        html += displayAISummary(
            data.summary
        );


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

            analyzeButton.disabled = true;

            analyzeButton.innerText =
                "Analyzing...";


            statusElement.innerHTML = `
                <div style="
                    margin-top: 25px;
                    padding: 20px;
                    border-radius: 12px;
                    background: #f5f5f5;
                ">
                    ⏳ Mengambil transcript dan membuat
                    AI summary...
                </div>
            `;


            try {

                // ==============================
                // CALL CLOUDFLARE API
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
                // API ERROR
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

                            ${
                                escapeHTML(
                                    data.message ||
                                    "Unknown error"
                                )
                            }

                        </div>
                    `;


                    return;
                }


                // ==============================
                // SUCCESS
                // ==============================

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

                        ${escapeHTML(error.message)}

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
