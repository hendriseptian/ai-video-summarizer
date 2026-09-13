const API_URL =
    "https://ai-video-summarizer.hendriseptian25.workers.dev";


function getYouTubeId(url) {

    try {

        const parsed = new URL(url);

        if (parsed.hostname.includes("youtu.be")) {
            return parsed.pathname.substring(1);
        }

        if (parsed.hostname.includes("youtube.com")) {
            return parsed.searchParams.get("v");
        }

        return null;

    } catch (error) {

        return null;

    }
}


async function analyzeVideo() {

    const urlInput = document.getElementById("videoUrl");
    const status = document.getElementById("status");

    if (!urlInput) {
        console.error("Element #videoUrl tidak ditemukan.");
        return;
    }

    if (!status) {
        console.error("Element #status tidak ditemukan.");
        return;
    }


    const url = urlInput.value.trim();


    // =========================
    // CHECK URL
    // =========================

    if (!url) {

        status.innerHTML = `
            <p>Please enter a YouTube URL.</p>
        `;

        return;
    }


    const videoId = getYouTubeId(url);


    if (!videoId) {

        status.innerHTML = `
            <p>Invalid YouTube URL.</p>
        `;

        return;
    }


    // =========================
    // START ANALYSIS
    // =========================

    status.innerHTML = `
        <p><strong>Status:</strong> Connecting...</p>
        <p><strong>URL:</strong> ${url}</p>
    `;


    try {

        console.log("Sending request to Cloudflare...");
        console.log("URL:", url);


        const response = await fetch(
            `${API_URL}/analyze`,
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    url: url
                })
            }
        );


        console.log("HTTP Status:", response.status);


        if (!response.ok) {

            throw new Error(
                `API returned HTTP ${response.status}`
            );

        }


        const data = await response.json();


        console.log("API Response:", data);


        if (data.status !== "success") {

            throw new Error(
                data.message || "Analysis failed"
            );

        }


        // =========================
        // SUCCESS
        // =========================

        status.innerHTML = `
            <p>
                <strong>Status:</strong>
                Connected
            </p>

            <p>
                <strong>URL:</strong>
                ${data.url}
            </p>

            <p>
                <strong>Source:</strong>
                YouTube
            </p>

            <p>
                <strong>Backend:</strong>
                Cloudflare
            </p>

            <p>
                <strong>Video ID:</strong>
                ${videoId}
            </p>
        `;


    } catch (error) {

        console.error("Analysis error:", error);


        status.innerHTML = `
            <p>
                <strong>Status:</strong>
                Error
            </p>

            <p>
                ${error.message}
            </p>
        `;

    }

}


// ========================================
// CONNECT ANALYZE BUTTON
// ========================================

document.addEventListener(
    "DOMContentLoaded",
    function () {

        const button =
            document.getElementById("analyzeButton");


        if (!button) {

            console.error(
                "Element #analyzeButton tidak ditemukan."
            );

            return;
        }


        button.addEventListener(
            "click",
            analyzeVideo
        );


        console.log(
            "AI Video Summarizer initialized."
        );

    }
);
