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
    } catch {
        return null;
    }
}


async function analyzeVideo() {

    const urlInput = document.getElementById("videoUrl");
    const url = urlInput.value.trim();

    const result = document.getElementById("result");
    const transcript = document.getElementById("transcript");

    if (!url) {
        alert("Please enter a YouTube URL.");
        return;
    }

    const videoId = getYouTubeId(url);

    if (!videoId) {
        alert("Please enter a valid YouTube URL.");
        return;
    }

    result.innerHTML = `
        <p><strong>Status:</strong> Analyzing...</p>
        <p><strong>URL:</strong> ${url}</p>
    `;

    transcript.innerHTML = `
        <p>Connecting to AI Video Summarizer API...</p>
    `;

    try {

        const response = await fetch(`${API_URL}/analyze`, {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                url: url
            })

        });


        if (!response.ok) {
            throw new Error(
                `API returned HTTP ${response.status}`
            );
        }


        const data = await response.json();


        if (data.status !== "success") {
            throw new Error(
                data.message || "Analysis failed"
            );
        }


        result.innerHTML = `
            <p><strong>Status:</strong> Connected</p>
            <p><strong>URL:</strong> ${data.url}</p>
            <p><strong>Source:</strong> YouTube</p>
            <p><strong>Backend:</strong> Cloudflare</p>
        `;


        transcript.innerHTML = `
            <p><strong>Backend connection successful.</strong></p>
            <p>
                YouTube video received successfully.
                Real transcript extraction will be added next.
            </p>
        `;


    } catch (error) {

        console.error(error);

        result.innerHTML = `
            <p><strong>Status:</strong> Error</p>
            <p>${error.message}</p>
        `;

        transcript.innerHTML = `
            <p>
                Unable to connect to the backend.
            </p>
        `;
    }
}
