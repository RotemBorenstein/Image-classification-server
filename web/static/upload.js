const TOKEN_KEY = "picture_server_token";

const token = sessionStorage.getItem(TOKEN_KEY);
const feedback = document.getElementById("upload-feedback");
const uploadForm = document.getElementById("upload-form");
const imageInput = document.getElementById("image-input");
const preview = document.getElementById("image-preview");
const fileMeta = document.getElementById("file-meta");
const resultsEmpty = document.getElementById("results-empty");
const resultsList = document.getElementById("results-list");

function setFeedback(message, kind) {
    feedback.textContent = message || "";
    feedback.className = "feedback";

    if (!message) {
        return;
    }

    feedback.classList.add("is-visible", kind === "error" ? "is-error" : "is-success");
}

function clearResults() {
    resultsList.innerHTML = "";
    resultsList.hidden = true;
    resultsEmpty.hidden = false;
}

function renderResults(matches) {
    resultsList.innerHTML = "";

    matches.forEach((match) => {
        const item = document.createElement("li");
        item.className = "result-item";

        const percentage = Math.max(0, Math.min(100, Number(match.score) * 100));

        item.innerHTML = `
            <div class="result-row">
                <span class="result-name">${match.name}</span>
                <span class="result-score">${percentage.toFixed(2)}%</span>
            </div>
            <div class="score-bar" aria-hidden="true">
                <span style="width: ${percentage}%"></span>
            </div>
        `;

        resultsList.appendChild(item);
    });

    resultsEmpty.hidden = matches.length > 0;
    resultsList.hidden = matches.length === 0;
}

function ensureAuthenticated() {
    if (token) {
        return true;
    }

    setFeedback("No bearer token found. Please log in first.", "error");
    uploadForm.querySelector("button[type='submit']").disabled = true;
    window.setTimeout(() => {
        window.location.href = "/";
    }, 1200);
    return false;
}

function updatePreview(file) {
    if (!file) {
        preview.hidden = true;
        preview.removeAttribute("src");
        fileMeta.textContent = "No image selected.";
        clearResults();
        return;
    }

    fileMeta.textContent = `${file.name} • ${(file.size / 1024).toFixed(1)} KB`;
    preview.src = URL.createObjectURL(file);
    preview.hidden = false;
    clearResults();
}

async function handleUpload(event) {
    event.preventDefault();

    if (!ensureAuthenticated()) {
        return;
    }

    const file = imageInput.files[0];
    if (!file) {
        setFeedback("Select an image before uploading.", "error");
        return;
    }

    setFeedback("Uploading image and waiting for classification...", "success");

    const formData = new FormData();
    formData.append("image", file);

    try {
        const response = await fetch("/classifier", {
            method: "POST",
            headers: {
                Authorization: `Bearer ${token}`
            },
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error?.message || "Classification failed");
        }

        renderResults(data.matches || []);
        setFeedback("Classification completed successfully.", "success");
    } catch (error) {
        setFeedback(error.message, "error");
        clearResults();
    }
}

async function handleStatusCheck() {
    if (!ensureAuthenticated()) {
        return;
    }

    setFeedback("Checking server status...", "success");

    try {
        const response = await fetch("/status", {
            headers: {
                Authorization: `Bearer ${token}`
            }
        });
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error?.message || "Status check failed");
        }

        const status = data.status;
        const uptimeSeconds = Number(status.uptime);
        const uptimeText = Number.isFinite(uptimeSeconds)
            ? uptimeSeconds.toFixed(1)
            : String(status.uptime);

        setFeedback(
            `Server health: ${status.health}. Uptime: ${uptimeText}s. Success: ${status.processed.success}, Fail: ${status.processed.fail}. API version: ${status.api_version}.`,
            "success"
        );
    } catch (error) {
        setFeedback(error.message, "error");
    }
}

async function handleLogout() {
    if (!token) {
        sessionStorage.removeItem(TOKEN_KEY);
        window.location.href = "/";
        return;
    }

    setFeedback("Logging out...", "success");

    try {
        const response = await fetch("/logout", {
            method: "POST",
            headers: {
                Authorization: `Bearer ${token}`
            }
        });
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error?.message || "Logout failed");
        }
    } catch (error) {
        setFeedback(error.message, "error");
        return;
    }

    sessionStorage.removeItem(TOKEN_KEY);
    window.location.href = "/";
}

imageInput.addEventListener("change", () => {
    updatePreview(imageInput.files[0]);
});

uploadForm.addEventListener("submit", handleUpload);
document.getElementById("status-button").addEventListener("click", handleStatusCheck);
document.getElementById("logout-button").addEventListener("click", handleLogout);

ensureAuthenticated();
