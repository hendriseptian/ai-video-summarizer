const analyzeButton = document.getElementById("analyzeButton");
const videoUrlInput = document.getElementById("videoUrl");

const status = document.getElementById("status");
const videoInfo = document.getElementById("videoInfo");
const transcript = document.getElementById("transcript");


analyzeButton.addEventListener("click", function () {

    const videoUrl = videoUrlInput.value.trim();

    // Check empty URL
    if (!videoUrl) {

        status.innerHTML = "Please enter a YouTube URL.";

        return;
    }


    // Check YouTube URL
    if (
        !videoUrl.includes("youtube.com") &&
        !videoUrl.includes("youtu.be")
    ) {

        status.innerHTML = "Please enter a valid YouTube URL.";

        return;
    }


    // Show loading
    status.innerHTML = "Analyzing video...";

    analyzeButton.disabled = true;
    analyzeButton.innerHTML = "PROCESSING...";


    // Temporary simulation
    setTimeout(function () {

        status.innerHTML = "Analysis completed.";

        videoInfo.innerHTML = `
            <p>
                <strong>URL:</strong>
                ${videoUrl}
            </p>

            <p>
                <strong>Status:</strong>
                Ready
            </p>

            <p>
                <strong>Source:</strong>
                YouTube
            </p>
        `;


        transcript.innerHTML = `
This is a V1 test transcript.

The real YouTube transcript will be loaded
after the backend is connected.

V1 frontend is working correctly.
        `;


        analyzeButton.disabled = false;
        analyzeButton.innerHTML = "ANALYZE";

    }, 1000);

});
