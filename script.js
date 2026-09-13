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
    // DISPLAY TRANSCRIPT
    // ==========================================

    function displayTranscript(data) {

        const transcriptData = data.transcript;

        if (!transcriptData) {
            statusElement.innerHTML =
                "❌ Transcript tidak ditemukan.";

            return;
        }

        const title = transcriptData.title || "Untitled Video";
        const language = transcriptData.language || "-";
        const segments = transcriptData.transcript || [];


        let html = "";

        html += `
            <div style="
                margin-top: 25px;
                padding: 20px;
                border-radius: 12px;
                background: #f5f5f5;
            ">

                <h2>${title}</h2>

                <p>
                    <strong>Language:</strong> ${language}
                </p>

                <hr>

                <h3>Transcript</h3>

                <div>
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
                            ${timestamp}
                        </span>

                        <span>
                            ${text}
                        </span>

                    </div>
                `;
            });
        }


        html += `
                </div>
            </div>
        `;


        statusElement.innerHTML = html;
    }


    // ==========================================
    // ANALYZE BUTTON
    // ==========================================

    analyzeButton.addEventListener("click", async () => {

        const url =
            videoUrlInput.value.trim();


        // ======================================
        // VALIDATION
        // ======================================

        if (!url) {

            statusElement.innerHTML =
                "❌ Masukkan URL YouTube terlebih dahulu.";

            return;
        }


        // ======================================
        // LOADING
        // ======================================

        analyzeButton.disabled = true;

        analyzeButton.innerText =
            "Analyzing...";

        statusElement.innerHTML =
            "⏳ Mengambil transcript dari YouTube...";


        try {

            // ==================================
            // CALL CLOUDFLARE API
            // ==================================

            const response =
                await fetch(API_URL, {

                    method: "POST",

                    headers: {
                        "Content-Type": "application/json"
                    },

                    body: JSON.stringify({
                        url: url
                    })
                });


            const data =
                await response.json();


            // ==================================
            // API ERROR
            // ==================================

            if (!response.ok ||
                data.status !== "success") {

                console.error(
                    "API Error:",
                    data
                );

                statusElement.innerHTML =
                    `
                    ❌ Gagal mengambil transcript.
                    <br><br>
                    ${data.message || "Unknown error"}
                    `;

                return;
            }


            // ==================================
            // SUCCESS
            // ==================================

            displayTranscript(data);


        } catch (error) {

            console.error(error);

            statusElement.innerHTML =
                `
                ❌ Tidak dapat terhubung ke backend.
                <br><br>
                ${error.message}
                `;

        } finally {

            analyzeButton.disabled = false;

            analyzeButton.innerText =
                "Analyze";
        }

    });

});
